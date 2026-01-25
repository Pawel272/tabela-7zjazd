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

st.set_page_config(page_title="ProStock ERP v5.0", layout="wide")

# --- 2. NOWOCZESNY DESIGN CSS ---
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #00d4ff;
    }
    .product-card {
        background: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }
    h1, h2, h3 { color: #00d4ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA DANYCH ---

def safe_float(value):
    try: return float(value) if value is not None else 0.0
    except: return 0.0

def fetch_data():
    prods = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria_id, kategorie(nazwa)").execute()
    cats = supabase.table("kategorie").select("id, nazwa").execute()
    return prods.data, cats.data

products_raw, categories_raw = fetch_data()

# Przetwarzanie do DataFrame
if products_raw:
    processed = []
    for p in products_raw:
        kat_obj = p.get('kategorie')
        nazwa_kat = kat_obj.get('nazwa', 'Brak') if isinstance(kat_obj, dict) else (kat_obj[0].get('nazwa') if (isinstance(kat_obj, list) and len(kat_obj)>0) else "Brak")
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

# --- 4. PANEL BOCZNY (ZARZĄDZANIE) ---

with st.sidebar:
    st.title("🛡️ Panel Sterowania")
    
    # SEKCJA: DODAWANIE
    st.subheader("➕ Dodaj Produkt")
    if categories_raw:
        cat_map = {c['nazwa']: c['id'] for c in categories_raw}
        with st.form("add_form", clear_on_submit=True):
            n_name = st.text_input("Nazwa produktu")
            n_qty = st.number_input("Ilość", min_value=0.0)
            n_price = st.number_input("Cena (PLN)", min_value=0.0)
            n_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
            if st.form_submit_button("Zapisz w bazie"):
                if n_name:
                    supabase.table("produkty").insert({
                        "nazwa": n_name, "liczba": n_qty, "cena": n_price, "kategoria_id": cat_map[n_cat]
                    }).execute()
                    st.success("Produkt dodany!")
                    st.rerun()

    st.divider()

    # SEKCJA: USUWANIE (NAPRAWIONA)
    st.subheader("🗑️ Usuń Produkt")
    if not df.empty:
        # Tworzymy listę opcji "Nazwa (ID)" dla łatwiejszego wyboru
        delete_options = {f"{row['Produkt']} (ID: {row['ID']})": row['ID'] for _, row in df.iterrows()}
        selected_to_delete = st.selectbox("Wybierz produkt do usunięcia", options=list(delete_options.keys()))
        
        if st.button("❌ Potwierdź usunięcie", type="primary"):
            target_id = delete_options[selected_to_delete]
            try:
                supabase.table("produkty").delete().eq("id", target_id).execute()
                st.warning(f"Usunięto produkt o ID: {target_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas usuwania: {e}")

# --- 5. EKRAN GŁÓWNY (ANALITYKA) ---

st.title("📊 Monitor Magazynu Pro")

if not df.empty:
    # Metryki
    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Suma Produktów", f"{int(df['Ilość'].sum())} szt.")
    m2.metric("💰 Całkowita Wartość", f"{df['Wartość'].sum():,.2f} PLN")
    m3.metric("🏗️ Liczba Pozycji", len(df))

    st.divider()

    # Wykresy (Zamiast tabeli na środku)
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📈 Stan Magazynowy")
        fig_bar = px.bar(df, x="Produkt", y="Ilość", color="Kategoria", 
                         text_auto=True, template="plotly_dark",
                         color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("🍕 Podział Wartości")
        fig_pie = px.pie(df, names="Kategoria", values="Wartość", 
                         hole=0.5, template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    # Wizualne karty zamiast tabeli
    st.subheader("🔍 Przegląd asortymentu")
    
    # Wyszukiwarka
    search = st.text_input("Szukaj produktu...", "")
    
    filtered_df = df[df['Produkt'].str.contains(search, case=False)] if search else df
    
    # Wyświetlanie kart w kolumnach
    cols = st.columns(3)
    for idx, row in filtered_df.iterrows():
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="product-card">
                <h4>{row['Produkt']}</h4>
                <p>📦 Ilość: <b>{row['Ilość']}</b></p>
                <p>💰 Cena: <b>{row['Cena']:.2f} zł</b></p>
                <p>📁 Kategoria: {row['Kategoria']}</p>
                <small>ID Systemowe: {row['ID']}</small>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("Baza danych jest pusta. Skorzystaj z panelu po lewej, aby dodać dane.")
