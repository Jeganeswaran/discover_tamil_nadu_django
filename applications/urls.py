from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'applications'
urlpatterns = [
    path('', views.ApplicationFormView.as_view(), name='application-form'),
    path('thank-you/', views.ThankYouView.as_view(), name='thank-you'),
    path('committee/login/', views.CommitteeLoginView.as_view(), name='committee-login'),
    path('committee/logout/', LogoutView.as_view(), name='committee-logout'),
    path('committee/', views.DashboardView.as_view(), name='dashboard'),
    path('committee/analytics/', views.DashboardView.as_view(), name='analytics'),
    path('committee/application/<int:pk>/', views.ApplicationDetailView.as_view(), name='application-detail'),
    path('committee/export.csv', views.CsvExportView.as_view(), name='export-csv'),
    path('committee/export.xlsx', views.XlsxExportView.as_view(), name='export-xlsx'),
    path('committee/application/<int:pk>/pdf/', views.ApplicationPdfView.as_view(), name='application-pdf'),
    path('committee/branding/', views.BrandingView.as_view(), name='branding'),
]
