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
    st.error("Błąd konfiguracji Secrets. Sprawdź SUPABASE_URL i SUPABASE_KEY.")
    st.stop()

st.set_page_config(page_title="ProStock ERP v4.0", layout="wide", initial_sidebar_state="expanded")

# --- 2. ZAAWANSOWANY DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Tło i ogólny styl */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    /* Karty metryk */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    /* Stylizacja tabeli */
    .stDataFrame {
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 10px;
    }
    /* Nagłówki */
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
        letter-spacing: -1px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA DANYCH ---

def safe_float(value):
    try: return float(value) if value is not None else 0.0
    except: return 0.0

def fetch_all_data():
    # Pobieramy produkty i kategorie w jednym zapytaniu
    prods = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria_id, kategorie(nazwa)").execute()
    cats = supabase.table("kategorie").select("id, nazwa").execute()
    return prods.data, cats.data

# Pobieranie danych
products_raw, categories_raw = fetch_all_data()

# Przetwarzanie do DataFrame
if products_raw:
    processed = []
    for p in products_raw:
        kat_obj = p.get('kategorie')
        nazwa_kat = kat_obj.get('nazwa', 'Brak') if isinstance(kat_obj, dict) else (kat_obj[0].get('nazwa') if kat_obj else "Brak")
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
    df = pd.DataFrame(columns=["ID", "Produkt", "Ilość", "Cena", "Kategoria", "Wartość"])

# --- 4. INTERFEJS UŻYTKOWNIKA ---

# Sidebar - Panel Sterowania
with st.sidebar:
    st.title("🛡️ Admin Panel")
    st.write("Zarządzaj bazą danych w czasie rzeczywistym.")
    
    with st.expander("🆕 Dodaj Nowy Produkt", expanded=True):
        if categories_raw:
            cat_map = {c['nazwa']: c['id'] for c in categories_raw}
            with st.form("add_product_form", clear_on_submit=True):
                n_name = st.text_input("Nazwa")
                n_qty = st.number_input("Ilość", min_value=0.0)
                n_price = st.number_input("Cena (PLN)", min_value=0.0)
                n_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
                
                if st.form_submit_button("🔥 Zatwierdź i Dodaj"):
                    if n_name:
                        supabase.table("produkty").insert({
                            "nazwa": n_name, "liczba": n_qty, 
                            "cena": n_price, "kategoria_id": cat_map[n_cat]
                        }).execute()
                        st.success("Dodano produkt!")
                        st.rerun()
                    else:
                        st.error("Wpisz nazwę!")
    
    st.divider()
    if st.button("🗑️ Usuń Wybrany ID"):
        id_to_del = st.number_input("Wpisz ID produktu", step=1, min_value=1)
        if st.button("Potwierdź usunięcie"):
            supabase.table("produkty").delete().eq("id", id_to_del).execute()
            st.rerun()

# Główny Ekran
st.title("📊 ProStock ERP Dashboard")

# Metryki
if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Produkty", len(df), "Szt.")
    m2.metric("💰 Kapitał", f"{df['Wartość'].sum():,.2f}", "PLN")
    m3.metric("📉 Braki", len(df[df['Ilość'] < 10]), "Alert", delta_color="inverse")
    m4.metric("🏷️ Kategorie", len(df['Kategoria'].unique()))

    st.divider()

    # Wykresy
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🗺️ Struktura Zasobów (Mapa Drzewa)")
        fig_tree = px.treemap(df, path=['Kategoria', 'Produkt'], values='Wartość',
                              color='Ilość', color_continuous_scale='Blues',
                              template="plotly_dark")
        st.plotly_chart(fig_tree, use_container_width=True)

    with c2:
        st.subheader("🍩 Wartość wg Kategorii")
        fig_donut = px.pie(df, names="Kategoria", values="Wartość", hole=0.6,
                           template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig_donut, use_container_width=True)

    # Tabela z Progress Barami
    st.subheader("🔍 Szczegółowy Rejestr Magazynowy")
    
    # Dodajemy wyszukiwarkę
    search = st.text_input("Filtruj tabelę...", placeholder="Wpisz nazwę produktu...")
    dff = df[df['Produkt'].str.contains(search, case=False)] if search else df

    st.dataframe(
        dff,
        column_config={
            "Ilość": st.column_config.ProgressColumn("Dostępność", min_value=0, max_value=max(df['Ilość'])*1.2, format="%d"),
            "Cena": st.column_config.NumberColumn("Cena jedn.", format="%.2f zł"),
            "Wartość": st.column_config.NumberColumn("Suma", format="%.2f zł"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Eksport
    st.download_button("💾 Pobierz Raport CSV", df.to_csv(index=False), "raport.csv", "text/csv")

else:
    st.warning("Twoja baza danych jest pusta. Dodaj produkty w panelu bocznym po lewej stronie!")
