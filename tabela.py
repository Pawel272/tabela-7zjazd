import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- 1. KONFIGURACJA POŁĄCZENIA ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji Secrets. Sprawdź ustawienia w Streamlit Cloud.")
    st.stop()

st.set_page_config(page_title="Magazyn & Analityka", layout="wide")

# --- 2. FUNKCJE POMOCNICZE ---

def safe_float(value):
    """Bezpieczna konwersja na liczbę zmiennoprzecinkową."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

def fetch_categories():
    """Pobiera kategorie do formularza."""
    res = supabase.table("kategorie").select("id, nazwa").execute()
    return res.data

def fetch_products():
    """Pobiera produkty wraz z relacją do tabeli kategorie."""
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    return res.data

# --- 3. LOGIKA I INTERFEJS ---

st.title("📦 System Zarządzania i Analityki")

# Boczne menu: Dodawanie produktów
with st.sidebar:
    st.header("➕ Dodaj produkt")
    categories = fetch_categories()
    cat_options = {c['nazwa']: c['id'] for c in categories}
    
    with st.form("add_form", clear_on_submit=True):
        new_nazwa = st.text_input("Nazwa produktu")
        new_liczba = st.number_input("Ilość", min_value=0.0, step=1.0)
        new_cena = st.number_input("Cena (zł)", min_value=0.0, format="%.2f")
        new_kat = st.selectbox("Kategoria", options=list(cat_options.keys()))
        
        if st.form_submit_button("Zapisz w bazie"):
            if new_nazwa:
                payload = {
                    "nazwa": new_nazwa,
                    "liczba": new_liczba,
                    "cena": new_cena,
                    "kategoria_id": cat_options[new_kat]
                }
                supabase.table("produkty").insert(payload).execute()
                st.success(f"Dodano: {new_nazwa}")
                st.rerun()
            else:
                st.warning("Podaj nazwę produktu!")

# Pobranie danych do głównego widoku
products = fetch_products()

# --- 4. SEKCJA WYKRESÓW (ANALITYKA) ---
if products:
    st.header("📊 Analiza Kategorii i Stanów")
    
    # Przetworzenie danych do DataFrame (dla wykresów)
    processed_data = []
    for p in products:
        # Obsługa relacji kategorii (bezpieczne wyciąganie nazwy)
        kat_raw = p.get('kategorie')
        if isinstance(kat_raw, dict):
            nazwa_kat = kat_raw.get('nazwa', 'Brak')
        elif isinstance(kat_raw, list) and len(kat_raw) > 0:
            nazwa_kat = kat_raw[0].get('nazwa', 'Brak')
        else:
            nazwa_kat = 'Nieprzypisane'

        processed_data.append({
            "ID": p['id'],
            "Produkt": p['nazwa'],
            "Ilość": safe_float(p.get('liczba')),
            "Cena": safe_float(p.get('cena')),
            "Kategoria": nazwa_kat,
            "Wartość Sumaryczna": safe_float(p.get('cena')) * safe_float(p.get('liczba'))
        })
    
    df = pd.DataFrame(processed_data)

    # Układ wykresów
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # Wykres 1: Suma ilości sztuk w danej kategorii
        fig_bars = px.bar(df.groupby("Kategoria")["Ilość"].sum().reset_index(), 
                         x="Kategoria", y="Ilość", 
                         title="Łączna ilość sztuk wg kategorii",
                         color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_bars, use_container_width=True)

    with col_chart2:
        # Wykres 2: Liczba unikalnych produktów w kategorii
        fig_pie = px.pie(df, names="Kategoria", 
                        title="Udział rodzajów produktów w kategoriach",
                        hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # --- 5. TABELA PRODUKTÓW I USUWANIE ---
    st.header("📋 Lista i edycja produktów")
    
    # Nagłówki
    h_id, h_naz, h_il, h_cen, h_kat, h_akc = st.columns([1, 3, 2, 2, 3, 1])
    h_id.write("**ID**")
    h_naz.write("**Nazwa**")
    h_il.write("**Ilość**")
    h_cen.write("**Cena**")
    h_kat.write("**Kategoria**")
    h_akc.write("**Akcja**")
    st.write("---")

    # Wiersze danych
    for _, row in df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 2, 2, 3, 1])
        c1.write(f"{int(row['ID'])}")
        c2.write(f"**{row['Produkt']}**")
        c3.write(f"{row['Ilość']}")
        c4.write(f"{row['Cena']:.2f} zł")
        c5.write(f"📁 {row['Kategoria']}")
        
        if c6.button("🗑️", key=f"del_{row['ID']}"):
            supabase.table("produkty").delete().eq("id", row['ID']).execute()
            st.toast(f"Usunięto: {row['Produkt']}")
            st.rerun()

else:
    st.info("Brak danych do wyświetlenia. Dodaj pierwszy produkt w panelu bocznym!")
