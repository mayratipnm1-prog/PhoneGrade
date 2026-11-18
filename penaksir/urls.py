from django.urls import path
from . import views

urlpatterns = [
    path('', views.prediksi, name='prediksi'),
    path('asisten/', views.asisten, name='asisten'),
    path('asisten/kirim/', views.asisten_kirim, name='asisten_kirim'),
    path('visualisasi/', views.visualisasi, name='visualisasi'),
    path('riwayat/', views.riwayat, name='riwayat'),
]