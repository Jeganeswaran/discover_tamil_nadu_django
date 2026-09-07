from django import forms
import pycountry
from .models import FamApplication

COUNTRY_CHOICES = [
    (country.name, country.name)
    for country in sorted(pycountry.countries, key=lambda item: item.name)
    if country.name != 'India'
]

class FamApplicationForm(forms.ModelForm):
    country_of_residence = forms.ChoiceField(choices=COUNTRY_CHOICES)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if FamApplication.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An application with this email address already exists.')
        return email

    class Meta:
        model=FamApplication
        exclude=(
            'status','submitted_at','social_profiles','content_links','professional_languages',
            'tourism_interests','promotion_channels','expected_content_types','strong_products',
            'reference_number',
            'committee_score','professional_credibility_score','market_relevance_score',
            'audience_reach_score','tourism_influence_score','language_reach_score',
            'content_potential_score','travel_trade_score','promotion_potential_score',
            'committee_notes','reviewed_at'
        )
        widgets={
            'country_of_residence': forms.Select(choices=COUNTRY_CHOICES),
            'short_bio': forms.Textarea(attrs={'maxlength':'1800'}),
            'declaration_date': forms.DateInput(attrs={'type':'date'}),
            'supporting_material': forms.FileInput(attrs={'accept':'.pdf,.doc,.docx,.jpg,.jpeg,.png'}),
        }

    def clean_short_bio(self):
        value=self.cleaned_data.get('short_bio','')
        if len(value.split()) > 200:
            raise forms.ValidationError('Please keep your short bio within 200 words.')
        return value

    def clean_declaration_accepted(self):
        value=self.cleaned_data.get('declaration_accepted')
        if not value:
            raise forms.ValidationError('You must agree to the Declaration and Consent before submitting.')
        return value


from .models import SiteBrand

class SiteBrandForm(forms.ModelForm):
    class Meta:
        model = SiteBrand
        fields = ['name', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class':'w-full rounded-xl border border-slate-300 px-4 py-3'}),
            'logo': forms.ClearableFileInput(attrs={'class':'w-full rounded-xl border border-slate-300 px-4 py-3'}),
        }
