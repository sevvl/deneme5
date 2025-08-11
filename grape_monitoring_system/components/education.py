import os
import sys
from pathlib import Path
import streamlit as st

# --- sadece debug için ---
print("\n".join(sys.path))

# --- secrets / env ---
def get_secret(name, default=None):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")

# --- education_content yolu ---
BASE_DIR = Path(__file__).resolve().parent
CANDIDATES = [
    BASE_DIR / "education_content",
    BASE_DIR.parent / "education_content",
    Path.cwd() / "education_content",
]
EDU_CONTENT_DIR = next((p for p in CANDIDATES if p.exists()), BASE_DIR / "education_content")

def list_education_files():
    if EDU_CONTENT_DIR.exists():
        return sorted([f for f in os.listdir(EDU_CONTENT_DIR) if f.endswith(".md")])
    return []

def read_education_file(filename):
    path = EDU_CONTENT_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

# --- cache (fonksiyon-bazlı temizleme) ---
@st.cache_data(ttl=3600)
def _fetch_fungicide_data_cached(_api_key: str):
    from scrape_data import get_grape_data_smart
    df = get_grape_data_smart(api_key=_api_key)
    if df is not None and not df.empty:
        df = df.dropna(how="all").reset_index(drop=True)
    return df

def load_fungicide_data(force_refresh: bool = False):
    try:
        if force_refresh:
            _fetch_fungicide_data_cached.clear()
        with st.spinner("📊 Fungisit verileri yükleniyor..."):
            return _fetch_fungicide_data_cached(GEMINI_API_KEY or "")
    except Exception as e:
        st.error(f"❌ Veri yükleme hatası: {e}")
        return None

# --- ana bileşen ---
def education_component(perform_search_func):
    st.header("📚 Bilgi Bankası / Eğitim Modülü")
    st.write("Bağcılık, hastalıklar ve ilaçlar hakkında eğitim içerikleri.")

    tab1, tab2, tab3 = st.tabs(["Yerel İçerikler", "Web Araması", "🧪 Fungisit Veritabanı"])

    # 📁 Yerel içerikler
    with tab1:
        files = list_education_files()
        if not files:
            st.info("Henüz yerel eğitim içeriği eklenmemiş.")
        else:
            selected = st.selectbox("Bir konu seçin:", files)
            if selected:
                content = read_education_file(selected)
                st.markdown(f'### {selected.replace(".md","").replace("_"," ")}', unsafe_allow_html=True)
                st.markdown(content, unsafe_allow_html=True)

    # 🌍 Web Araması
    with tab2:
        st.subheader("Online Makale Araması")
        search_query = st.text_input(
            "Aramak istediğiniz konuyu girin (örn: üzüm mildiyö tedavisi)",
            key="web_search_input",
        )

        if st.button("Web'de Ara", key="web_search_button"):
            if search_query:
                try:
                    with st.spinner(f"'{search_query}' için web araması yapılıyor..."):
                        # gerekirse perform_search_func'e api_key geçebilirsin
                        # results = perform_search_func(search_query, api_key=GEMINI_API_KEY)
                        results = perform_search_func(search_query)

                    st.write("🔍 Arama Sonuçları Ham Veri:", results)

                    if results:
                        st.subheader("Arama Sonuçları:")
                        for result in results:
                            title = result.get("title", "Başlık Yok")
                            link = result.get("link") or result.get("url") or "#"
                            snippet = result.get("snippet", "")
                            st.markdown(f"- **[{title}]({link})**")
                            st.write(snippet)
                            st.markdown("--- ")
                    else:
                        st.info(f"'{search_query}' için sonuç bulunamadı.")
                except Exception as e:
                    st.error(f"Web araması hata verdi: {e}")
            else:
                st.warning("Lütfen bir arama terimi girin.")



    # 🧪 Fungisit verileri
    with tab3:
        st.subheader("UMass kaynaklı fungisit etkinlik verileri")
        # import hatasını erken yakala
        try:
            import scrape_data  # noqa: F401
        except Exception as e:
            st.error(f"`scrape_data` import hatası: {e}")

        df = load_fungicide_data()
        if df is not None and not df.empty:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_term = st.text_input("🔍 Hastalık veya fungisit ara:", key="search_fungicide")
            with col2:
                st.metric("📊 Toplam Kayıt", len(df))
            with col3:
                if st.button("🔄 Veriyi Yenile", key="refresh_data"):
                    _fetch_fungicide_data_cached.clear()
                    df_fresh = load_fungicide_data(force_refresh=True)
                    if df_fresh is not None:
                        st.success("✅ Veriler güncellendi!")
                        st.rerun()

            filtered_df = df
            if search_term:
                mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
                filtered_df = df[mask]
                if len(filtered_df) > 0:
                    st.info(f"🎯 '{search_term}' için {len(filtered_df)} sonuç bulundu")
                else:
                    st.warning(f"❌ '{search_term}' için sonuç bulunamadı")

            st.dataframe(filtered_df, use_container_width=True, height=400, hide_index=True)
        else:
            st.info("Veri henüz yüklenemedi.")
