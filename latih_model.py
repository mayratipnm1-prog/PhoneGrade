import json
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeClassifier

print("Membaca 1 juta data dari used_phone_1M.csv...")
df_hp = pd.read_csv("used_phone_1M.csv")

# Label latihan mengelompokkan Excellent/Good sebagai layak dan Fair/Poor untuk servis.
df_hp["kelayakan"] = df_hp["condition"].map({
    "Excellent": "LAYAK_JUAL",
    "Good": "LAYAK_JUAL",
    "Fair": "PERLU_SERVIS",
    "Poor": "PERLU_SERVIS",
})

# Harga memakai usia dan baterai; kelayakan juga memakai kondisi layar.
X_harga = df_hp[["age_months", "battery_health"]]
y_harga = df_hp["resale_price"]
model_harga = LinearRegression().fit(X_harga, y_harga)
joblib.dump(model_harga, "model_harga_hp.joblib")

X_layak = df_hp[["age_months", "battery_health", "screen_cracked"]]
y_layak = df_hp["kelayakan"]
model_kelayakan = DecisionTreeClassifier(max_depth=2, random_state=42).fit(X_layak, y_layak)
joblib.dump(model_kelayakan, "model_kelayakan_hp.joblib")

# Statistik ini dipakai halaman ringkasan tanpa membaca CSV mentah saat server berjalan.
statistik = {
    "total": int(len(df_hp)),
    "layak": int((df_hp["kelayakan"] == "LAYAK_JUAL").sum()),
    "servis": int((df_hp["kelayakan"] == "PERLU_SERVIS").sum()),
    "rata_harga_inr": round(float(df_hp["resale_price"].mean()), 2),
    "rata_baterai": round(float(df_hp["battery_health"].mean()), 1),
}
with open("statistik_dataset.json", "w") as f:
    json.dump(statistik, f)

# Sampel ini mengisi grafik dan tabel dataset lokal.
df_sampel = df_hp.sample(n=1000, random_state=42)
df_sampel.to_csv("hp_bekas_sampel_grafik.csv", index=False)

print(f"Sukses! Statistik & model dari {len(df_hp):,} baris data berhasil disimpan.")