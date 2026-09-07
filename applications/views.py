import csv
import secrets
import time
import json

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db.models import Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView
from .forms import FamApplicationForm
from .models import FamApplication, SiteBrand, STATUS
from .forms import SiteBrandForm
from .utils import send_email
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

ARRAY_FIELDS = {'tourism_interests', 'promotion_channels', 'expected_content_types', 'strong_products'}

SCORE_FIELDS = ['professional_credibility_score', 'market_relevance_score', 'audience_reach_score',
                'tourism_influence_score', 'language_reach_score', 'content_potential_score', 'travel_trade_score',
                'promotion_potential_score']

OTP_EXPIRY_SECONDS = 10 * 60
OTP_RESEND_DELAY_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


def _email_error(request):
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return email, 'Enter a valid email address.'
    if FamApplication.objects.filter(email__iexact=email).exists():
        return email, 'An application with this email address already exists.'
    return email, None


class SendEmailOtpView(View):
    """Send a time-limited email verification code for a new applicant."""

    def post(self, request, *args, **kwargs):
        email, error = _email_error(request)
        if error:
            return JsonResponse({'error': error}, status=400)

        last_sent = request.session.get('email_otp_sent_at', 0)
        if time.time() - last_sent < OTP_RESEND_DELAY_SECONDS:
            return JsonResponse({'error': 'Please wait before requesting another code.'}, status=429)

        code = f'{secrets.randbelow(1000000):06d}'
        request.session['email_otp_email'] = email
        request.session['email_otp_hash'] = make_password(code)
        request.session['email_otp_expires_at'] = time.time() + OTP_EXPIRY_SECONDS
        request.session['email_otp_sent_at'] = time.time()
        request.session['email_otp_attempts'] = 0
        request.session.pop('email_verified', None)
        request.session.modified = True

        send_email(
            email,
            {'otp': code},
            'applications/email/email_verification_subject.txt',
            plain_body_template_name='applications/email/email_verification.txt',
        )
        return JsonResponse({'message': 'Verification code sent. Check your email.'})


class VerifyEmailOtpView(View):
    """Verify the submitted email code and mark that email as verified in session."""

    def post(self, request, *args, **kwargs):
        email, error = _email_error(request)
        if error:
            return JsonResponse({'error': error}, status=400)

        if request.session.get('email_otp_email') != email:
            return JsonResponse({'error': 'Request a verification code for this email first.'}, status=400)
        if time.time() > request.session.get('email_otp_expires_at', 0):
            return JsonResponse({'error': 'This verification code has expired. Request a new code.'}, status=400)
        if request.session.get('email_otp_attempts', 0) >= OTP_MAX_ATTEMPTS:
            return JsonResponse({'error': 'Too many incorrect attempts. Request a new code.'}, status=400)

        request.session['email_otp_attempts'] = request.session.get('email_otp_attempts', 0) + 1
        if not check_password(request.POST.get('otp', '').strip(), request.session.get('email_otp_hash', '')):
            request.session.modified = True
            return JsonResponse({'error': 'The verification code is incorrect.'}, status=400)

        request.session['email_verified'] = email
        request.session.modified = True
        return JsonResponse({'message': 'Email verified successfully.'})


class ApplicationFormView(FormView):
    """Display and process the public FAM tour application form."""

    template_name = 'applications/application_form.html'
    form_class = FamApplicationForm

    def post(self, request, *args, **kwargs):
        """Accept submitted form data and uploaded supporting material."""
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add the current site branding to the form context."""
        context = super().get_context_data(**kwargs)
        context['brand'] = SiteBrand.objects.first()
        return context

    def form_invalid(self, form):
        """Redisplay the submitted form with validation errors and branding."""
        context = self.get_context_data(form=form)
        context['submission_failed'] = True
        return self.render_to_response(context)

    def form_valid(self, form):
        """Validate repeated fields and save the submitted application."""
        email = form.cleaned_data['email'].strip().lower()
        if self.request.session.get('email_verified') != email:
            form.add_error('email', 'Please verify this email address before submitting.')
            return self.form_invalid(form)

        missing = []
        if not any(value.strip() for value in self.request.POST.getlist('language_name')):
            missing.append('at least one professional language')
        if not self.request.POST.getlist('tourism_interests'):
            missing.append('at least one tourism area of interest')
        if not self.request.POST.getlist('promotion_channels'):
            missing.append('at least one post-FAM promotion option')
        if missing:
            form.add_error(None, 'Please provide ' + ', '.join(missing) + '.')
            return self.form_invalid(form)

        application = form.save(commit=False)
        application.social_profiles = {
            key: self.request.POST.get(key, '').strip()
            for key in ['instagram', 'facebook', 'x', 'linkedin', 'youtube', 'tiktok_other']
        }
        application.content_links = [
            value.strip() for value in self.request.POST.getlist('content_links') if value.strip()
        ]
        names = self.request.POST.getlist('language_name')
        levels = self.request.POST.getlist('language_level')
        application.professional_languages = [
            {'language': name.strip(), 'proficiency': levels[index] if index < len(levels) else ''}
            for index, name in enumerate(names) if name.strip()
        ]
        for field in ARRAY_FIELDS:
            setattr(application, field, self.request.POST.getlist(field))
        application.save()
        application.reference_number = f'DTN{timezone.now().year % 100:02d}-{application.pk:03d}'
        application.save(update_fields=['reference_number'])
        self.request.session['last_submission_reference'] = application.reference_number
        self.request.session['last_submission_name'] = application.applicant_name
        self.request.session.modified = True
        send_email(
            application.email,
            {
                'applicant_name': application.applicant_name,
                'reference_number': application.reference_number,
            },
            'applications/email/application_confirmation_subject.txt',
            plain_body_template_name='applications/email/application_confirmation.txt',
        )
        return redirect('applications:thank-you')


class ThankYouView(TemplateView):
    """Display the confirmation page after an application is submitted."""

    template_name = 'applications/thank_you.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reference_number'] = self.request.session.get('last_submission_reference')
        context['applicant_name'] = self.request.session.get('last_submission_name')
        return context


def suggested_score(app):
    """Calculate a lightweight completeness score for dashboard guidance."""
    score = 0
    if app.short_bio: score += 8
    if app.awards: score += 6
    if app.fam_experience == 'Yes': score += 5
    if app.visited_tamil_nadu == 'Yes': score += 3
    if app.promoted_india_tn == 'Yes': score += 5
    if app.social_profiles: score += 8
    if app.content_links: score += 8
    if app.total_audience: score += 10
    if app.monthly_reach: score += 5
    if app.audience_regions: score += 8
    if app.professional_languages: score += 7
    if app.tourism_interests: score += 5
    if app.promotion_channels: score += 7
    if app.promotion_plan: score += 6
    if app.selection_reason: score += 5
    if app.availability in ('Yes, I confirm my availability', 'I expect to be available'): score += 5
    return min(score, 100)


class StaffRequiredMixin(UserPassesTestMixin):
    """Require an active staff user for committee views."""

    login_url = reverse_lazy('applications:committee-login')

    def test_func(self):
        """
        Return whether the current user may access committee features.
        """
        return self.request.user.is_active and self.request.user.is_staff


class DashboardView(StaffRequiredMixin, View):
    """Display the searchable committee application dashboard."""

    def get(self, request):
        """Build dashboard applications and summary statistics."""
        queryset = FamApplication.objects.all()
        query = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(country_of_residence__icontains=query) |
                Q(primary_category__icontains=query) |
                Q(organisation__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        applications = list(queryset.order_by('-committee_score', '-submitted_at'))
        stats = {key: FamApplication.objects.filter(status=key).count() for key in
                 ['submitted', 'reviewing', 'shortlisted', 'selected', 'rejected']}
        from django.db.models import Avg
        total = FamApplication.objects.count()
        scored = FamApplication.objects.filter(committee_score__isnull=False)
        average_score = round(scored.aggregate(value=Avg('committee_score'))['value'] or 0, 1)
        countries = FamApplication.objects.values('country_of_residence').distinct().count()
        brand = SiteBrand.objects.first()
        return render(request, 'applications/dashboard.html', {
            'applications': applications,
            'stats': stats,
            'q': query,
            'status': status,
            'statuses': STATUS,
            'suggested_score': suggested_score,
            'total': total,
            'avg_score': average_score,
            'countries': countries,
            'selected': stats.get('selected', 0),
            'brand': brand,
        })


class ApplicationDetailView(StaffRequiredMixin, View):
    """Display and update committee scoring for one application."""

    def get(self, request, pk):
        """Render the committee review form."""
        application = get_object_or_404(FamApplication, pk=pk)
        return render(request, 'applications/application_detail.html', {
            'app': application,
            'suggested': suggested_score(application),
            'score_fields': [
                (field, field.replace('_score', '').replace('_', ' ').title())
                for field in SCORE_FIELDS
            ],
            'statuses': STATUS,
        })

    def post(self, request, pk):
        """Save committee scores, status, notes, and review timestamp."""
        application = get_object_or_404(FamApplication, pk=pk)
        for field in SCORE_FIELDS:
            value = request.POST.get(field)
            if value != '':
                setattr(application, field, max(0, min(10, int(value))))
        total = sum(getattr(application, field) for field in SCORE_FIELDS)
        if any(getattr(application, field) for field in SCORE_FIELDS):
            application.committee_score = max(0, min(100, total * 1.25))
        application.status = request.POST.get('status', application.status)
        application.committee_notes = request.POST.get('committee_notes', '')
        application.reviewed_at = timezone.now()
        application.save()
        return redirect('applications:application-detail', pk=pk)


class CsvExportView(StaffRequiredMixin, View):
    """Export committee applications as a CSV download."""

    def get(self, request):
        """Generate and return the applications CSV file."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="discover-tamil-nadu-applications.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Country', 'Category', 'Organisation', 'Email', 'Audience', 'Availability',
                         'Status', 'Committee Score', 'Submitted'])
        for application in FamApplication.objects.order_by('-submitted_at'):
            writer.writerow([
                application.id, f'{application.first_name} {application.last_name}', application.country_of_residence,
                application.primary_category, application.organisation, application.email,
                application.total_audience, application.availability, application.status,
                application.committee_score or '', application.submitted_at,
            ])
        return response


class CommitteeLoginView(DjangoLoginView):
    """Authenticate committee staff users."""

    template_name = 'applications/committee_login.html'
    redirect_authenticated_user = True


def _export_xlsx(request):
    """Build the applications Excel response."""
    apps = FamApplication.objects.order_by('-submitted_at')
    wb = Workbook()
    ws = wb.active
    ws.title = 'Applications'

    form_labels = {
        'id': 'ID',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'nationality': 'Nationality',
        'country_of_residence': 'Country of Residence',
        'city_state_province': 'City / State / Province',
        'address': 'Address',
        'email': 'Email Address',
        'mobile_whatsapp': 'Mobile / WhatsApp Number',
        'preferred_language': 'Preferred Language of Communication',
        'age_group': 'Age Group',
        'primary_category': 'Primary Category',
        'other_professional_category': 'Other Tourism Professional',
        'organisation': 'Organisation / Media House / Company',
        'designation': 'Designation / Professional Role',
        'website': 'Website / Professional Profile',
        'years_experience': 'Years of Professional Experience',
        'short_bio': 'Short Bio - Maximum 200 Words',
        'awards': 'Awards, Recognitions & Achievements',
        'fam_experience': 'Previous International / Destination FAM Experience',
        'fam_experience_details': 'Previous FAM Experience Details',
        'visited_india': 'Have you visited India before?',
        'india_states': 'States / Union Territories Visited in India',
        'last_india_visit': 'Last India Visit',
        'visited_tamil_nadu': 'Have you visited Tamil Nadu before?',
        'tamil_nadu_destinations': 'Tamil Nadu Destinations Visited',
        'promoted_india_tn': 'Previously Published, Broadcast or Promoted India / Tamil Nadu',
        'promoted_india_tn_details': 'India / Tamil Nadu Promotion Details',
        'social_profiles': 'Social Profiles',
        'total_audience': 'Approximate Total Audience / Followers',
        'audience_regions': 'Primary Audience Countries / Regions',
        'audience_languages': 'Primary Audience Language(s)',
        'monthly_reach': 'Approximate Average Monthly Reach / Views',
        'engagement_rate': 'Average Engagement Rate',
        'content_links': 'Relevant Travel Stories / Articles / Videos / Campaigns',
        'professional_languages': 'Professional Languages and Proficiency',
        'post_fam_languages': 'Languages for Sharing Tamil Nadu Experience',
        'language_reach_regions': 'Regions Reached Through These Languages',
        'tourism_interests': 'Tamil Nadu Tourism Areas of Interest',
        'other_tourism_interest': 'Other Area of Interest',
        'desired_experience': 'Desired Tamil Nadu Experience',
        'familiar_destinations': 'Familiar Tamil Nadu Destinations',
        'promotion_channels': 'Post-FAM Promotion Channels',
        'other_promotion_channel': 'Other Promotion Channel',
        'promotion_plan': 'Proposed Post-FAM Promotion Plan',
        'expected_content_types': 'Expected Content Types',
        'other_content_type': 'Other Content Type',
        'output_count': 'Expected Content / Promotional Outputs',
        'coverage_timeline': 'Expected Timeline for Post-FAM Coverage',
        'market_value': 'Value for Tamil Nadu Tourism in the Market',
        'sells_india': 'Currently Sell or Promote India',
        'offers_tamil_nadu': 'Currently Offer Tamil Nadu',
        'introduce_tamil_nadu': 'Introduce Tamil Nadu into Existing Programmes',
        'dedicated_tn_package': 'Develop a Dedicated Tamil Nadu Itinerary / Package',
        'strong_products': 'Tamil Nadu Tourism Products with Strongest Potential',
        'annual_clients': 'Travellers / Clients Handled Annually',
        'future_b2b': 'Interested in Future B2B Engagement',
        'selection_reason': 'Why Should You Be Selected',
        'unique_perspective': 'Unique Perspective, Audience or Market Access',
        'media_participation': 'Willing to Participate in Media Activities',
        'post_fam_participation': 'Willing to Participate in Post-FAM Activities',
        'programme_source': 'How You Heard About Discover Tamil Nadu',
        'other_programme_source': 'Other Source',
        'availability': 'Availability for 12-20 January 2027',
        'valid_passport': 'Valid Passport for Travel to India',
        'comply_schedule': 'Willing to Comply with Programme Requirements',
        'additional_information': 'Additional Information for Selection Committee',
        'supporting_material': 'Supporting Material',
        'declaration_accepted': 'Declaration and Consent Accepted',
        'applicant_name': 'Applicant Name',
        'declaration_date': 'Declaration Date',
        'digital_signature': 'Digital Confirmation / Signature',
        'status': 'Application Status',
        'committee_score': 'Committee Score',
        'professional_credibility_score': 'Professional Credibility Score',
        'market_relevance_score': 'Market Relevance Score',
        'audience_reach_score': 'Audience Reach Score',
        'tourism_influence_score': 'Tourism Influence Score',
        'language_reach_score': 'Language Reach Score',
        'content_potential_score': 'Content Potential Score',
        'travel_trade_score': 'Travel Trade Score',
        'promotion_potential_score': 'Promotion Potential Score',
        'committee_notes': 'Committee Notes',
        'reviewed_at': 'Reviewed At',
        'submitted_at': 'Submitted At',
    }
    export_fields = [field for field in FamApplication._meta.concrete_fields]
    ws.append([form_labels.get(field.name, field.verbose_name.title()) for field in export_fields])
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center')

    def display_value(application, field):
        value = getattr(application, field.name)
        if field.name == 'status':
            return application.get_status_display()
        if field.name == 'supporting_material':
            return value.name if value else ''
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=True)
        if field.name in {'submitted_at', 'reviewed_at'} and value:
            return value.strftime('%Y-%m-%d %H:%M')
        return value if value is not None else ''

    for a in apps:
        ws.append([display_value(a, field) for field in export_fields])
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max(len(str(col[0].value or '')) + 2, 12), 35)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="discover-tamil-nadu-applications.xlsx"'
    wb.save(response)
    return response


def _application_pdf(request, pk):
    """Build the PDF response for one application."""
    app = get_object_or_404(FamApplication, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="application-{app.id}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=15 * mm,
                            bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('TitleX', parent=styles['Title'], fontSize=18, textColor=colors.HexColor('#8f1d24'),
                           spaceAfter=8)
    h = ParagraphStyle('HX', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#8f1d24'),
                       spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle('BodyX', parent=styles['BodyText'], fontSize=8.5, leading=12)
    story = [Paragraph('DISCOVER TAMIL NADU 2026–27', title),
             Paragraph('International FAM Tour — Application', styles['Heading2']),
             Paragraph('FAM Tour Dates: 12–20 January 2027', body), Spacer(1, 8)]
    sections = [
        ('Applicant Details', [('First Name', app.first_name), ('Last Name', app.last_name), ('Nationality', app.nationality),
                               ('Country of Residence', app.country_of_residence),
                               ('City / State / Province', app.city_state_province), ('Address', app.address),
                               ('Email', app.email), ('Mobile / WhatsApp', app.mobile_whatsapp),
                               ('Preferred Language', app.preferred_language), ('Age Group', app.age_group)]),
        ('Professional Profile', [('Primary Category', app.primary_category), ('Organisation', app.organisation),
                                  ('Designation', app.designation),
                                  ('Website / Profile', app.website), ('Years of Experience', app.years_experience),
                                  ('Short Bio', app.short_bio), ('Awards', app.awards),
                                  ('Previous FAM Experience', app.fam_experience),
                                  ('FAM Details', app.fam_experience_details)]),
        ('India & Tamil Nadu Experience', [('Visited India', app.visited_india), ('States / UTs', app.india_states),
                                           ('Last India Visit', app.last_india_visit),
                                           ('Visited Tamil Nadu', app.visited_tamil_nadu),
                                           ('Tamil Nadu Destinations', app.tamil_nadu_destinations),
                                           ('Promoted India / Tamil Nadu', app.promoted_india_tn),
                                           ('Promotion Details', app.promoted_india_tn_details)]),
        ('Digital & Media Profile', [('Social Profiles', json.dumps(app.social_profiles, ensure_ascii=False)),
                                     ('Total Audience', app.total_audience),
                                     ('Audience Countries / Regions', app.audience_regions),
                                     ('Audience Languages', app.audience_languages),
                                     ('Monthly Reach', app.monthly_reach),
                                     ('Engagement Rate', app.engagement_rate),
                                     ('Content Links', json.dumps(app.content_links, ensure_ascii=False))]),
        ('Language & Regional Reach',
         [('Professional Languages', json.dumps(app.professional_languages, ensure_ascii=False)),
          ('Post-FAM Languages', app.post_fam_languages), ('Language Reach Regions', app.language_reach_regions)]),
        ('Areas of Interest',
         [('Tourism Interests', ', '.join(app.tourism_interests)), ('Desired Experience', app.desired_experience),
          ('Familiar Destinations', app.familiar_destinations)]),
        ('Post-FAM Promotion Commitment',
         [('Promotion Channels', ', '.join(app.promotion_channels)), ('Promotion Plan', app.promotion_plan),
          ('Content Types', ', '.join(app.expected_content_types)), ('Expected Outputs', app.output_count),
          ('Coverage Timeline', app.coverage_timeline),
          ('Value to Tamil Nadu Tourism', app.market_value)]),
        ('Travel Trade Potential', [('Sells India', app.sells_india), ('Offers Tamil Nadu', app.offers_tamil_nadu),
                                    ('Introduce Tamil Nadu', app.introduce_tamil_nadu),
                                    ('Dedicated TN Package', app.dedicated_tn_package),
                                    ('Strong Products', ', '.join(app.strong_products)),
                                    ('Annual Clients', app.annual_clients), ('Future B2B', app.future_b2b)]),
        ('Participant Value & Suitability',
         [('Why Select', app.selection_reason), ('Unique Perspective', app.unique_perspective),
          ('Media Participation', app.media_participation), ('Post-FAM Participation', app.post_fam_participation)]),
        ('Programme & Availability',
         [('Source', app.programme_source), ('Availability', app.availability), ('Valid Passport', app.valid_passport),
          ('Comply with Schedule', app.comply_schedule), ('Additional Information', app.additional_information)]),
        ('Declaration', [('Applicant Name', app.applicant_name), ('Date', app.declaration_date),
                         ('Digital Signature', app.digital_signature),
                         ('Declaration Accepted', app.declaration_accepted)]),
    ]
    for heading, rows in sections:
        story.append(Paragraph(heading, h))
        data = [[Paragraph(str(k), body), Paragraph(str(v if v not in (None, '') else '—'), body)] for k, v in rows]
        t = Table(data, colWidths=[48 * mm, 127 * mm], repeatRows=0)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d9dde3')),
                               ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f4f6f8')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 5),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                               ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [t, Spacer(1, 5)]
    story.append(Paragraph('Committee Review', h))
    score_rows = [('Professional credibility', app.professional_credibility_score),
                  ('International market relevance', app.market_relevance_score),
                  ('Audience / business reach', app.audience_reach_score),
                  ('Tourism influence', app.tourism_influence_score),
                  ('Language reach', app.language_reach_score),
                  ('Media / content potential', app.content_potential_score),
                  ('Travel trade potential', app.travel_trade_score),
                  ('Post-FAM promotion potential', app.promotion_potential_score),
                  ('Committee total', app.committee_score or 'Not scored'), ('Status', app.get_status_display()),
                  ('Notes', app.committee_notes)]
    data = [[Paragraph(str(k), body), Paragraph(str(v), body)] for k, v in score_rows]
    t = Table(data, colWidths=[75 * mm, 100 * mm])
    t.setStyle(
        TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d9dde3')), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story += [t]
    doc.build(story)
    return response


class XlsxExportView(StaffRequiredMixin, View):
    """Export committee applications as an Excel workbook."""

    def get(self, request):
        """Generate and return the applications Excel file."""
        return _export_xlsx(request)


class ApplicationPdfView(StaffRequiredMixin, View):
    """Export one application and its review data as a PDF."""

    def get(self, request, pk):
        """Generate and return the selected application PDF."""
        return _application_pdf(request, pk)


class BrandingView(StaffRequiredMixin, View):
    """Display and update the site branding configuration."""

    def get(self, request):
        """Render the branding form."""
        brand = SiteBrand.objects.first() or SiteBrand.objects.create()
        form = SiteBrandForm(instance=brand)
        return render(request, 'applications/branding.html', {'form': form, 'brand': brand})

    def post(self, request):
        """Validate and save submitted branding configuration."""
        brand = SiteBrand.objects.first() or SiteBrand.objects.create()
        form = SiteBrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            return redirect('applications:branding')
        return render(request, 'applications/branding.html', {'form': form, 'brand': brand})
