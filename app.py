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

# Inicjalizacja opisów klipów
for i in range(1, 4):
    if f"clip_{i}_desc" not in st.session_state:
        st.session_state[f"clip_{i}_desc"] = ""

# === PRAWA KOLUMNA: opis ===
st.title("🎧 AudioReader")
st.markdown("""
Narzędzie stworzone z myślą o podcasterach – umożliwia automatyczne tworzenie transkrypcji wywiadów, 
generowanie napisów oraz przygotowanie materiałów do publikacji 
w mediach społecznościowych.

ﺡ **Uwaga:** 
Przed wczytaniem nowego pliku należy odświeżyć stronę, aby wyczyścić pamięć poprzedniego pliku.
📦 **Maksymalny rozmiar pliku: 200MB**
""")

# === LEWA KOLUMNA: upload + przetwarzanie ===
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📄 Wczytaj plik wideo")
    video_file = st.file_uploader("Wybierz plik (MP4 lub MOV)", type=["mp4", "mov"])

    if video_file is not None:
        st.write(f"📦 Rozmiar pliku: {video_file.size / (1024 * 1024):.2f} MB")

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as temp_video:
            temp_video.write(video_file.read())
            video_path = temp_video.name

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

        audio_bytes = Path(audio_path).read_bytes()
        st.audio(audio_bytes, format="audio/mp3")

        with open(audio_path, "rb") as f:
            st.download_button("⬇️ Pobierz audio (.mp3)", data=f, file_name="audio_z_wideo.mp3")

        if st.button("📝 Transkrybuj plik wideo"):
            with st.spinner("⏳ Transkrypcja w toku..."):
                with open(audio_path, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        file=f,
                        model=AUDIO_TRANSCRIBE_MODEL,
                        response_format="verbose_json"
                    )
                    st.session_state["video_transcript"] = transcript.text

        if st.session_state["video_transcript"]:
            txt_file = BytesIO(st.session_state["video_transcript"].encode("utf-8"))
            txt_file.name = "transkrypcja.txt"
            st.download_button("⬇️ Pobierz transkrypcję (.txt)", data=txt_file, file_name="transkrypcja.txt")

with col2:
    if st.session_state.get("video_transcript"):
        st.markdown("---")
        st.subheader("📄 Pełna transkrypcja z pliku")
        st.text_area("Transkrypcja", value=st.session_state["video_transcript"], height=400, disabled=True)

        if st.button("📌 Podsumuj rozmowę"):
            with st.spinner("🔍 Analizuję transkrypcję..."):
                system_prompt = "Jesteś asystentem do analizy rozmów. Podsumuj rozmowę w 3-4 zdaniach."
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

                topic_prompt = "Wypisz dokładnie 5 najważniejszych tematów poruszonych w rozmowie w postaci punktów."
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

# === KLIPY DO SOCIAL MEDIÓW ===
st.markdown("---")
st.header("🎬 Klipy do social mediów")

for i in range(1, 4):
    st.markdown(f"## 🎥 Klip {i} (max 1 minuta)")
    clip = st.file_uploader(f"Wczytaj Klip {i}", type=["mp4", "mov"], key=f"clip_{i}")

    if clip:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(clip.name).suffix) as temp_clip:
            temp_clip.write(clip.read())
            clip_path = temp_clip.name

        if st.button(f"✏️ Stwórz opis i hashtagi dla Klipu {i}"):
            clip_audio_path = clip_path.rsplit(".", 1)[0] + ".mp3"
            subprocess.run([
                "/usr/local/bin/ffmpeg", "-hide_banner", "-y",
                "-i", clip_path, "-vn", clip_audio_path
            ], check=True)

            with open(clip_audio_path, "rb") as f:
                transcription = openai_client.audio.transcriptions.create(
                    file=f,
                    model=AUDIO_TRANSCRIBE_MODEL,
                    response_format="text"
                )

            transcript_text = transcription.strip()

            description_prompt = (
                "Na podstawie poniższej transkrypcji stwórz krótki opis (max 300 znaków) filmu do mediów społecznościowych oraz wygeneruj 10 unikalnych hashtagów oddzielonych spacją. Nie powtarzaj hashtagów."
            )

            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": description_prompt},
                    {"role": "user", "content": transcript_text}
                ]
            )

            output = response.choices[0].message.content.strip()
            st.session_state[f"clip_{i}_desc"] = output

    if st.session_state.get(f"clip_{i}_desc"):
        st.text_area("Opis + Hashtagi", value=st.session_state[f"clip_{i}_desc"], height=180)
