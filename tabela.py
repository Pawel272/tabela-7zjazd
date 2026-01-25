import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- 1. KONFIGURACJA POŁĄCZENIA ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Błąd konfiguracji Secrets.")
    st.stop()

st.set_page_config(page_title="ERP Dashboard Pro", layout="wide")

# --- 2. CUSTOM CSS (GRAFIKA W TLE I STYLIZACJA) ---
# Podmień link w 'url()' na własną grafikę jeśli chcesz
st.markdown("""
    <style>
    .main {
        background-image: url("https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp {
        background: rgba(255, 255, 255, 0.05);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #00d4ff;
    }
    .stDataFrame {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: white !important;
        text-shadow: 2px 2px 4px #000000;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNKCJE DANYCH ---

def safe_float(value):
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0

@st.cache_data(ttl=30)
def fetch_data():
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    return res.data

# --- 4. LOGIKA APLIKACJI ---

data_raw = fetch_data()
if data_raw:
    processed = []
    for p in data_raw:
        kat_raw = p.get('kategorie')
        nazwa_kat = kat_raw.get('nazwa', 'Brak') if isinstance(kat_raw, dict) else (kat_raw[0].get('nazwa') if kat_raw else "Brak")
        processed.append({
            "ID": p['id'],
            "Produkt": p['nazwa'],
            "Ilość": safe_float(p.get('liczba')),
            "Cena": safe_float(p.get('cena')),
            "Kategoria": nazwa_kat,
            "Wartość": safe_float(p.get('cena')) * safe_float(p.get('liczba'))
        })
    df = pd.DataFrame(processed)
else:
    df = pd.DataFrame()

# --- 5. INTERFEJS ---

st.title("🚀 Zaawansowany System ERP v3.0")

if not df.empty:
    # Metryki w górnym rzędzie
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("📦 Pozycje", len(df))
    with m2: st.metric("💰 Wartość netto", f"{df['Wartość'].sum():,.2f} zł")
    with m3: st.metric("📉 Deficyt", len(df[df['Ilość'] < 5]))
    with m4: st.metric("🏢 Kategorie", len(df['Kategoria'].unique()))

    st.divider()

    # WYKRESY 2.0
    c1, c2 = st.columns([3, 2])
    
    with c1:
        # Wykres Treemap - bardzo "pro" wygląd
        st.subheader("📊 Mapa Hierarchiczna Magazynu")
        fig_tree = px.treemap(df, path=['Kategoria', 'Produkt'], values='Wartość',
                              color='Ilość', color_continuous_scale='RdYlGn',
                              title="Wielkość prostokąta = Wartość finansowa")
        fig_tree.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_tree, use_container_width=True)

    with c2:
        st.subheader("📈 Udział w Kapitale")
        fig_sun = px.sunburst(df, path=['Kategoria', 'Produkt'], values='Wartość',
                              color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_sun, use_container_width=True)

    # TABELA I FILTRY
    st.subheader("📂 Baza Operacyjna")
    
    col_search, col_export = st.columns([4, 1])
    search = col_search.text_input("Szybkie filtrowanie tabeli...", placeholder="Wpisz nazwę produktu...")
    
    dff = df[df['Produkt'].str.contains(search, case=False)] if search else df
    
    # Interaktywna tabela Streamlit
    st.dataframe(
        dff,
        column_config={
            "Ilość": st.column_config.ProgressColumn("Stan magazynowy", min_value=0, max_value=max(df['Ilość'])*1.2, format="%d"),
            "Cena": st.column_config.NumberColumn("Cena (PLN)", format="%.2f zł"),
            "Wartość": st.column_config.NumberColumn("Suma", format="%.2f zł"),
        },
        hide_index=True,
        use_container_width=True
    )

    csv = dff.to_csv(index=False).encode('utf-8')
    col_export.download_button("💾 Eksportuj CSV", csv, "magazyn.csv", "text/csv")

# Sidebar do akcji (Dodaj/Usuń)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2897/2897832.png", width=100)
    st.header("Panel Administracyjny")
    
    with st.expander("🆕 Dodaj Nowy Towar"):
        # Tutaj logika dodawania (jak w poprzednim kodzie)
        st.info("Logika dodawania produktów dostępna tutaj.")
    
    if st.button("🔄 Odśwież Dane"):
        st.cache_data.clear()
        st.rerun()
