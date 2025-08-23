from io import BytesIO
import tempfile
from pathlib import Path
import os
import subprocess  # ✅ dodaj to

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
st.set_page_config(page_title="AudioReader", page_icon="🎧", layout="wide")

# --- Inicjalizacja sesji ---
if "video_transcript" not in st.session_state:
    st.session_state["video_transcript"] = ""

# --- Layout: 2 kolumny ---
col1, col2 = st.columns([1, 2])

# === LEWA KOLUMNA: upload + przetwarzanie ===
with col1:
    st.subheader("📤 Wczytaj plik wideo")
    video_file = st.file_uploader("Wybierz plik (MP4 lub MOV)", type=["mp4", "mov"])

    if video_file is not None:
        # Zapisz plik tymczasowo
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as temp_video:
            temp_video.write(video_file.read())
            video_path = temp_video.name

      # 🔧 KONWERSJA DO WAV przy użyciu subprocess + jawna ścieżka
            audio_path = video_path.rsplit(".", 1)[0] + ".wav"
        try:
            ffmpeg_path = "/usr/local/bin/ffmpeg"  # ścieżka z `brew install ffmpeg`
            subprocess.run([
             ffmpeg_path, "-hide_banner", "-y",
            "-i", video_path,
            "-vn",
            audio_path
        ], check=True)
            st.success("🎧 Audio wyodrębnione z wideo")
        except Exception as e:
            st.error(f"❌ Błąd konwersji przez ffmpeg: {e}")
            st.stop()

        # 🔊 Odtwarzacz audio
        audio_bytes = Path(audio_path).read_bytes()
        st.audio(audio_bytes, format="audio/wav")

        # 📝 TRANSKRYPCJA
        if st.button("📝 Transkrybuj plik wideo"):
            with st.spinner("⏳ Transkrypcja w toku..."):
                with open(audio_path, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        file=f,
                        model=AUDIO_TRANSCRIBE_MODEL,
                        response_format="verbose_json"
                    )
                    st.session_state["video_transcript"] = transcript.text

        # 🎬 NAPISY
        if st.button("🎬 Wygeneruj napisy format (.srt)"):
            with st.spinner("⏳ Tworzę napisy..."):
                with open(audio_path, "rb") as f:
                    srt_result = openai_client.audio.transcriptions.create(
                        file=f,
                        model=AUDIO_TRANSCRIBE_MODEL,
                        response_format="srt"
                    )
                srt_file = BytesIO(srt_result.encode("utf-8"))
                srt_file.name = "napisy.srt"
                st.success("✅ Napisy gotowe")
                st.download_button("⬇️ Pobierz napisy", data=srt_file, file_name="napisy.srt")

# === PRAWA KOLUMNA: opis i transkrypcja ===
with col2:
    st.title("🎧 AudioReader")
    st.markdown("""
    Narzędzie stworzone z myślą o podcasterach – umożliwia automatyczne tworzenie transkrypcji wywiadów, 
    generowanie napisów oraz przygotowanie materiałów do publikacji 
    w mediach społecznościowych.
    """)

# === PEŁNA TRANSKRYPCJA POD OPISEM ===
if st.session_state["video_transcript"]:
    st.markdown("---")
    st.subheader("📄 Pełna transkrypcja z pliku")
    st.text_area(
        "Transkrypcja",
        value=st.session_state["video_transcript"],
        height=400,
        disabled=True
    )
