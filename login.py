# login.py
import streamlit as st

def login():
    st.set_page_config(page_title="🔐 Logowanie - AudioReader", layout="centered")
    st.title("🔐 Zaloguj się do AudioReader")

    st.markdown("""
    Aby korzystać z aplikacji AudioReader, musisz podać własny klucz API OpenAI (`sk-...`).
    Nie przechowujemy żadnych kluczy – dane pozostają tylko w Twojej przeglądarce.
    """)

    api_key = st.text_input("🔑 Podaj swój klucz API OpenAI", type="password")

    if api_key:
        if api_key.startswith("sk-") and len(api_key) > 30:
            st.session_state["api_key"] = api_key
            st.success("✅ Zalogowano pomyślnie! Uruchom teraz `app.py`.")
        else:
            st.error("❌ Niepoprawny format klucza. Klucz powinien zaczynać się od 'sk-'.")

if __name__ == "__main__":
    login()
