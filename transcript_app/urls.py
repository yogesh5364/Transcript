from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.TranscriptUploadView.as_view(), name='transcript-upload'),
    path('', views.TranscriptListView.as_view(), name='transcript-list'),
    path('<int:pk>/', views.TranscriptDetailView.as_view(), name='transcript-detail'),
    path('<int:pk>/status/', views.TranscriptStatusView.as_view(), name='transcript-status'),
    path('<int:pk>/export/<str:format_type>/', views.TranscriptExportView.as_view(), name='transcript-export'),
]