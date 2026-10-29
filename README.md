# TrendWatch X — Android-friendly starter

Aplikasi Streamlit untuk memantau postingan X melalui API resmi, menyaring kata kunci/produk, menyimpan hasil ke SQLite tanpa duplikasi, memperbarui status, dan mengekspor CSV.

## Penting
- Aplikasi **tidak** menampilkan data demo seolah-olah data live.
- Akses endpoint `GET /2/tweets/search/recent`, harga, kuota, dan jangkauan data ditentukan oleh paket/izin akun X. Pastikan portal developer menunjukkan akses yang sesuai sebelum mengandalkan integrasi ini.
- Tombol pencarian mengambil data saat diklik. Untuk berjalan otomatis berkala, perlu scheduler/worker pada hosting yang mendukungnya.
- Jangan pernah mengunggah Bearer Token ke repositori publik atau membagikannya lewat chat.

## Jalankan dari HP Android
Cara yang relatif mudah adalah memakai GitHub + Streamlit Community Cloud melalui browser HP:
1. Unduh ZIP ini lalu ekstrak jika memakai layanan yang mendukung upload file.
2. Buat repositori GitHub baru di https://github.com/ dan unggah `app.py`, `requirements.txt`, `.gitignore`, serta folder `.streamlit` tanpa file secrets asli.
3. Buka https://share.streamlit.io/ dan deploy repositori, pilih `app.py`.
4. Di pengaturan aplikasi Streamlit, masukkan `X_BEARER_TOKEN` pada bagian Secrets, dengan format:
   `X_BEARER_TOKEN = "token_rahasia_kamu"`
5. Restart/redeploy aplikasi. Jangan masukkan token ke `app.py` atau chat.

Layanan hosting gratis dapat berubah ketentuannya dan aplikasi dapat tidur saat tidak aktif. Penyimpanan lokal SQLite pada hosting gratis juga mungkin tidak persisten saat aplikasi dibangun ulang; untuk operasi jangka panjang, gunakan database persisten.

## Query contoh
`(("butuh" OR "cari" OR "WTB") (Netflix OR Canva OR Spotify)) lang:id -is:retweet`

Sesuaikan sintaks query berdasarkan operator yang didukung endpoint/paket X API akunmu.
