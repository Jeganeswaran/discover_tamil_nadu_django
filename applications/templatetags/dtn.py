from django import template
register=template.Library()
@register.filter
def get_item(d,key): return d.get(key,0)
@register.filter
def suggested_score(app):
    score=0
    for attr,points in [('short_bio',8),('awards',6),('fam_experience',5),('visited_tamil_nadu',3),('promoted_india_tn',5),('social_profiles',8),('content_links',8),('total_audience',10),('monthly_reach',5),('audience_regions',8),('professional_languages',7),('tourism_interests',5),('promotion_channels',7),('promotion_plan',6),('selection_reason',5)]:
        if getattr(app,attr,None): score+=points
    if app.availability in ('Yes, I confirm my availability','I expect to be available'): score+=5
    return min(score,100)

@register.filter
def get_attr(obj,name): return getattr(obj,name,'')
