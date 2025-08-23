from io import BytesIO
import tempfile
from pathlib import Path
import os
import subprocess

import streamlit as st
from dotenv import dotenv_values
from openai import OpenAI

# --- Konfiguracja środowiska i klienta OpenAI ---
env = dotenv_values(".env")
AUDIO_TRANSCRIBE_MODEL = "whisper-1"

@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=env["OPENAI_API_KEY"])

openai_client = get_openai_client()

# --- Konfiguracja strony ---
st.set_page_config(page_title="AudioReader", page_icon="🎷", layout="wide")

# --- Inicjalizacja sesji ---
if "video_transcript" not in st.session_state:
    st.session_state["video_transcript"] = ""
if "summary_text" not in st.session_state:
    st.session_state["summary_text"] = ""
if "key_topics" not in st.session_state:
    st.session_state["key_topics"] = []

# === PRAWA KOLUMNA: opis ===
st.title("🎧 AudioReader")
st.markdown("""
Narzędzie stworzone z myślą o podcasterach – umożliwia automatyczne tworzenie transkrypcji wywiadów, 
generowanie napisów oraz przygotowanie materiałów do publikacji 
w mediach społecznościowych.

ℹ️ **Uwaga:** 
Przed wczytaniem nowego pliku należy odświeżyć stronę, aby wyczyścić pamięć poprzedniego pliku.
📦 **Maksymalny rozmiar pliku: 200MB**
""")

# --- Layout: 2 kolumny ---
col1, col2 = st.columns([1, 2])

# === LEWA KOLUMNA: upload + przetwarzanie ===
with col1:
    st.subheader("📄 Wczytaj plik wideo")
    video_file = st.file_uploader("Wybierz plik (MP4 lub MOV)", type=["mp4", "mov"])

    if video_file is not None:
        st.write(f"📦 Rozmiar pliku: {video_file.size / (1024 * 1024):.2f} MB")

        # Zapisz plik tymczasowo
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as temp_video:
            temp_video.write(video_file.read())
            video_path = temp_video.name

        # KONWERSJA DO MP3
        audio_path = video_path.rsplit(".", 1)[0] + ".mp3"
        try:
            ffmpeg_path = "/usr/local/bin/ffmpeg"
            subprocess.run([
                ffmpeg_path, "-hide_banner", "-y",
                "-i", video_path,
                "-vn", "-ar", "44100", "-ac", "1", "-b:a", "128k",
                audio_path
            ], check=True)
            st.success("🎷 Audio wyodrębnione z wideo")
        except Exception as e:
            st.error(f"❌ Błąd konwersji przez ffmpeg: {e}")
            st.stop()

        # Odtwarzacz audio
        audio_bytes = Path(audio_path).read_bytes()
        st.audio(audio_bytes, format="audio/mp3")

        # Pobierz plik MP3
        with open(audio_path, "rb") as f:
            st.download_button("⬇️ Pobierz audio (.mp3)", data=f, file_name="audio_z_wideo.mp3")

        # TRANSKRYPCJA
        if st.button("📝 Transkrybuj plik wideo"):
            with st.spinner("⏳ Transkrypcja w toku..."):
                with open(audio_path, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        file=f,
                        model=AUDIO_TRANSCRIBE_MODEL,
                        response_format="verbose_json"
                    )
                    st.session_state["video_transcript"] = transcript.text

        # EKSPORT TRANSKRYPCJI DO TXT
        if st.session_state["video_transcript"]:
            txt_file = BytesIO(st.session_state["video_transcript"].encode("utf-8"))
            txt_file.name = "transkrypcja.txt"
            st.download_button("⬇️ Pobierz transkrypcję (.txt)", data=txt_file, file_name="transkrypcja.txt")

# === PRAWA KOLUMNA: transkrypcja i analiza ===
with col2:
    if st.session_state.get("video_transcript"):
        st.markdown("---")
        st.subheader("📄 Pełna transkrypcja z pliku")
        st.text_area(
            "Transkrypcja",
            value=st.session_state["video_transcript"],
            height=400,
            disabled=True
        )

        if st.button("📌 Podsumuj rozmowę"):
            with st.spinner("🔍 Analizuję transkrypcję..."):
                system_prompt = (
                    "Jesteś asystentem do analizy rozmów. "
                    "Podsumuj rozmowę w 3-4 zdaniach."
                )
                user_prompt = st.session_state["video_transcript"]

                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )

                result = response.choices[0].message.content.strip()
                st.session_state["summary_text"] = result

                # Nowa analiza tematów po podsumowaniu
                topic_prompt = (
                    "Wypisz dokładnie 5 najważniejszych tematów poruszonych w rozmowie w postaci punktów."
                )
                topic_response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": topic_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )

                topic_lines = topic_response.choices[0].message.content.strip().split("\n")
                cleaned_topics = []
                for line in topic_lines:
                    stripped = line.strip()
                    if stripped:
                        if ". " in stripped:
                            cleaned_topics.append(stripped.split(". ", 1)[-1])
                        else:
                            cleaned_topics.append(stripped)
                st.session_state["key_topics"] = cleaned_topics[:5]

    if st.session_state.get("summary_text"):
        st.markdown("---")
        st.subheader("🧠 Podsumowanie rozmowy")
        st.write(st.session_state["summary_text"])

    if st.session_state.get("key_topics"):
        st.subheader("🔑 Najważniejsze tematy rozmowy:")
        for i, topic in enumerate(st.session_state["key_topics"], start=1):
            st.markdown(f"**{i}.** {topic}")
