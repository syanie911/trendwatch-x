import os
import re
import sqlite3
import hashlib
from datetime import datetime, timezone
from collections import Counter

import pandas as pd
import streamlit as st

st.set_page_config(page_title="TrendWatch X", page_icon="🌷", layout="wide")

st.markdown("""
<style>
.stApp{background:linear-gradient(145deg,#e8def8,#fbe3f1 60%,#fff5fa);color:#603f59}
.block-container{max-width:1200px;padding-top:1.5rem}
h1,h2,h3{color:#743d68!important}
div[data-testid="stMetric"],div[data-testid="stVerticalBlockBorderWrapper"]{
 background:#fffafd;border:1px solid #edc4dc;border-radius:20px;
 box-shadow:0 6px 22px rgba(127,65,111,.06)
}
div[data-testid="stMetric"]{padding:14px}
.stButton>button,.stDownloadButton>button{border-radius:14px;background:#fff1f8;color:#873a70;border:1px solid #e8b2d2}
[data-testid="stSidebar"]{background:#fff8fc}
</style>
""", unsafe_allow_html=True)

DB_PATH = os.getenv("TRENDWATCH_DB", "trendwatch.db")
DEFAULT_PRODUCTS = "Netflix,Canva,CapCut,Spotify,ChatGPT,YouTube,Prime Video,Vidio,Disney+"
DEFAULT_KEYWORDS = "butuh,cari,mau beli,ada yang jual,WTB,want to buy,rekomendasi,nyari,need"
DEFAULT_HASHTAGS = "zonauang,canva,spotify,netflix"
STATUSES = ["Baru", "Ditindaklanjuti", "Selesai", "Perlu ditinjau"]

def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT PRIMARY KEY, created_at TEXT, username TEXT,
        text TEXT NOT NULL, likes INTEGER DEFAULT 0, reposts INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0, lang TEXT, matched_product TEXT,
        matched_terms TEXT, status TEXT DEFAULT 'Baru',
        source TEXT DEFAULT 'Input manual', imported_at TEXT
    )""")
    conn.commit()
    return conn

def comma_list(value):
    return [x.strip() for x in value.split(",") if x.strip()]

def match_post(text, products, keywords, hashtags):
    lower = text.lower()
    product_hits = [p for p in products if p.lower() in lower]
    keyword_hits = [k for k in keywords if k.lower() in lower]
    hashtag_hits = [h.lstrip("#") for h in hashtags if ("#" + h.lstrip("#").lower()) in lower]
    terms = keyword_hits + [f"#{h}" for h in hashtag_hits]
    return ", ".join(product_hits), ", ".join(dict.fromkeys(terms)), bool(product_hits and (keyword_hits or hashtag_hits))

def load_posts():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM posts ORDER BY created_at DESC, imported_at DESC", conn)
    conn.close()
    return df

def save_posts(texts, products, keywords, hashtags, source="Input manual"):
    conn = connect_db()
    added = 0
    now = datetime.now(timezone.utc).isoformat()
    for item in texts:
        text_value = str(item.get("text", "")).strip()
        if not text_value:
            continue
        raw_id = str(item.get("post_id") or hashlib.sha256(text_value.encode("utf-8")).hexdigest())
        post_id = raw_id if raw_id else hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        product, terms, opportunity = match_post(text_value, products, keywords, hashtags)
        row = {
            "post_id": post_id, "created_at": str(item.get("created_at") or now),
            "username": str(item.get("username") or "Input manual"),
            "text": text_value, "likes": int(item.get("likes") or 0),
            "reposts": int(item.get("reposts") or 0), "replies": int(item.get("replies") or 0),
            "lang": str(item.get("lang") or ""), "matched_product": product,
            "matched_terms": terms, "status": "Baru" if opportunity else "Perlu ditinjau",
            "source": str(item.get("source") or source), "imported_at": now
        }
        before = conn.total_changes
        conn.execute("""INSERT OR IGNORE INTO posts
        (post_id,created_at,username,text,likes,reposts,replies,lang,matched_product,matched_terms,status,source,imported_at)
        VALUES (:post_id,:created_at,:username,:text,:likes,:reposts,:replies,:lang,:matched_product,:matched_terms,:status,:source,:imported_at)""", row)
        if conn.total_changes > before:
            added += 1
    conn.commit()
    conn.close()
    return added

st.title("🌷 TrendWatch X")
st.caption("Dashboard riset tren dari teks postingan publik yang kamu masukkan sendiri — tanpa X API dan tanpa biaya API.")

with st.sidebar:
    st.header("Pengaturan pantauan")
    products_raw = st.text_area("Produk (pisahkan dengan koma)", DEFAULT_PRODUCTS, height=90)
    keywords_raw = st.text_area("Kata kunci minat (pisahkan dengan koma)", DEFAULT_KEYWORDS, height=100)
    hashtags_raw = st.text_area("Hashtag tanpa # (pisahkan dengan koma)", DEFAULT_HASHTAGS, height=80)
    st.divider()
    st.caption("Analisis dilakukan pada data yang kamu masukkan. Dashboard tidak mengambil postingan otomatis dari X.")

products = comma_list(products_raw)
keywords = comma_list(keywords_raw)
hashtags = comma_list(hashtags_raw)

st.subheader("Tambah data postingan")
st.write("Salin teks postingan publik yang ingin dianalisis, lalu tempelkan di bawah. Pisahkan setiap postingan dengan satu baris kosong.")
with st.form("manual_import"):
    pasted = st.text_area("Teks postingan", height=180, placeholder="Contoh: Lagi cari akun Canva Pro yang aman, ada rekomendasi?\n\nButuh rekomendasi aplikasi edit video selain CapCut.")
    username = st.text_input("Nama akun (opsional)", placeholder="@nama_akun")
    submitted = st.form_submit_button("✨ Analisis dan simpan postingan", use_container_width=True)
if submitted:
    blocks = [x.strip() for x in re.split(r"\n\s*\n", pasted) if x.strip()]
    if not blocks:
        st.warning("Tempelkan setidaknya satu teks postingan terlebih dahulu.")
    else:
        rows = [{"text": block, "username": username or "Input manual"} for block in blocks]
        added = save_posts(rows, products, keywords, hashtags)
        st.success(f"Selesai! {len(blocks)} teks diproses; {added} data baru disimpan.")
        st.rerun()

with st.expander("Impor banyak data dari CSV"):
    st.caption("CSV minimal harus memiliki kolom `text`. Kolom opsional: username, created_at, likes, reposts, replies, post_id.")
    uploaded = st.file_uploader("Pilih file CSV", type=["csv"])
    if uploaded is not None:
        try:
            csv_df = pd.read_csv(uploaded).fillna("")
            if "text" not in csv_df.columns:
                st.error("CSV harus memiliki kolom bernama text.")
            else:
                st.dataframe(csv_df.head(5), use_container_width=True)
                if st.button("Impor CSV ini"):
                    rows = csv_df.to_dict(orient="records")
                    added = save_posts(rows, products, keywords, hashtags, source="Impor CSV")
                    st.success(f"{added} data baru berhasil disimpan.")
                    st.rerun()
        except Exception as exc:
            st.error(f"CSV tidak dapat dibaca: {exc}")

st.divider()
df = load_posts()
if df.empty:
    st.info("Belum ada data. Tambahkan teks postingan di atas atau impor file CSV untuk mulai melihat analisis.")
else:
    total = len(df)
    new_count = int((df["status"] == "Baru").sum())
    tracked_products = int(df["matched_product"].fillna("").ne("").sum())
    likes_total = int(pd.to_numeric(df["likes"], errors="coerce").fillna(0).sum())
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Postingan tersimpan", total)
    c2.metric("Peluang terdeteksi", new_count)
    c3.metric("Cocok produk", tracked_products)
    c4.metric("Total likes (jika diisi)", likes_total)

    st.subheader("Kata kunci yang sering muncul")
    term_counts = Counter()
    for _, row in df.iterrows():
        term_counts.update([x.strip() for x in str(row["matched_terms"]).split(",") if x.strip()])
    if term_counts:
        st.bar_chart(pd.DataFrame(term_counts.most_common(12), columns=["Kata kunci", "Jumlah"]).set_index("Kata kunci"))
    else:
        st.caption("Belum ada kata kunci pantauan yang cocok. Kamu bisa menambah kata di pengaturan sebelah kiri.")

    product_counts = Counter()
    for value in df["matched_product"].fillna(""):
        product_counts.update([x.strip() for x in value.split(",") if x.strip()])
    if product_counts:
        st.subheader("Produk yang sering disebut")
        st.bar_chart(pd.DataFrame(product_counts.most_common(10), columns=["Produk", "Jumlah"]).set_index("Produk"))

    st.subheader("Filter data")
    f1,f2,f3 = st.columns([2,1,1])
    with f1:
        search = st.text_input("Cari teks, akun, atau produk", "")
    with f2:
        status_filter = st.selectbox("Status", ["Semua"] + STATUSES)
    with f3:
        product_options = ["Semua"] + sorted([p for p in df["matched_product"].dropna().unique() if p])
        product_filter = st.selectbox("Produk", product_options)
    view = df.copy()
    if search:
        mask = view[["text","username","matched_product","matched_terms"]].fillna("").astype(str).apply(lambda c: c.str.contains(search, case=False, regex=False)).any(axis=1)
        view = view[mask]
    if status_filter != "Semua":
        view = view[view["status"] == status_filter]
    if product_filter != "Semua":
        view = view[view["matched_product"].fillna("").str.contains(product_filter, case=False, regex=False)]

    st.subheader(f"Postingan ({len(view)})")
    for _, row in view.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['username']}** · <span style='color:#987f94'>{row['created_at']}</span>", unsafe_allow_html=True)
            st.write(row["text"])
            tags = []
            if row.get("matched_product"): tags.append("Produk: " + row["matched_product"])
            if row.get("matched_terms"): tags.append("Cocok: " + row["matched_terms"])
            if tags: st.caption(" · ".join(tags))
            st.caption(f"Likes {row['likes']} · Repost {row['reposts']} · Balasan {row['replies']} · Sumber: {row['source']}")
            current_status = row["status"] if row["status"] in STATUSES else "Perlu ditinjau"
            new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(current_status), key=f"status_{row['post_id']}")
            if new_status != current_status and st.button("Simpan status", key=f"save_{row['post_id']}"):
                conn = connect_db()
                conn.execute("UPDATE posts SET status=? WHERE post_id=?", (new_status, row["post_id"]))
                conn.commit(); conn.close()
                st.rerun()

    st.download_button("⬇️ Ekspor semua data ke CSV", df.to_csv(index=False).encode("utf-8-sig"), "trendwatch_x_data.csv", "text/csv")

with st.expander("Cara kerja dan batasan"):
    st.markdown("""
- Versi ini tidak terhubung ke X API, tidak meminta Bearer Token, dan tidak melakukan scraping.
- Kamu memasukkan sendiri teks postingan publik yang ingin dianalisis, atau mengimpor CSV.
- Analisis mencocokkan nama produk, kata kunci minat, dan hashtag berdasarkan daftar di sidebar.
- Label peluang adalah petunjuk untuk ditinjau, bukan bukti pasti seseorang akan membeli.
- Pastikan penggunaan data menghormati aturan platform dan privasi. Jangan masukkan informasi pribadi atau postingan privat.
- Penyimpanan menggunakan SQLite pada lingkungan hosting. Pada layanan hosting gratis, data lokal dapat memiliki batas persistensi; unduh CSV secara berkala sebagai cadangan.
""")
