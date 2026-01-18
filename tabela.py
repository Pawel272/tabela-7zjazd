import streamlit as st
from supabase import create_client, Client

# Konfiguracja połączenia z Supabase
# Dane te znajdziesz w Project Settings -> API w panelu Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Zarządzanie Produktami", layout="centered")

st.title("📦 System Zarządzania Produktami")

# --- FUNKCJE POMOCNICZE ---

def fetch_categories():
    response = supabase.table("kategorie").select("id, nazwa").execute()
    return response.data

def fetch_products():
    # Pobieramy produkty wraz z nazwą kategorii (join)
    response = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    return response.data

# --- SEKCHJA 1: DODAWANIE PRODUKTU ---

st.header("➕ Dodaj nowy produkt")

categories = fetch_categories()
category_options = {c['nazwa']: c['id'] for c in categories}

with st.form("add_product_form", clear_on_submit=True):
    nazwa = st.text_input("Nazwa produktu")
    liczba = st.number_input("Ilość (liczba)", min_value=0.0, step=1.0)
    cena = st.number_input("Cena", min_value=0.0, format="%.2f")
    kat_nazwa = st.selectbox("Kategoria", options=list(category_options.keys()))
    
    submit_button = st.form_submit_button("Dodaj produkt")

    if submit_button:
        if nazwa:
            new_product = {
                "nazwa": nazwa,
                "liczba": liczba,
                "cena": cena,
                "kategoria_id": category_options[kat_nazwa]
            }
            try:
                supabase.table("produkty").insert(new_product).execute()
                st.success(f"Produkt '{nazwa}' został dodany!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas dodawania: {e}")
        else:
            st.warning("Proszę podać nazwę produktu.")

# --- SEKCJA 2: LISTA I USUWANIE ---

st.header("📋 Aktualna lista produktów")

products = fetch_products()

if products:
    for p in products:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 3, 1])
        
        col1.write(f"**{p['nazwa']}**")
        col2.write(f"Szt: {p['liczba']}")
        col3.write(f"{p['cena']} zł")
        # Wyświetlanie nazwy kategorii z relacji
        kat = p.get('kategorie', {}).get('nazwa', 'Brak')
        col4.write(f"📁 {kat}")
        
        # Przycisk usuwania
        if col5.button("🗑️", key=f"del_{p['id']}"):
            supabase.table("produkty").delete().eq("id", p['id']).execute()
            st.toast(f"Usunięto produkt: {p['nazwa']}")
            st.rerun()
else:
    st.info("Brak produktów w bazie danych.")
