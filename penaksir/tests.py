from unittest.mock import Mock, patch

import httpx
from groq import RateLimitError
from django.test import TestCase
from django.urls import reverse

from .views import HasilPanggilanAI, panggil_ai


class VisualisasiTests(TestCase):
    @patch("penaksir.views.panggil_ai")
    @patch("penaksir.views.siapkan_data_grafik")
    @patch("penaksir.views.konteks_dasar")
    def test_each_chart_requests_only_its_own_explanation(
        self, konteks_mock, data_mock, ai_mock
    ):
        statistik = {
            "total": "100",
            "layak": "60",
            "servis": "40",
            "total_raw": 100,
            "layak_raw": 60,
            "servis_raw": 40,
            "rata_baterai": 75,
            "rata_harga_rp": "Rp 1.000.000",
        }
        konteks_mock.return_value = {"statistik": statistik}
        data_mock.return_value = (
            '[{"x": 50, "y": 1.0}, {"x": 80, "y": 2.0}]',
            "[]",
            "[60, 40]",
            '["Excellent", "Good"]',
            "[70, 30]",
            statistik,
        )
        kasus = (
            ("scatter", "Penjelasan grafik sebar:", "distribusi kelayakan"),
            ("kelayakan", "Penjelasan grafik kelayakan:", "kesehatan baterai"),
            ("kondisi", "Penjelasan grafik kondisi fisik:", "kesehatan baterai"),
        )

        for grafik, judul_hasil, topik_lain in kasus:
            with self.subTest(grafik=grafik):
                ai_mock.return_value = (
                    HasilPanggilanAI(status="rate_limited")
                    if grafik == "kondisi"
                    else HasilPanggilanAI(teks=f"Penjelasan uji {grafik}.")
                )
                response = self.client.post(
                    reverse("visualisasi"), {"grafik": grafik}
                )
                prompt = ai_mock.call_args.args[0]

                self.assertEqual(response.context["grafik_dijelaskan"], grafik)
                self.assertContains(response, judul_hasil)
                if grafik == "kondisi":
                    self.assertContains(response, "Kategori terbanyak: Excellent.")
                    self.assertContains(response, "Batas pemakaian Groq")
                else:
                    self.assertContains(response, f"Penjelasan uji {grafik}.")
                self.assertNotIn(topik_lain, prompt)
                ai_mock.reset_mock()

        hasil = response.context["penjelasan_grafik"]
        self.assertEqual(
            set(hasil),
            {"scatter", "kelayakan", "kondisi"},
        )


class FallbackTests(TestCase):
    @patch("penaksir.views.muat_api_key", return_value=("test-key", ""))
    @patch("groq.Groq")
    def test_groq_rate_limit_is_reported_without_retrying_other_models(
        self, groq_mock, key_mock
    ):
        client = Mock()
        client.chat.completions.create.side_effect = RateLimitError(
            "rate limit",
            response=httpx.Response(
                429,
                request=httpx.Request("POST", "https://api.groq.com"),
            ),
            body=None,
        )
        groq_mock.return_value = client

        hasil = panggil_ai("Jelaskan aturan prediksi.")

        self.assertEqual(hasil.status, "rate_limited")
        client.chat.completions.create.assert_called_once()
        client.models.list.assert_not_called()

    @patch(
        "penaksir.views.panggil_ai",
        return_value=HasilPanggilanAI(status="rate_limited"),
    )
    def test_chat_uses_relevant_faq_and_shows_rate_limit_notice(self, ai_mock):
        response = self.client.post(
            reverse("asisten_kirim"),
            data='{"pertanyaan":"Bagaimana harga dipengaruhi usia dan baterai?"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Aturan Prediksi Harga", response.json()["jawaban"])
        self.assertIn("Batas pemakaian Groq", response.json()["peringatan"])
        ai_mock.assert_called_once()
