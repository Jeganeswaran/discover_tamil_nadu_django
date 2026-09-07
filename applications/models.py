from django.db import models

STATUS = (
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('reviewing', 'Under Review'),
    ('shortlisted', 'Shortlisted'),
    ('selected', 'Selected'),
    ('rejected', 'Rejected')
)


class FamApplication(models.Model):
    objects = models.Manager()
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    nationality = models.CharField(max_length=120)
    country_of_residence = models.CharField(max_length=120)
    city_state_province = models.CharField(max_length=160)
    address = models.TextField()
    email = models.EmailField()
    mobile_whatsapp = models.CharField(max_length=40)
    preferred_language = models.CharField(max_length=100, blank=True)
    age_group = models.CharField(max_length=20, blank=True)
    primary_category = models.CharField(max_length=100)
    other_professional_category = models.CharField(max_length=160, blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=160, blank=True)
    website = models.URLField(blank=True)
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    short_bio = models.TextField()
    awards = models.TextField(blank=True)
    fam_experience = models.CharField(max_length=8, blank=True)
    fam_experience_details = models.TextField(blank=True)
    visited_india = models.CharField(max_length=8)
    india_states = models.TextField(blank=True)
    last_india_visit = models.CharField(max_length=40, blank=True)
    visited_tamil_nadu = models.CharField(max_length=8)
    tamil_nadu_destinations = models.TextField(blank=True)
    promoted_india_tn = models.CharField(max_length=8, blank=True)
    promoted_india_tn_details = models.TextField(blank=True)
    social_profiles = models.JSONField(default=dict, blank=True)
    total_audience = models.CharField(max_length=80)
    audience_regions = models.TextField()
    audience_languages = models.CharField(max_length=240)
    monthly_reach = models.CharField(max_length=80, blank=True)
    engagement_rate = models.CharField(max_length=80, blank=True)
    content_links = models.JSONField(default=list, blank=True)
    professional_languages = models.JSONField(default=list, blank=True)
    post_fam_languages = models.CharField(max_length=240)
    language_reach_regions = models.TextField(blank=True)
    tourism_interests = models.JSONField(default=list, blank=True)
    other_tourism_interest = models.CharField(max_length=160, blank=True)
    desired_experience = models.TextField(blank=True)
    familiar_destinations = models.TextField(blank=True)
    promotion_channels = models.JSONField(default=list, blank=True)
    other_promotion_channel = models.CharField(max_length=160, blank=True)
    promotion_plan = models.TextField()
    expected_content_types = models.JSONField(default=list, blank=True)
    other_content_type = models.CharField(max_length=160, blank=True)
    output_count = models.CharField(max_length=40, blank=True)
    coverage_timeline = models.CharField(max_length=40, blank=True)
    market_value = models.TextField(blank=True)
    sells_india = models.CharField(max_length=8, blank=True)
    offers_tamil_nadu = models.CharField(max_length=8, blank=True)
    introduce_tamil_nadu = models.CharField(max_length=12, blank=True)
    dedicated_tn_package = models.CharField(max_length=12, blank=True)
    strong_products = models.JSONField(default=list, blank=True)
    annual_clients = models.CharField(max_length=80, blank=True)
    future_b2b = models.CharField(max_length=8, blank=True)
    selection_reason = models.TextField()
    unique_perspective = models.TextField(blank=True)
    media_participation = models.CharField(max_length=8, blank=True)
    post_fam_participation = models.CharField(max_length=30, blank=True)
    programme_source = models.CharField(max_length=120)
    other_programme_source = models.CharField(max_length=160, blank=True)
    availability = models.CharField(max_length=80)
    valid_passport = models.CharField(max_length=30, blank=True)
    comply_schedule = models.CharField(max_length=8, blank=True)
    additional_information = models.TextField(blank=True)
    supporting_material = models.FileField(upload_to='fam-support/', blank=True)
    declaration_accepted = models.BooleanField(default=False)
    applicant_name = models.CharField(max_length=160)
    declaration_date = models.DateField()
    digital_signature = models.CharField(max_length=160)
    reference_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default='submitted')
    committee_score = models.PositiveIntegerField(null=True, blank=True)
    professional_credibility_score = models.PositiveIntegerField(default=0)
    market_relevance_score = models.PositiveIntegerField(default=0)
    audience_reach_score = models.PositiveIntegerField(default=0)
    tourism_influence_score = models.PositiveIntegerField(default=0)
    language_reach_score = models.PositiveIntegerField(default=0)
    content_potential_score = models.PositiveIntegerField(default=0)
    travel_trade_score = models.PositiveIntegerField(default=0)
    promotion_potential_score = models.PositiveIntegerField(default=0)
    committee_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.country_of_residence}'


class SiteBrand(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=160, default='Discover Tamil Nadu')
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Branding'
        verbose_name_plural = 'Site Branding'

    def __str__(self):
        return self.name
