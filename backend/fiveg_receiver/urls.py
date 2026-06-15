from django.urls import path
from . import views

urlpatterns = [
    path('spectrum/upload/', views.SpectrumUploadView.as_view(), name='spectrum-upload'),
    path('simulator/start/', views.SimulatorStartView.as_view(), name='simulator-start'),
    path('simulator/stop/', views.SimulatorStopView.as_view(), name='simulator-stop'),
    path('simulator/inject_forgery/', views.ForgeryInjectView.as_view(), name='inject-forgery'),
    path('simulator/remove_forgery/', views.ForgeryRemoveView.as_view(), name='remove-forgery'),
    path('simulator/forgery_list/', views.ForgeryListView.as_view(), name='forgery-list'),
]
