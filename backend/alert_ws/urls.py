from django.urls import path
from . import views

urlpatterns = [
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/<str:alert_id>/acknowledge/', views.AlertAcknowledgeView.as_view(), name='alert-acknowledge'),
]
