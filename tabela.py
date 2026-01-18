import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
# Upewnij się, że w Streamlit Cloud Secrets masz SUPABASE_URL i SUPABASE_KEY
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji Secrets. Sprawdź, czy dodałeś SUPABASE_URL i SUPABASE_KEY.")
    st.stop()

st.set_page_config(page_title="Zarządzanie Magazynem", layout="wide")

# --- FUNKCJE LOGICZNE ---

def fetch_categories():
    """Pobiera listę kategorii do selectboxa."""
    res = supabase.table("kategorie").select("id, nazwa").execute()
    return res.data

def fetch_products():
    """Pobiera produkty wraz z danymi powiązanej kategorii."""
    # Używamy select z relacją do tabeli kategorie
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    return res.data

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Zarządzania Produktami")

# Boczne menu - Dodawanie produktów
with st.sidebar:
    st.header("➕ Dodaj nowy produkt")
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
                st.success("Dodano produkt!")
                st.rerun()
            else:
                st.warning("Nazwa jest wymagana.")

# Główny widok - Tabela produktów
st.header("📋 Lista produktów w bazie")
products = fetch_products()

if not products:
    st.info("Baza produktów jest obecnie pusta.")
else:
    # Nagłówki tabeli
    cols = st.columns([1, 3, 2, 2, 3, 1])
    cols[0].write("**ID**")
    cols[1].write("**Nazwa**")
    cols[2].write("**Ilość**")
    cols[3].write("**Cena**")
    cols[4].write("**Kategoria**")
    cols[5].write("**Akcja**")
    
    st.divider()

    for p in products:
        c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 2, 2, 3, 1])
        
        # Wyciąganie nazwy kategorii - ROZWIĄZANIE TWOJEGO BŁĘDU:
        kat_raw = p.get('kategorie')
        nazwa_kategorii = "Brak"
        
        if isinstance(kat_raw, dict):
            nazwa_kategorii = kat_raw.get('nazwa', 'Brak')
        elif isinstance(kat_raw, list) and len(kat_raw) > 0:
            nazwa_kategorii = kat_raw[0].get('nazwa', 'Brak')

        c1.write(p['id'])
        c2.write(f"**{p['nazwa']}**")
        c3.write(str(p['liczba']))
        c4.write(f"{p['cena']:.2f} zł")
        c5.write(f"📁 {nazwa_kategorii}")
        
        # Przycisk usuwania
        if c6.button("🗑️", key=f"del_{p['id']}"):
            supabase.table("produkty").delete().eq("id", p['id']).execute()
            st.toast(f"Usunięto: {p['nazwa']}")
            st.rerun()
