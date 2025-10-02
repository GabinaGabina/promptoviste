import streamlit as st
import json
import os
from datetime import datetime
from collections import defaultdict

# Nastavení stránky
st.set_page_config(
    page_title="Promptoviště",
    page_icon="🤖",
    layout="wide"
)

# Soubor pro ukládání dat
DATA_FILE = "prompty.json"

# Funkce pro načtení dat
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Funkce pro uložení dat
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Funkce pro export dat
def export_to_json():
    data = load_data()
    return json.dumps(data, ensure_ascii=False, indent=2)

# Inicializace session state
if 'prompts' not in st.session_state:
    st.session_state.prompts = load_data()
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

prompts = st.session_state.prompts

# Hlavička
st.title("🤖 Promptoviště")
st.markdown("*Sdílená kolekce užitečných promptů pro vzdělávání, marketing a další oblasti*")

# Admin login v postranním panelu
with st.sidebar:
    st.header("Admin přístup")
    if not st.session_state.admin_logged_in:
        admin_password = st.text_input("Heslo", type="password", key="admin_pass")
        if st.button("Přihlásit"):
            if admin_password == "promptmaster":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Nesprávné heslo")
    else:
        st.success("Přihlášen jako admin")
        if st.button("Odhlásit"):
            st.session_state.admin_logged_in = False
            st.rerun()

st.markdown("---")

# Rozdělení na záložky
if st.session_state.admin_logged_in:
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Procházet prompty", "📂 Kategorie & Tagy", "➕ Přidat prompt", "ℹ️ O projektu"])
    tabs = [tab1, tab2, tab3, tab4]
else:
    tab1, tab2, tab3 = st.tabs(["📚 Procházet prompty", "📂 Kategorie & Tagy", "ℹ️ O projektu"])
    tabs = [tab1, tab2, tab3]

# Detekce změny záložky - resetuje expandery v kategorii
# Streamlit automaticky spustí celý skript znovu při změně záložky
# Takže expandery se automaticky zavřou, ale musíme jim nastavit expanded=False

# Záložka 1: Procházet prompty
with tab1:
    st.header("Databáze promptů")
    
    # Export tlačítko
    if prompts:
        col_export, col_space = st.columns([1, 5])
        with col_export:
            st.download_button(
                label="💾 Export do JSON",
                data=export_to_json(),
                file_name=f"prompty_export_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    # Vyhledávání
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Vyhledat v promptech", placeholder="Zadej klíčové slovo...")
    
    # Získání všech unikátních kategorií
    all_categories = list(set([p.get('kategorie', 'Bez kategorie') for p in prompts]))
    all_categories.sort()
    
    with col2:
        category_filter = st.selectbox("Kategorie", ["Všechny"] + all_categories)
    
    # Filtrování promptů
    filtered_prompts = prompts
    
    if search:
        filtered_prompts = [p for p in filtered_prompts 
                          if search.lower() in p['nazev'].lower() 
                          or search.lower() in p['text'].lower()
                          or search.lower() in p.get('popis', '').lower()]
    
    if category_filter != "Všechny":
        filtered_prompts = [p for p in filtered_prompts 
                          if p.get('kategorie') == category_filter]
    
    # Zobrazení promptů
    st.markdown(f"**Zobrazeno {len(filtered_prompts)} z {len(prompts)} promptů**")
    st.markdown("")
    
    if not filtered_prompts:
        st.info("🔍 Žádné prompty nenalezeny. Zkus změnit vyhledávání nebo filtr.")
    else:
        for i, prompt in enumerate(filtered_prompts):
            # Najdeme index v původním seznamu
            prompt_index = prompts.index(prompt)
            
            with st.expander(f"**{prompt['nazev']}** • {prompt.get('kategorie', 'Bez kategorie')}"):
                if prompt.get('popis'):
                    st.markdown(f"*{prompt['popis']}*")
                    st.markdown("")
                
                st.markdown("**Prompt:**")
                st.code(prompt['text'], language=None)
                
                if prompt.get('tagy'):
                    st.markdown(f"🏷️ **Tagy:** {', '.join(prompt['tagy'])}")
                
                # Tlačítka - zobrazí se podle toho, jestli je admin přihlášen
                if st.session_state.admin_logged_in:
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
                    
                    with col1:
                        if st.button("📋 Kopírovat", key=f"copy_{prompt_index}"):
                            st.success("✅ Zkopírováno!")
                    
                    with col2:
                        if st.button("✏️ Editovat", key=f"edit_{prompt_index}"):
                            st.session_state[f'editing_{prompt_index}'] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Smazat", key=f"delete_{prompt_index}"):
                            st.session_state[f'confirm_delete_{prompt_index}'] = True
                            st.rerun()
                    
                    # Potvrzení smazání
                    if st.session_state.get(f'confirm_delete_{prompt_index}', False):
                        st.warning("⚠️ Opravdu chceš smazat tento prompt?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Ano, smazat", key=f"confirm_yes_{prompt_index}"):
                                st.session_state.prompts.pop(prompt_index)
                                save_data(st.session_state.prompts)
                                st.session_state[f'confirm_delete_{prompt_index}'] = False
                                st.success("🗑️ Prompt byl smazán!")
                                st.rerun()
                        with col_no:
                            if st.button("❌ Ne, zrušit", key=f"confirm_no_{prompt_index}"):
                                st.session_state[f'confirm_delete_{prompt_index}'] = False
                                st.rerun()
                    
                    # Editační formulář
                    if st.session_state.get(f'editing_{prompt_index}', False):
                        st.markdown("---")
                        st.markdown("**✏️ Editovat prompt:**")
                        
                        with st.form(f"edit_form_{prompt_index}"):
                            new_nazev = st.text_input("Název", value=prompt['nazev'])
                            new_kategorie = st.text_input("Kategorie", value=prompt.get('kategorie', ''))
                            new_popis = st.text_area("Popis", value=prompt.get('popis', ''))
                            new_text = st.text_area("Text promptu", value=prompt['text'], height=200)
                            new_tagy = st.text_input("Tagy (oddělené čárkou)", 
                                                    value=', '.join(prompt.get('tagy', [])))
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                save_btn = st.form_submit_button("💾 Uložit změny")
                            with col_cancel:
                                cancel_btn = st.form_submit_button("❌ Zrušit")
                            
                            if save_btn:
                                st.session_state.prompts[prompt_index] = {
                                    'nazev': new_nazev,
                                    'kategorie': new_kategorie,
                                    'popis': new_popis,
                                    'text': new_text,
                                    'tagy': [t.strip() for t in new_tagy.split(',') if t.strip()],
                                    'datum': prompt.get('datum', datetime.now().strftime("%d.%m.%Y"))
                                }
                                save_data(st.session_state.prompts)
                                st.session_state[f'editing_{prompt_index}'] = False
                                st.success("✅ Změny uloženy!")
                                st.rerun()
                            
                            if cancel_btn:
                                st.session_state[f'editing_{prompt_index}'] = False
                                st.rerun()
                else:
                    # Pro běžné uživatele jen tlačítko kopírovat
                    if st.button("📋 Kopírovat", key=f"copy_{prompt_index}"):
                        st.success("✅ Text promptu zkopírován!")

# Záložka 2: Kategorie & Tagy
with tab2:
    st.header("📂 Kategorie a tagy")
    
    if not prompts:
        st.info("📭 Zatím nejsou žádné prompty v databázi.")
    else:
        # Seskupení podle kategorií
        categories_data = defaultdict(lambda: {'count': 0, 'tags': set(), 'prompts': []})
        
        for prompt in prompts:
            cat = prompt.get('kategorie', 'Bez kategorie')
            categories_data[cat]['count'] += 1
            categories_data[cat]['prompts'].append(prompt)
            if prompt.get('tagy'):
                categories_data[cat]['tags'].update(prompt['tagy'])
        
        # Seřazení kategorií podle abecedy
        sorted_categories = sorted(categories_data.keys())
        
        # Zobrazení kategorií - používáme unikátní klíče které se změní při každém načtení
        for idx, category in enumerate(sorted_categories):
            data = categories_data[category]
            
            # Generujeme unikátní klíč pro každý expander, který se mění s časem
            unique_key = f"cat_{category}_{datetime.now().timestamp()}"
            
            with st.expander(f"**{category}** ({data['count']} {'prompt' if data['count'] == 1 else 'prompty' if data['count'] < 5 else 'promptů'})", expanded=False, key=unique_key):
                
                # Tagy v této kategorii
                if data['tags']:
                    st.markdown("**🏷️ Používané tagy:**")
                    
                    # Zobrazení tagů jako tlačítka
                    cols = st.columns(4)
                    for idx, tag in enumerate(sorted(data['tags'])):
                        col_idx = idx % 4
                        with cols[col_idx]:
                            # Počet promptů s tímto tagem v této kategorii
                            tag_count = sum(1 for p in data['prompts'] if tag in p.get('tagy', []))
                            st.button(f"🏷️ {tag} ({tag_count})", key=f"tag_{category}_{tag}", use_container_width=True)
                    
                    st.markdown("---")
                
                # Seznam promptů v kategorii - nyní jako klikatelné expandery
                st.markdown("**📝 Prompty:**")
                for prompt_cat in data['prompts']:
                    # Najdeme index v původním seznamu
                    prompt_index_cat = prompts.index(prompt_cat)
                    
                    with st.expander(f"**{prompt_cat['nazev']}**"):
                        if prompt_cat.get('popis'):
                            st.markdown(f"*{prompt_cat['popis']}*")
                            st.markdown("")
                        
                        st.markdown("**Prompt:**")
                        st.code(prompt_cat['text'], language=None)
                        
                        if prompt_cat.get('tagy'):
                            st.markdown(f"🏷️ **Tagy:** {', '.join(prompt_cat['tagy'])}")
                        
                        # Tlačítko kopírovat pro všechny
                        if st.button("📋 Kopírovat", key=f"copy_cat_{category}_{prompt_index_cat}"):
                            st.success("✅ Text promptu zkopírován!")

# Záložka 3: Přidat prompt (pouze pro admina)
if st.session_state.admin_logged_in:
    with tab3:
        st.header("Přidat nový prompt")
        
        with st.form("add_prompt"):
            nazev = st.text_input("Název promptu *", placeholder="např. The Blindspot Cartographer")
            kategorie = st.text_input("Kategorie *", placeholder="např. Strategické myšlení, Marketing...")
            popis = st.text_area("Krátký popis", placeholder="Co tento prompt dělá?")
            text = st.text_area("Text promptu *", height=300, 
                              placeholder="Vlož zde celý prompt...")
            tagy = st.text_input("Tagy (oddělené čárkou)", 
                               placeholder="např. strategie, analýza, kritické myšlení")
            
            submit = st.form_submit_button("➕ Přidat prompt")
            
            if submit:
                if nazev and kategorie and text:
                    new_prompt = {
                        'nazev': nazev,
                        'kategorie': kategorie,
                        'popis': popis,
                        'text': text,
                        'tagy': [t.strip() for t in tagy.split(',') if t.strip()],
                        'datum': datetime.now().strftime("%d.%m.%Y")
                    }
                    st.session_state.prompts.append(new_prompt)
                    save_data(st.session_state.prompts)
                    st.success(f"✅ Prompt '{nazev}' byl úspěšně přidán!")
                    st.rerun()
                else:
                    st.error("⚠️ Vyplň prosím všechna povinná pole (označená *)")

# Záložka O projektu
if st.session_state.admin_logged_in:
    with tab4:
        st.header("O Promptovišti")
        st.markdown("""
        **Promptoviště** je sdílená databáze užitečných promptů pro práci s AI.
        
        ### Jak používat:
        1. **Procházej prompty** v záložce "Procházet prompty"
        2. **Vyhledávej** podle klíčových slov nebo filtruj podle kategorií
        3. **Prohlížej kategorie a tagy** pro inspiraci a objevování
        4. **Kopíruj** prompty a používej je ve svých AI konverzacích
        5. **Exportuj** celou databázi do JSON souboru pro zálohu
        
        ---
        *Vytvořeno s pomocí Claude & Streamlit 🤖*
        """)
else:
    with tab3:
        st.header("O Promptovišti")
        st.markdown("""
        **Promptoviště** je sdílená databáze užitečných promptů pro práci s AI.
        
        ### Jak používat:
        1. **Procházej prompty** v záložce "Procházet prompty"
        2. **Vyhledávej** podle klíčových slov nebo filtruj podle kategorií
        3. **Prohlížej kategorie a tagy** pro inspiraci a objevování
        4. **Kopíruj** prompty a používej je ve svých AI konverzacích
        
        ---
        *Vytvořeno s pomocí Claude & Streamlit 🤖*
        """)

# Footer
st.markdown("---")
st.markdown("*Máš nápad na vylepšení? Napiš administrátorovi!*")