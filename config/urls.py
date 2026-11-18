from django.contrib import admin
from django.urls import path
from penaksir import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.prediksi, name='prediksi'),
    path('asisten/', views.asisten, name='asisten'),
    path('asisten/kirim/', views.asisten_kirim, name='asisten_kirim'),
    path('visualisasi/', views.visualisasi, name='visualisasi'),
    path('riwayat/', views.riwayat, name='riwayat'),
]