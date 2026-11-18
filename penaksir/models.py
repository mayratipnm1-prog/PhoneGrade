from django.db import models


class DatasetHP(models.Model):
    age_months = models.IntegerField()
    battery_health = models.IntegerField()
    screen_cracked = models.IntegerField()
    condition = models.CharField(max_length=20)
    resale_price = models.FloatField()
    kelayakan = models.CharField(max_length=20)

    def __str__(self):
        return f"Umur {self.age_months} bln | Baterai {self.battery_health}% | {self.kelayakan}"


class RiwayatPrediksi(models.Model):
    nama_hp = models.CharField(max_length=100)
    age_months = models.IntegerField()
    battery_health = models.IntegerField()
    screen_cracked = models.IntegerField()
    prediksi_harga = models.FloatField()
    prediksi_kelayakan = models.CharField(max_length=20)
    penjelasan_ai = models.TextField(blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_hp} - {self.prediksi_kelayakan}"