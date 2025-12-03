import streamlit as st
import json
import os
from datetime import datetime
from github import Github, GithubException
import google.generativeai as genai

# --- KONFIGURACE A PŘIPOJENÍ ---

# Nastavení stránky
st.set_page_config(
    page_title="Promptoviště 2.0",
    page_icon="✨",
    layout="wide"
)

# Načtení klíčů ze Secrets
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("Chybí soubor secrets.toml nebo nastavení na cloudu! Zkontroluj návod.")
    st.stop()
except KeyError as e:
    st.error(f"V secrets chybí klíč: {e}")
    st.stop()

# Konfigurace Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# Cesta k souboru v repozitáři
DATA_FILE = "prompty.json"

# --- FUNKCE PRO PRÁCI S GITHUBEM ---

def get_github_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

def load_data_from_github():
    """Načte JSON přímo z GitHubu."""
    try:
        repo = get_github_repo()
        contents = repo.get_contents(DATA_FILE)
        json_data = contents.decoded_content.decode("utf-8")
        return json.loads(json_data)
    except Exception as e:
        st.error(f"🚨 CHYBA NAČÍTÁNÍ Z GITHUBU: {e}")
        return []

def save_data_to_github(data, commit_message="Aktualizace promptů z aplikace"):
    """Uloží JSON přímo do GitHubu (commit)."""
    repo = get_github_repo()
    try:
        # Zkusíme soubor najít, abychom získali jeho SHA (nutné pro update)
        contents = repo.get_contents(DATA_FILE)
        repo.update_file(
            path=contents.path,
            message=commit_message,
            content=json.dumps(data, ensure_ascii=False, indent=2),
            sha=contents.sha
        )
        return True
    except GithubException as e:
        # Pokud soubor neexistuje, vytvoříme ho
        if e.status == 404:
            repo.create_file(
                path=DATA_FILE,
                message="První uložení promptů",
                content=json.dumps(data, ensure_ascii=False, indent=2)
            )
            return True
        else:
            st.error(f"Chyba při ukládání do GitHubu: {e}")
            return False

# --- FUNKCE PRO GEMINI AI ---

def analyze_prompt_with_ai(prompt_text):
    """Pošle text promptu do Gemini a získá strukturovaná data."""
    # Používáme model, který jsi nastavila a funguje ti
    model = genai.GenerativeModel('gemini-2.0-flash') 
    
    # VYLEPŠENÉ ZADÁNÍ PRO AI (aby lépe čistila text)
    prompt = f"""
    Jsi expertní editor a analytik AI promptů. Dostaneš surový text zkopírovaný z webové stránky nebo mailu.
    
    SUROVÝ TEXT:
    {prompt_text}
    
    TVŮJ ÚKOL (Vrať JSON):
    1. "nazev": Najdi hlavní název. DŮLEŽITÉ: Ponech ho v ORIGINÁLE (Anglicky), pokud to zní jako název metody (např. 'Pattern Pivot Protocol', 'Life OS Architect'). Nepřekládej do češtiny, pokud by to znělo krkolomně. Pokud název chybí, vymysli krátký český.
    2. "kategorie": Vyber jednu: Vzdělávání, Marketing, Business, Osobní rozvoj, Kreativita, Kariéra, Technologie, Zdraví a wellness, Jiné.
    3. "popis": Napiš stručné české shrnutí (1-2 věty), co ten prompt dělá.
    4. "tagy": Navrhni 3-5 českých tagů (pole řetězců).
    5. "text": TOTO JE NEJDŮLEŽITĚJŠÍ. Extrahuj POUZE samotný systémový prompt.
       - Ignoruj úvodní texty, autory, odkazy, ukázky použití ("Example user prompts").
       - Hledej bloky začínající tagy jako <role>, <context>, <instructions> nebo fráze "You are a...".
       - Vrať čistý text, který se má vložit do AI, bez okolního balastu.
    
    Vrať POUZE čistý JSON bez formátování markdownem.
    """
    
    try:
        response = model.generate_content(prompt)
        # Očištění odpovědi od případných ```json značek
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"Chyba AI analýzy: {e}")
        return None

# --- HLAVNÍ APLIKACE ---

# Inicializace session state
if 'prompts' not in st.session_state:
    st.session_state.prompts = load_data_from_github()

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# Refresh data tlačítko (pro jistotu)
if st.sidebar.button("🔄 Načíst čerstvá data z GitHubu"):
    st.session_state.prompts = load_data_from_github()
    st.rerun()

prompts = st.session_state.prompts

# Hlavička
st.title("✨ Promptoviště 2.0")
st.markdown("*Chytrá databáze promptů, která se ukládá přímo do cloudu.*")

# Admin login v postranním panelu
with st.sidebar:
    st.header("🔐 Admin zóna")
    if not st.session_state.admin_logged_in:
        admin_password = st.text_input("Heslo", type="password", key="admin_pass")
        if st.button("Přihlásit"):
            if admin_password == "promptmaster": # Změň si heslo dle potřeby
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Nesprávné heslo")
    else:
        st.success("✅ Přihlášen jako admin")
        if st.button("Odhlásit"):
            st.session_state.admin_logged_in = False
            st.rerun()

st.divider()

# --- LOGIKA ZÁLOŽEK ---

if st.session_state.admin_logged_in:
    # Admin má 3 záložky
    tab1, tab2, tab3 = st.tabs(["📚 Procházet prompty", "➕ Přidat prompt (AI Powered)", "📊 Statistiky"])
    tab_stats = tab3
else:
    # Návštěvník má 2 záložky
    tab1, tab2 = st.tabs(["📚 Procházet prompty", "📊 Statistiky"])
    tab_stats = tab2

# --- ZÁLOŽKA 1: PROCHÁZENÍ ---
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Hledat...", placeholder="Klíčové slovo...")
    with col2:
        if prompts:
            all_categories = sorted(list(set([p.get('kategorie', 'Jiné') for p in prompts])))
        else:
            all_categories = []
        cat_filter = st.selectbox("Filtr kategorie", ["Všechny"] + all_categories)

    filtered = [
        p for p in prompts 
        if (search.lower() in str(p).lower()) and 
           (cat_filter == "Všechny" or p.get('kategorie') == cat_filter)
    ]
    
    st.info(f"Zobrazeno {len(filtered)} z {len(prompts)} promptů")
    
    for p in filtered:
        with st.expander(f"**{p['nazev']}** ({p.get('kategorie', 'Nezadáno')})"):
            st.caption(p.get('popis', ''))
            st.code(p['text'])
            
            # Moderní zobrazení tagů
            if 'tagy' in p and p['tagy']:
                try:
                    st.pills("Tagy", p['tagy'], selection_mode="multi", key=f"pills_{p['nazev']}")
                except AttributeError:
                    st.write("🏷️ " + ", ".join(p['tagy']))

# --- ZÁLOŽKA 2: PŘIDÁNÍ PROMPTU (POUZE ADMIN) ---
if st.session_state.admin_logged_in:
    with tab2:
        st.header("✨ Přidat nový prompt s AI")
        
        # Tlačítko pro ruční vyčištění
        if st.button("🗑️ Vyčistit formulář"):
            st.session_state.new_prompt_data = {"nazev": "", "kategorie": "", "popis": "", "tagy": "", "text": ""}
            # BEZPEČNÉ MAZÁNÍ - Místo přepisování klíč úplně odstraníme
            if "input_text_area" in st.session_state:
                del st.session_state["input_text_area"]
            st.rerun()

        if 'new_prompt_data' not in st.session_state:
            st.session_state.new_prompt_data = {"nazev": "", "kategorie": "", "popis": "", "tagy": "", "text": ""}

        # 1. Vstup pro text
        input_text = st.text_area("Vlož sem text promptu (klidně i s balastem okolo):", value=st.session_state.new_prompt_data["text"], height=200, key="input_text_area")
        
        # 2. AI Tlačítko
        if st.button("✨ Analyzovat a vyplnit pomocí AI"):
            if input_text:
                with st.spinner("AI čistí a analyzuje prompt..."):
                    ai_result = analyze_prompt_with_ai(input_text)
                    if ai_result:
                        st.session_state.new_prompt_data["text"] = ai_result.get("text", input_text)
                        st.session_state.new_prompt_data["nazev"] = ai_result.get("nazev", "")
                        st.session_state.new_prompt_data["kategorie"] = ai_result.get("kategorie", "")
                        st.session_state.new_prompt_data["popis"] = ai_result.get("popis", "")
                        st.session_state.new_prompt_data["tagy"] = ", ".join(ai_result.get("tagy", []))
                        st.success("Údaje vyplněny a text vyčištěn!")
                        st.rerun()
            else:
                st.warning("Nejdřív vlož text promptu!")

        st.markdown("---")
        
        # 3. Formulář
        with st.form("add_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_nazev = st.text_input("Název", value=st.session_state.new_prompt_data["nazev"])
                
                cats_list = ["Vzdělávání", "Marketing", "Business", "Osobní rozvoj", "Kreativita", "Kariéra", "Technologie", "Zdraví a wellness", "Jiné"]
                curr_cat = st.session_state.new_prompt_data["kategorie"]
                cat_index = cats_list.index(curr_cat) if curr_cat in cats_list else 8
                
                f_kategorie = st.selectbox("Kategorie", cats_list, index=cat_index)
                
            with col_f2:
                f_tagy = st.text_input("Tagy (oddělené čárkou)", value=st.session_state.new_prompt_data["tagy"])
            
            f_popis = st.text_area("Popis", value=st.session_state.new_prompt_data["popis"])
            f_text = st.text_area("Finální text promptu (k uložení)", value=st.session_state.new_prompt_data.get("text", ""), height=300)
            
            submit = st.form_submit_button("💾 Uložit do GitHubu")
            
            if submit:
                # Kontrola duplicit
                is_duplicate = any(p['nazev'].lower() == f_nazev.lower() for p in st.session_state.prompts)
                if is_duplicate:
                    st.error(f"⚠️ Prompt s názvem '{f_nazev}' už existuje! Zvol jiný název.")
                elif not f_nazev or not f_text:
                    st.error("Vyplň alespoň název a text.")
                else:
                    new_item = {
                        "nazev": f_nazev,
                        "kategorie": f_kategorie,
                        "popis": f_popis,
                        "tagy": [t.strip() for t in f_tagy.split(",") if t.strip()],
                        "text": f_text,
                        "datum": datetime.now().strftime("%d.%m.%Y")
                    }
                    
                    st.session_state.prompts.append(new_item)
                    
                    with st.spinner("Odesílám data do GitHubu..."):
                        if save_data_to_github(st.session_state.prompts):
                            st.success("✅ Uloženo! Data jsou bezpečně v cloudu.")
                            # RESET DAT
                            st.session_state.new_prompt_data = {"nazev": "", "kategorie": "", "popis": "", "tagy": "", "text": ""}
                            # BEZPEČNÉ MAZÁNÍ - Odstranění klíče z session state
                            if "input_text_area" in st.session_state:
                                del st.session_state["input_text_area"]
                            st.rerun()

# --- ZÁLOŽKA: STATISTIKY (Univerzální pro všechny) ---
with tab_stats:
    st.metric("Celkem promptů", len(prompts))
    if prompts:
        cats = [p.get('kategorie', 'Nezadáno') for p in prompts]
        st.bar_chart({x: cats.count(x) for x in set(cats)})
