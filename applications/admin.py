from django.contrib import admin
from .models import FamApplication

@admin.register(FamApplication)
class FamApplicationAdmin(admin.ModelAdmin):
    list_display=('reference_number','first_name','last_name','country_of_residence','primary_category','committee_score','status','submitted_at')
    search_fields=('reference_number','first_name','last_name','email','country_of_residence','organisation')
    list_filter=('status','primary_category','visited_india','visited_tamil_nadu','submitted_at')
    list_editable=('status','committee_score')
    readonly_fields=('reference_number','submitted_at','reviewed_at')
    fieldsets=(
      ('Application',{'fields':('reference_number','first_name','last_name','email','country_of_residence','primary_category','organisation','status','committee_score')}),
      ('Committee scoring',{'fields':('professional_credibility_score','market_relevance_score','audience_reach_score','tourism_influence_score','language_reach_score','content_potential_score','travel_trade_score','promotion_potential_score','committee_notes','reviewed_at')}),
      ('Submission',{'fields':('submitted_at',)}),
    )
