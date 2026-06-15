from django.urls import path
from . import views

urlpatterns = [
    path('spectrum/upload/', views.SpectrumUploadView.as_view(), name='spectrum-upload'),
    path('simulator/start/', views.SimulatorStartView.as_view(), name='simulator-start'),
    path('simulator/stop/', views.SimulatorStopView.as_view(), name='simulator-stop'),
]
