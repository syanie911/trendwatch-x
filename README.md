# TrendWatch X — versi gratis tanpa X API

Dashboard Streamlit untuk menganalisis teks postingan publik yang dimasukkan sendiri atau diimpor dari CSV.

## Fitur
- Input beberapa teks postingan sekaligus
- Impor CSV dengan kolom wajib `text`
- Deteksi kata kunci, produk, dan hashtag
- Ringkasan grafik dan filter
- Ubah status dan ekspor data ke CSV

## Jalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

Versi ini tidak memakai Bearer Token, tidak memanggil X API, dan tidak melakukan scraping. Pengguna memasukkan sendiri teks yang ingin dianalisis. Hormati aturan platform dan privasi.
