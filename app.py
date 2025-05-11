from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import wikipedia
import uuid
import os
import time
from google.cloud import texttospeech

# === Hilfsfunktion: Alte MP3-Dateien löschen ===
def cleanup_old_files(folder_path, max_age_days=3):
    now = time.time()
    cutoff = now - (max_age_days * 86400)
    if not os.path.exists(folder_path):
        return
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
            try:
                os.remove(filepath)
                print(f"🧹 Alte Datei gelöscht: {filepath}")
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen von {filepath}: {e}")

# === Google Cloud TTS Initialisierung ===
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-credentials.json"
tts_client = texttospeech.TextToSpeechClient()

# === Flask Setup ===
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    title = data.get("title")
    lang = data.get("lang", "de")

    if not title:
        return jsonify({"error": "Kein Titel übergeben."}), 400

    try:
        wikipedia.set_lang(lang)
        page = wikipedia.page(title)
        text = page.content

        # Kürze Text auf max. 5 Sätze
        summary = '. '.join(text.split('. ')[:5]) + '.'
        print("🧠 Zusammenfassung:", summary)

        # TTS-Konfiguration je nach Sprache
        lang_map = {
            "de": ("de-DE", "de-DE-Wavenet-F"),
            "en": ("en-US", "en-US-Wavenet-D"),
            "fr": ("fr-FR", "fr-FR-Wavenet-B"),
            "es": ("es-ES", "es-ES-Wavenet-A")
        }
        tts_lang, tts_voice = lang_map.get(lang, ("de-DE", "de-DE-Wavenet-F"))

        synthesis_input = texttospeech.SynthesisInput(text=summary)
        voice = texttospeech.VoiceSelectionParams(language_code=tts_lang, name=tts_voice)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # MP3 speichern
        filename = f"{uuid.uuid4().hex}.mp3"
        output_dir = os.path.join("static", "audio")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        file_size = os.path.getsize(output_path)
        print(f"💾 MP3 gespeichert unter: {output_path} ({file_size} Bytes)")

        return jsonify({
            "summary": summary,
            "audio_url": f"/audio/{filename}"
        })

    except Exception as e:
        print("❌ Fehler:", e)
        return jsonify({"error": f"Fehler: {str(e)}"}), 500

# MP3-Dateien ausliefern
@app.route("/audio/<filename>")
def get_audio(filename):
    return send_from_directory("static/audio", filename)

# === Flask starten ===
if __name__ == "__main__":
    audio_folder = os.path.join("static", "audio")
    os.makedirs(audio_folder, exist_ok=True)
    cleanup_old_files(audio_folder, max_age_days=3)
    app.run(debug=True)

