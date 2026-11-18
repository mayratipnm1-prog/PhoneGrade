import json
import logging
import os
import re
from dataclasses import dataclass

import joblib
import pandas as pd
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from dotenv import load_dotenv

from .models import DatasetHP, RiwayatPrediksi

# Model menghasilkan harga dalam INR; hasil ditampilkan dalam rupiah dengan kurs proyek.
KURS_INR_KE_IDR = 190
MODEL_GROQ = "openai/gpt-oss-20b"
logger = logging.getLogger(__name__)

FAQ_HP_BEKAS = [
    "Aturan Prediksi Harga (Regresi Linear): Harga jual kembali ditaksir dari usia pemakaian (age_months) dan kesehatan baterai (battery_health) yang dilatih dari 1.000.000 data Kaggle.",
    "Aturan Konversi Mata Uang: Dataset asli Kaggle menggunakan satuan Rupee India (INR), sehingga PhoneGrade mengalikannya dengan kurs Rp190/INR agar tampil dalam Rupiah.",
    "Aturan Klasifikasi Kelayakan (Decision Tree): Status LAYAK_JUAL (kondisi Excellent/Good) dan PERLU_SERVIS (kondisi Fair/Poor) ditentukan dari usia pemakaian, kesehatan baterai, dan kondisi layar.",
    "Aturan Kesehatan Baterai: HP dengan battery health di bawah 80% disarankan ganti baterai terlebih dahulu karena menurunkan nilai jual kembali.",
    "Aturan Layar Retak: Layar yang retak (screen_cracked = 1) menurunkan skor kelayakan dan cenderung masuk kategori PERLU_SERVIS.",
    "Aturan Penyimpanan Data: Setiap hasil pengecekan pada menu Prediksi Harga otomatis tersimpan ke tabel RiwayatPrediksi di database SQLite (db.sqlite3).",
]

KATA_KUNCI_FAQ = [
    (0, ("harga", "usia", "umur", "baterai", "battery", "regresi", "prediksi", "taksir")),
    (1, ("kurs", "rupee", "inr", "rupiah", "konversi")),
    (2, ("kelayakan", "layak jual", "perlu servis", "decision tree", "status")),
    (3, ("baterai", "battery health", "80%", "ganti baterai")),
    (4, ("layar", "retak", "screen cracked")),
    (5, ("riwayat", "simpan", "database", "sqlite")),
]


@dataclass(frozen=True)
class HasilPanggilanAI:
    teks: str = ""
    status: str = "ok"


def format_rupiah(nominal):
    return f"Rp {nominal:,.0f}".replace(",", ".")


def format_ribuan(angka):
    return f"{int(angka):,}".replace(",", ".")


def muat_api_key():
    env_path = os.path.join(settings.BASE_DIR, ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    groq_key = os.getenv("API_KEY", "").strip()
    openai_key = os.getenv("OPEN_API_KEY", "").strip()
    return groq_key, openai_key


def panggil_ai(prompt_teks):
    groq_key, _ = muat_api_key()
    if not groq_key:
        return HasilPanggilanAI(status="offline")

    from groq import APIError, Groq, RateLimitError

    client = Groq(api_key=groq_key)
    try:
        response = client.chat.completions.create(
            model=MODEL_GROQ,
            messages=[{"role": "user", "content": prompt_teks}],
        )
    except RateLimitError:
        logger.warning("Groq rate limit reached for model %s.", MODEL_GROQ)
        return HasilPanggilanAI(status="rate_limited")
    except APIError as error:
        logger.error(
            "Groq request failed with status %s.",
            getattr(error, "status_code", "unknown"),
        )
        return HasilPanggilanAI(status="unavailable")

    return HasilPanggilanAI(teks=response.choices[0].message.content or "")


def pesan_status_ai(status):
    pesan = {
        "rate_limited": "Batas pemakaian Groq tercapai. Jawaban ini menggunakan informasi lokal.",
        "offline": "API Groq belum diaktifkan. Jawaban ini menggunakan informasi lokal.",
        "unavailable": "Groq sedang tidak dapat diakses. Jawaban ini menggunakan informasi lokal.",
    }
    return pesan.get(status, "Jawaban ini menggunakan informasi lokal.")


def jawab_faq_lokal(pertanyaan):
    pertanyaan_normal = " ".join(re.findall(r"[a-z0-9]+", pertanyaan.lower()))
    cocok = []
    for indeks, kata_kunci in KATA_KUNCI_FAQ:
        kata_kunci_normal = [
            " ".join(re.findall(r"[a-z0-9]+", kata))
            for kata in kata_kunci
        ]
        skor = sum(
            f" {kata} " in f" {pertanyaan_normal} "
            for kata in kata_kunci_normal
        )
        if skor:
            cocok.append((skor, FAQ_HP_BEKAS[indeks]))

    cocok.sort(key=lambda item: item[0], reverse=True)
    if not cocok:
        return "Silakan hubungi admin toko untuk info lebih lanjut."
    return " ".join(item[1] for item in cocok[:2])


def isi_database_awal():
    if DatasetHP.objects.count() == 0:
        # Sampel ini mengisi grafik saat database baru dibuat tanpa memuat CSV mentah.
        csv_path = os.path.join(settings.BASE_DIR, "hp_bekas_sampel_grafik.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            data_list = [
                DatasetHP(
                    age_months=int(row["age_months"]),
                    battery_health=int(row["battery_health"]),
                    screen_cracked=int(row["screen_cracked"]),
                    condition=str(row["condition"]),
                    resale_price=float(row["resale_price"]),
                    kelayakan=str(row["kelayakan"]),
                )
                for _, row in df.iterrows()
            ]
            DatasetHP.objects.bulk_create(data_list)


def ambil_statistik():
    stat_path = os.path.join(settings.BASE_DIR, "statistik_dataset.json")
    if os.path.exists(stat_path):
        with open(stat_path, "r") as f:
            stat_json = json.load(f)
        total_asli = stat_json["total"]
        layak_asli = stat_json["layak"]
        servis_asli = stat_json["servis"]
        rata_harga_inr = stat_json["rata_harga_inr"]
        rata_baterai = stat_json["rata_baterai"]
    else:
        data = list(DatasetHP.objects.values("battery_health", "resale_price", "kelayakan"))
        if not data:
            return {"total": "0", "layak": "0", "servis": "0", "total_raw": 0, "layak_raw": 0, "servis_raw": 0, "rata_harga_rp": "Rp 0", "rata_baterai": 0}
        df = pd.DataFrame(data)
        total_asli = len(df)
        layak_asli = int((df["kelayakan"] == "LAYAK_JUAL").sum())
        servis_asli = int((df["kelayakan"] == "PERLU_SERVIS").sum())
        rata_harga_inr = float(df["resale_price"].mean())
        rata_baterai = round(float(df["battery_health"].mean()), 1)

    return {
        "total": format_ribuan(total_asli),
        "layak": format_ribuan(layak_asli),
        "servis": format_ribuan(servis_asli),
        "total_raw": int(total_asli),
        "layak_raw": int(layak_asli),
        "servis_raw": int(servis_asli),
        "rata_harga_rp": format_rupiah(rata_harga_inr * KURS_INR_KE_IDR),
        "rata_baterai": rata_baterai,
    }


def siapkan_data_grafik():
    data = list(DatasetHP.objects.values("battery_health", "resale_price", "kelayakan", "condition"))
    statistik = ambil_statistik()
    if not data:
        return "[]", "[]", "[0, 0]", "[]", "[]", statistik
    df = pd.DataFrame(data)
    df["harga_juta_rp"] = (df["resale_price"] * KURS_INR_KE_IDR) / 1_000_000

    scatter_layak = [
        {"x": int(r["battery_health"]), "y": round(float(r["harga_juta_rp"]), 2)}
        for _, r in df[df["kelayakan"] == "LAYAK_JUAL"].iterrows()
    ]
    scatter_servis = [
        {"x": int(r["battery_health"]), "y": round(float(r["harga_juta_rp"]), 2)}
        for _, r in df[df["kelayakan"] == "PERLU_SERVIS"].iterrows()
    ]
    bar_values = [statistik["layak_raw"], statistik["servis_raw"]]

    urutan_kondisi = ["Excellent", "Good", "Fair", "Poor"]
    kondisi_counts = df["condition"].value_counts()
    doughnut_labels = [k for k in urutan_kondisi if k in kondisi_counts.index]
    doughnut_values = [int(kondisi_counts[k]) for k in doughnut_labels]

    return (
        json.dumps(scatter_layak),
        json.dumps(scatter_servis),
        json.dumps(bar_values),
        json.dumps(doughnut_labels),
        json.dumps(doughnut_values),
        statistik,
    )


def konteks_dasar(aktif_menu):
    isi_database_awal()
    groq_key, _ = muat_api_key()
    return {
        "aktif_menu": aktif_menu,
        "status_ai": "Groq AI Aktif" if groq_key else "Mode Offline (.env belum terbaca)",
        "ai_aktif": bool(groq_key),
        "statistik": ambil_statistik(),
    }



def prediksi(request):
    ctx = konteks_dasar("prediksi")
    hasil_prediksi = None
    hasil_harga_rp = None
    hasil_harga_inr = None
    peringatan_ai = None

    if request.method == "POST":
        nama_hp = request.POST.get("nama_hp", "HP Bekas")
        umur = int(request.POST.get("age_months", 12))
        baterai = int(request.POST.get("battery_health", 85))
        layar_retak = int(request.POST.get("screen_cracked", 0))

        model_harga = joblib.load(os.path.join(settings.BASE_DIR, "model_harga_hp.joblib"))
        model_kelayakan = joblib.load(os.path.join(settings.BASE_DIR, "model_kelayakan_hp.joblib"))

        df_harga = pd.DataFrame({"age_months": [umur], "battery_health": [baterai]})
        taksiran_inr = max(0, float(model_harga.predict(df_harga)[0]))
        taksiran_idr = taksiran_inr * KURS_INR_KE_IDR

        df_layak = pd.DataFrame({
            "age_months": [umur],
            "battery_health": [baterai],
            "screen_cracked": [layar_retak],
        })
        status_kelayakan = str(model_kelayakan.predict(df_layak)[0])
        # Aturan proyek menetapkan unit retak, baterai di bawah 75%, atau usia >= 36 bulan untuk servis.
        if layar_retak == 1 or baterai < 75 or umur >= 36:
            status_kelayakan = "PERLU_SERVIS"

        hasil_harga_rp = format_rupiah(taksiran_idr)
        hasil_harga_inr = f"₹{taksiran_inr:,.0f}".replace(",", ".")

        prompt_ai = (
            f"Kamu asisten ahli jual-beli HP bekas. Jelaskan secara singkat (maksimal 3 kalimat, bahasa Indonesia baku dan mudah dipahami) "
            f"mengapa HP '{nama_hp}' dengan usia {umur} bulan, battery health {baterai}%, dan "
            f"status layar {'retak' if layar_retak == 1 else 'mulus'} mendapatkan taksiran harga {hasil_harga_rp} "
            f"dan status kelayakan {status_kelayakan}, lalu beri 1 saran singkat."
        )
        hasil_ai = panggil_ai(prompt_ai)
        if hasil_ai.status == "ok":
            penjelasan = hasil_ai.teks
        else:
            penjelasan = (
                f"Model harga memakai usia pemakaian dan kesehatan baterai. "
                f"Hasil kelayakan unit ini: {status_kelayakan}."
            )
            peringatan_ai = pesan_status_ai(hasil_ai.status)

        hasil_prediksi = RiwayatPrediksi.objects.create(
            nama_hp=nama_hp,
            age_months=umur,
            battery_health=baterai,
            screen_cracked=layar_retak,
            prediksi_harga=round(taksiran_idr, 0),
            prediksi_kelayakan=status_kelayakan,
            penjelasan_ai=penjelasan,
        )

    ctx.update({
        "hasil_prediksi": hasil_prediksi,
        "hasil_harga_rp": hasil_harga_rp,
        "hasil_harga_inr": hasil_harga_inr,
        "peringatan_ai": peringatan_ai,
    })
    return render(request, "penaksir/prediksi.html", ctx)


def asisten(request):
    ctx = konteks_dasar("asisten")
    if request.method == "POST" and request.POST.get("aksi") == "reset":
        request.session["chat_history"] = []

    ctx.update({
        "chat_history": request.session.get("chat_history", []),
        "faq_list": FAQ_HP_BEKAS,
    })
    return render(request, "penaksir/asisten.html", ctx)


def asisten_kirim(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metode harus POST"}, status=405)

    data = json.loads(request.body.decode("utf-8"))
    pertanyaan_user = data.get("pertanyaan", "").strip()
    if not pertanyaan_user:
        return JsonResponse({"error": "Pertanyaan kosong"}, status=400)

    konteks_faq = "\n".join(f"- {item}" for item in FAQ_HP_BEKAS)
    riwayat = request.session.get("chat_history", [])
    riwayat_singkat = "\n".join(
        f"Pelanggan: {c['user']}\nCS: {c['ai']}" for c in riwayat[-4:]
    )

    prompt_rag = (
        f"Kamu adalah Customer Service Toko HP Bekas.\n"
        f"Jawab pertanyaan pelanggan HANYA berdasarkan daftar FAQ resmi berikut:\n"
        f"{konteks_faq}\n\n"
        f"Riwayat percakapan sebelumnya:\n{riwayat_singkat}\n\n"
        f"Jika jawabannya tidak ada di FAQ, katakan: 'Silakan hubungi admin toko untuk info lebih lanjut.'\n"
        f"Jawab maksimal 2 kalimat dengan ramah.\n"
        f"Pertanyaan terbaru: {pertanyaan_user}"
    )
    hasil_ai = panggil_ai(prompt_rag)
    peringatan_ai = None
    if hasil_ai.status == "ok":
        jawaban_chatbot = hasil_ai.teks
    else:
        # FAQ lokal menjaga asisten tetap bisa menjawab saat Groq offline atau terkena limit.
        jawaban_chatbot = jawab_faq_lokal(pertanyaan_user)
        peringatan_ai = pesan_status_ai(hasil_ai.status)

    riwayat.append({
        "user": pertanyaan_user,
        "ai": jawaban_chatbot,
        "peringatan": peringatan_ai,
    })
    request.session["chat_history"] = riwayat
    request.session.modified = True

    return JsonResponse({
        "jawaban": jawaban_chatbot,
        "peringatan": peringatan_ai,
    })


def penjelasan_lokal_grafik(
    grafik,
    statistik,
    scatter_layak_json,
    scatter_servis_json,
    doughnut_labels_json,
    doughnut_values_json,
):
    if grafik == "scatter":
        titik = json.loads(scatter_layak_json) + json.loads(scatter_servis_json)
        data = pd.DataFrame(titik)
        if len(data) < 2:
            return f"Grafik membandingkan kesehatan baterai dan harga pada {len(titik)} unit."

        korelasi = data["x"].corr(data["y"])
        if pd.isna(korelasi):
            return (
                f"Grafik membandingkan kesehatan baterai dan harga pada {len(titik)} unit. "
                "Korelasi tidak dapat dihitung dari titik yang tersedia."
            )

        arah = "positif" if korelasi > 0 else "negatif" if korelasi < 0 else "tidak tampak"
        return (
            f"Grafik membandingkan kesehatan baterai dan harga pada {len(titik)} unit. "
            f"Korelasi Pearson sebesar {korelasi:.2f} menunjukkan hubungan {arah}; "
            "korelasi tidak membuktikan sebab-akibat."
        )

    if grafik == "kelayakan":
        layak = statistik["layak_raw"]
        servis = statistik["servis_raw"]
        total = layak + servis
        if not total:
            return "Belum ada data untuk ditampilkan pada grafik kelayakan."
        kategori_terbanyak = "LAYAK_JUAL" if layak >= servis else "PERLU_SERVIS"
        return (
            f"Dari {format_ribuan(total)} unit, {format_ribuan(layak)} berstatus "
            f"LAYAK_JUAL dan {format_ribuan(servis)} PERLU_SERVIS. "
            f"Kategori terbanyak adalah {kategori_terbanyak}."
        )

    label_kondisi = json.loads(doughnut_labels_json)
    jumlah_kondisi = json.loads(doughnut_values_json)
    if not jumlah_kondisi:
        return "Belum ada data kondisi fisik untuk ditampilkan."
    indeks_terbanyak = jumlah_kondisi.index(max(jumlah_kondisi))
    rincian = ", ".join(
        f"{label}: {format_ribuan(jumlah)} unit"
        for label, jumlah in zip(label_kondisi, jumlah_kondisi)
    )
    return (
        f"Distribusi kondisi fisik adalah {rincian}. "
        f"Kategori terbanyak: {label_kondisi[indeks_terbanyak]}."
    )


def visualisasi(request):
    ctx = konteks_dasar("visualisasi")
    scatter_layak_json, scatter_servis_json, bar_values_json, doughnut_labels_json, doughnut_values_json, statistik = siapkan_data_grafik()
    penjelasan_grafik = request.session.get("penjelasan_grafik", {})
    grafik_dijelaskan = None

    if request.method == "POST":
        grafik_dijelaskan = request.POST.get("grafik")
        if grafik_dijelaskan in {"scatter", "kelayakan", "kondisi"}:
            pembuka_prompt = (
                "Kamu dosen/analis data. Jelaskan grafik yang dipilih secara singkat, "
                "jelas, dan spesifik dalam bahasa Indonesia, maksimal 3 kalimat. "
                "Jangan membahas grafik lain atau menyimpulkan hal yang tidak didukung data."
            )

            if grafik_dijelaskan == "scatter":
                titik = json.loads(scatter_layak_json) + json.loads(scatter_servis_json)
                data_scatter = pd.DataFrame(titik)
                korelasi = None
                if len(data_scatter) > 1:
                    nilai_korelasi = data_scatter["x"].corr(data_scatter["y"])
                    if pd.notna(nilai_korelasi):
                        korelasi = round(float(nilai_korelasi), 2)
                prompt_grafik = (
                    f"{pembuka_prompt} Grafik sebar ini membandingkan kesehatan baterai "
                    f"(sumbu X, persen) dengan harga jual (sumbu Y, juta rupiah) "
                    f"dari {len(titik)} unit. Korelasi Pearson pada titik yang tersedia: "
                    f"{korelasi if korelasi is not None else 'tidak dapat dihitung'}. "
                    "Terangkan cara membaca pola hubungan kedua variabel."
                )
            elif grafik_dijelaskan == "kelayakan":
                prompt_grafik = (
                    f"{pembuka_prompt} Grafik batang menunjukkan distribusi kelayakan "
                    f"dari {statistik['total']} unit: {statistik['layak']} unit LAYAK_JUAL "
                    f"dan {statistik['servis']} unit PERLU_SERVIS. Terangkan perbandingan "
                    "jumlah kedua kategori tersebut."
                )
            else:
                label_kondisi = json.loads(doughnut_labels_json)
                jumlah_kondisi = json.loads(doughnut_values_json)
                distribusi_kondisi = ", ".join(
                    f"{label}: {jumlah} unit"
                    for label, jumlah in zip(label_kondisi, jumlah_kondisi)
                ) or "tidak ada data kondisi fisik"
                prompt_grafik = (
                    f"{pembuka_prompt} Grafik donat menunjukkan kondisi fisik HP: "
                    f"{distribusi_kondisi}. Terangkan kategori yang paling banyak "
                    "dan perbandingan antar kategori berdasarkan data tersebut."
                )

            hasil_ai = panggil_ai(prompt_grafik)
            if hasil_ai.status == "ok":
                teks_penjelasan = hasil_ai.teks
                peringatan = None
            else:
                teks_penjelasan = penjelasan_lokal_grafik(
                    grafik_dijelaskan,
                    statistik,
                    scatter_layak_json,
                    scatter_servis_json,
                    doughnut_labels_json,
                    doughnut_values_json,
                )
                peringatan = pesan_status_ai(hasil_ai.status)

            penjelasan_grafik[grafik_dijelaskan] = {
                "teks": teks_penjelasan,
                "peringatan": peringatan,
            }
            # Hasil disimpan per grafik agar penjelasan sebelumnya tetap terlihat.
            request.session["penjelasan_grafik"] = penjelasan_grafik
        else:
            grafik_dijelaskan = None

    ctx.update({
        "scatter_layak_json": scatter_layak_json,
        "scatter_servis_json": scatter_servis_json,
        "bar_values_json": bar_values_json,
        "doughnut_labels_json": doughnut_labels_json,
        "doughnut_values_json": doughnut_values_json,
        "penjelasan_grafik": penjelasan_grafik,
        "grafik_dijelaskan": grafik_dijelaskan,
    })
    return render(request, "penaksir/visualisasi.html", ctx)


def riwayat(request):
    ctx = konteks_dasar("riwayat")
    riwayat_list = RiwayatPrediksi.objects.order_by("-dibuat_pada")[:50]
    for r in riwayat_list:
        nilai_idr = r.prediksi_harga * KURS_INR_KE_IDR if r.prediksi_harga < 200000 else r.prediksi_harga
        r.harga_rp = format_rupiah(nilai_idr)

    ctx["riwayat_list"] = riwayat_list
    return render(request, "penaksir/riwayat.html", ctx)