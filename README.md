# PhoneGrade: Penaksir Harga dan Kelayakan HP Bekas

Aplikasi Django untuk menaksir harga jual kembali dan status kelayakan HP bekas (`LAYAK_JUAL` / `PERLU_SERVIS`). Aplikasi menyediakan grafik, riwayat pengecekan dengan SQLite, dan asisten toko yang menjawab berdasarkan FAQ PhoneGrade.

## Sumber Dataset
- **Nama Dataset:** Used Phone Price Prediction Dataset (1.000.000 baris)
- **Sumber Kaggle:** [Used Phone Price Prediction Dataset](https://www.kaggle.com/datasets/sharmajicoder/used-phone-price-prediction-dataset), oleh Stable Space.
- **Lisensi dataset:** Kaggle mencantumkan MIT. Pertahankan atribusi dan tautan sumber saat mendistribusikan dataset.
- File asli `used_phone_1M.csv` berukuran sekitar 116 MiB. Repo melacaknya dengan Git LFS karena ukurannya melebihi batas file biasa GitHub. Git LFS memakai kuota penyimpanan dan bandwidth akun GitHub.
- Repo juga menyertakan model terlatih (`.joblib`), statistik (`statistik_dataset.json`), sampel grafik (`hp_bekas_sampel_grafik.csv`), dan fixture data demo. `db.sqlite3`, akun admin, sesi login, dan log admin tidak disertakan.

## Fitur Utama
1. **Prediksi Harga & Kelayakan (`LinearRegression` & `DecisionTreeClassifier`)**: Menaksir harga (dikonversi dari INR ke Rupiah dengan kurs Rp190/INR) dan status kelayakan.
2. **Asisten Toko**: Tanya-jawab beruntun tentang aturan PhoneGrade berdasarkan FAQ. API Groq bersifat opsional; tanpa API, aplikasi memakai jawaban lokal.
3. **Visualisasi Interaktif (Chart.js)**: Grafik hubungan kesehatan baterai dengan harga serta distribusi kelayakan dan kondisi dataset.
4. **Riwayat & Database Admin (SQLite)**: Menyimpan riwayat pengecekan ke `db.sqlite3` dan dapat dipantau melalui `/admin/`.

## Clone dan jalankan di Windows

Perintah Windows berikut diuji dengan Python 3.15.2. Pasang Git, Git LFS, dan Python terlebih dahulu.

```powershell
git lfs install
git clone https://github.com/mayratipnm1-prog/PhoneGrade.git
Set-Location PhoneGrade

py -3.15 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py loaddata penaksir\fixtures\demo_data.json
.\venv\Scripts\python.exe manage.py runserver
```

Buka `http://127.0.0.1:8000/` setelah server berjalan. Jalankan perintah `loaddata` sekali pada database baru. Perintah tersebut memuat sampel dan riwayat demo ke SQLite lokal.

## Clone dan jalankan di macOS

Langkah macOS ini menggunakan Python 3.15.2, tetapi belum diuji di Mac. Jika Homebrew terpasang, gunakan:

```bash
brew install git git-lfs python@3.15
git lfs install
git clone https://github.com/mayratipnm1-prog/PhoneGrade.git
cd PhoneGrade
git lfs pull

python3.15 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata penaksir/fixtures/demo_data.json
python manage.py runserver
```

Jika Homebrew belum menyediakan Python 3.15, pasang Python 3.15.2 untuk macOS dari [python.org](https://www.python.org/downloads/), lalu pastikan perintah `python3.15 --version` berhasil. Buka `http://127.0.0.1:8000/` setelah server berjalan. Perintah `loaddata` cukup dijalankan sekali pada database baru.

Git LFS akan mengunduh dataset saat clone jika sudah terpasang. Jika repo terlanjur di-clone sebelum Git LFS dipasang, jalankan `git lfs install` lalu `git lfs pull` dari folder repo. Dataset mentah diperlukan untuk menjalankan `latih_model.py`; aplikasi biasa menggunakan model `.joblib` yang sudah disertakan.

API Groq tidak wajib. Tanpa API key, prediksi dan jawaban lokal tetap tersedia. Jika ingin mengaktifkan Groq, salin `.env.example` menjadi `.env`, lalu isi `API_KEY`. Jangan unggah `.env` atau API key ke GitHub.

`db.sqlite3` dibuat di komputer masing-masing dan tidak dibagikan. Fixture `penaksir/fixtures/demo_data.json` mengisi tabel dataset dan riwayat dengan data demo yang sama. Fixture tidak memuat akun, sesi login, atau log admin. Perubahan data setelah aplikasi dijalankan hanya tersimpan di database lokal dan tidak tersinkron kembali ke GitHub.

Jika dosen perlu membuka `/admin/`, buat akun lokal:

- Windows: `.\venv\Scripts\python.exe manage.py createsuperuser`
- macOS: aktifkan virtual environment dengan `source .venv/bin/activate`, lalu jalankan `python manage.py createsuperuser`

Kunci Django cadangan hanya untuk penggunaan lokal; jangan gunakan konfigurasi ini untuk deployment publik.