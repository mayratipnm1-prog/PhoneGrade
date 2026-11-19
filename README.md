# PhoneGrade: Penaksir Harga dan Kelayakan HP Bekas

Aplikasi Django untuk menaksir harga jual kembali dan status kelayakan HP bekas (`LAYAK_JUAL` / `PERLU_SERVIS`). Aplikasi menyediakan grafik, riwayat pengecekan dengan SQLite, dan asisten toko yang menjawab berdasarkan FAQ PhoneGrade.

## Sumber Dataset
- **Nama Dataset:** Used Phone Price Prediction Dataset (1.000.000 baris)
- **Sumber Kaggle:** [Used Phone Price Prediction Dataset](https://www.kaggle.com/datasets/sharmajicoder/used-phone-price-prediction-dataset), oleh Stable Space.
- **Lisensi dataset:** Kaggle mencantumkan MIT. Pertahankan atribusi dan tautan sumber saat mendistribusikan dataset.
- File asli `used_phone_1M.csv` berukuran sekitar 116 MiB. Repo melacaknya dengan Git LFS karena ukurannya melebihi batas file biasa GitHub. Git LFS memakai kuota penyimpanan dan bandwidth akun GitHub.
- Repo menyertakan model terlatih (`.joblib`), statistik (`statistik_dataset.json`), sampel grafik (`hp_bekas_sampel_grafik.csv`), fixture data demo, dan snapshot SQLite `db.sqlite3`. Database berisi 1.000 data sampel dan 14 riwayat prediksi, tanpa akun, sesi, atau log admin.

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
.\venv\Scripts\python.exe manage.py runserver
```

Buka `http://127.0.0.1:8000/` setelah server berjalan. `db.sqlite3` sudah berisi data sampel dan riwayat, jadi tidak perlu menjalankan `loaddata` saat pertama kali clone.

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
python manage.py runserver
```

Jika Homebrew belum menyediakan Python 3.15, pasang Python 3.15.2 untuk macOS dari [python.org](https://www.python.org/downloads/), lalu pastikan perintah `python3.15 --version` berhasil. Buka `http://127.0.0.1:8000/` setelah server berjalan. Database sudah memuat data sampel dan riwayat demo.

Git LFS akan mengunduh dataset saat clone jika sudah terpasang. Jika repo terlanjur di-clone sebelum Git LFS dipasang, jalankan `git lfs install` lalu `git lfs pull` dari folder repo. Dataset mentah diperlukan untuk menjalankan `latih_model.py`; aplikasi biasa menggunakan model `.joblib` yang sudah disertakan.

API Groq tidak wajib. Tanpa API key, prediksi dan jawaban lokal tetap tersedia. Jika ingin mengaktifkan Groq, salin `.env.example` menjadi `.env`, lalu isi `API_KEY`. Jangan unggah `.env` atau API key ke GitHub.

`db.sqlite3` adalah snapshot awal bersama repo. Aplikasi menyimpan perubahan berikutnya secara lokal, dan perubahan itu tidak tersinkron kembali ke GitHub. Fixture `penaksir/fixtures/demo_data.json` tetap tersedia untuk mengisi tabel dataset dan riwayat jika database perlu dibuat ulang.

Untuk mengakses `/admin/`, buat akun lokal:

- Windows: `.\venv\Scripts\python.exe manage.py createsuperuser`
- macOS: aktifkan virtual environment dengan `source .venv/bin/activate`, lalu jalankan `python manage.py createsuperuser`

Kunci Django cadangan hanya untuk penggunaan lokal; jangan gunakan konfigurasi ini untuk deployment publik.