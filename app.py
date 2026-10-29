import os
import re
import sqlite3
from datetime import datetime, timezone
from collections import Counter

import pandas as pd
import requests
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

def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT PRIMARY KEY,
        created_at TEXT,
        username TEXT,
        text TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        reposts INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0,
        lang TEXT,
        matched_product TEXT,
        matched_terms TEXT,
        status TEXT DEFAULT 'Baru',
        source TEXT DEFAULT 'X API',
        imported_at TEXT
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

def get_token():
    try:
        token = st.secrets.get("X_BEARER_TOKEN", "")
    except Exception:
        token = ""
    return token or os.getenv("X_BEARER_TOKEN", "")

def fetch_x(query, limit):
    token = get_token()
    if not token:
        raise RuntimeError("Bearer Token belum dipasang. Ikuti README untuk mengaturnya secara rahasia.")
    # Official X API v2 recent search. Availability and pricing depend on X account tier.
    url = "https://api.x.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": min(100, max(10, int(limit))),
        "tweet.fields": "created_at,public_metrics,entities,lang,author_id",
        "expansions": "author_id",
        "user.fields": "username,name"
    }
    response = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if response.status_code == 401:
        raise RuntimeError("X API menolak token (401). Periksa token.")
    if response.status_code == 403:
        raise RuntimeError("Akses ditolak (403). Endpoint atau paket akunmu mungkin tidak mengizinkan pencarian ini.")
    if response.status_code == 429:
        raise RuntimeError("Kuota/batas permintaan tercapai (429). Tunggu sebelum mencoba lagi.")
    response.raise_for_status()
    payload = response.json()
    users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
    rows = []
    for post in payload.get("data", []):
        user = users.get(post.get("author_id"), {})
        metrics = post.get("public_metrics", {})
        rows.append({
            "post_id": post["id"],
            "created_at": post.get("created_at", ""),
            "username": "@" + user.get("username", "unknown"),
            "text": post.get("text", ""),
            "likes": metrics.get("like_count", 0),
            "reposts": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "lang": post.get("lang", ""),
            "source": "X API"
        })
    return rows

def save_posts(rows, products, keywords, hashtags):
    conn = connect_db()
    added = 0
    for row in rows:
        product, terms, is_opportunity = match_post(row.get("text", ""), products, keywords, hashtags)
        row["matched_product"] = product
        row["matched_terms"] = terms
        row["imported_at"] = datetime.now(timezone.utc).isoformat()
        row["status"] = "Baru" if is_opportunity else "Perlu ditinjau"
        before = conn.total_changes
        conn.execute("""INSERT OR IGNORE INTO posts
        (post_id,created_at,username,text,likes,reposts,replies,lang,matched_product,matched_terms,status,source,imported_at)
        VALUES (:post_id,:created_at,:username,:text,:likes,:reposts,:replies,:lang,:matched_product,:matched_terms,:status,:source,:imported_at)""", row)
        if conn.total_changes > before:
            added += 1
    conn.commit()
    conn.close()
    return added

def load_posts():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM posts ORDER BY created_at DESC", conn)
    conn.close()
    return df

st.title("🌷 TrendWatch X")
st.caption("Pemantau hashtag dan peluang produk · sumber live hanya jika X API berhasil diakses")

with st.sidebar:
    st.header("Pengaturan pantauan")
    products_raw = st.text_area("Produk (pisahkan dengan koma)", DEFAULT_PRODUCTS, height=90)
    keywords_raw = st.text_area("Kata kunci minat (pisahkan dengan koma)", DEFAULT_KEYWORDS, height=100)
    hashtags_raw = st.text_area("Hashtag tanpa # (pisahkan dengan koma)", DEFAULT_HASHTAGS, height=80)
    query = st.text_input("Query X API", '(("butuh" OR "cari" OR "WTB") (Netflix OR Canva OR Spotify)) lang:id -is:retweet')
    limit = st.select_slider("Maksimum hasil per pengambilan", options=[10,20,30,50,100], value=20)
    st.divider()
    st.markdown("**Sumber:** X API resmi saja. Tidak ada data demo yang otomatis dicampur dengan data live.")

products = comma_list(products_raw)
keywords = comma_list(keywords_raw)
hashtags = comma_list(hashtags_raw)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔎 Ambil postingan dari X", use_container_width=True, type="primary"):
        try:
            with st.spinner("Menghubungi X API..."):
                rows = fetch_x(query, limit)
                added = save_posts(rows, products, keywords, hashtags)
            st.success(f"Pengambilan selesai. Hasil dari API: {len(rows)}; postingan baru disimpan: {added}.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
with col2:
    if st.button("↻ Muat ulang dashboard", use_container_width=True):
        st.rerun()

df = load_posts()
if df.empty:
    st.info("Belum ada postingan live tersimpan. Atur token X API dan tekan 'Ambil postingan dari X'. Dashboard tidak akan menampilkan data contoh sebagai data asli.")
else:
    total = len(df)
    new_count = int((df["status"] == "Baru").sum())
    tracked_products = int(df["matched_product"].fillna("").ne("").sum())
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Postingan tersimpan", total)
    c2.metric("Peluang baru", new_count)
    c3.metric("Cocok produk", tracked_products)
    c4.metric("Total likes", int(pd.to_numeric(df["likes"], errors="coerce").fillna(0).sum()))

    st.subheader("Filter postingan")
    f1,f2,f3 = st.columns([2,1,1])
    with f1:
        search = st.text_input("Cari teks, akun, atau produk", "")
    with f2:
        status_filter = st.selectbox("Status", ["Semua","Baru","Ditindaklanjuti","Selesai","Perlu ditinjau"])
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
            current_status = row["status"] if row["status"] in ["Baru","Ditindaklanjuti","Selesai","Perlu ditinjau"] else "Perlu ditinjau"
            new_status = st.selectbox("Status", ["Baru","Ditindaklanjuti","Selesai","Perlu ditinjau"], index=["Baru","Ditindaklanjuti","Selesai","Perlu ditinjau"].index(current_status), key=f"status_{row['post_id']}")
            if new_status != current_status and st.button("Simpan status", key=f"save_{row['post_id']}"):
                conn = connect_db()
                conn.execute("UPDATE posts SET status=? WHERE post_id=?", (new_status, row["post_id"]))
                conn.commit(); conn.close()
                st.rerun()

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Ekspor semua data ke CSV", csv_bytes, "trendwatch_x_posts.csv", "text/csv")
    counts = Counter()
    for text_value in df["text"].fillna(""):
        counts.update("#" + tag for tag in re.findall(r"(?<!\\w)#([\\w]+)", text_value))
    if counts:
        st.subheader("Hashtag yang ditemukan")
        st.bar_chart(pd.DataFrame(counts.most_common(12), columns=["Hashtag","Jumlah"]).set_index("Hashtag"))

with st.expander("Cara kerja dan batasan"):
    st.markdown("""
- Data hanya disimpan setelah berhasil diambil dari X API resmi; dashboard tidak membuat data live palsu.
- Penyimpanan SQLite memakai `post_id` sebagai kunci unik sehingga hasil yang sama tidak disimpan dua kali.
- Penyaringan peluang memakai pencocokan kata sederhana. Hasil perlu ditinjau manusia; ini bukan bukti pasti seseorang berniat membeli.
- Tombol pengambilan melakukan satu kali permintaan. Untuk otomatis berkala 24/7, aplikasi perlu dijalankan di hosting dengan scheduler/worker; refresh halaman saja tidak menjamin pengambilan data baru.
- Endpoint recent search, kuota, harga, dan periode data bergantung pada akses X API akunmu. HTTP 403 dapat berarti paket tidak memiliki akses.
- Hormati aturan platform dan privasi. Jangan memakai cara yang melewati login atau pembatasan akses.
""")
