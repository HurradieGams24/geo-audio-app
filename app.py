from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import wikipedia
import uuid
import os
import base64
import requests

from google.cloud import texttospeech
from PIL import Image
import io

# === GOOGLE API SETUP ===
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-credentials.json"
tts_client = texttospeech.TextToSpeechClient()

# === FLASK APP ===
app = Flask(__name__, static_url_path='/static')
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    title = data.get("title")
    lang = data.get("lang", "de")

    try:
        wikipedia.set_lang(lang)
        page = wikipedia.page(title)
        text = page.content
        summary = '. '.join(text.split('. ')[:5]) + '.'

        filename = generate_tts(summary, lang)
        return jsonify({"summary": summary, "audio_url": f"/static/audio/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analyze-photo", methods=["POST"])
def analyze_photo():
    try:
        print("🚀 /analyze-photo wurde aufgerufen")
        lang = request.form.get("lang", "de")
        file = request.files["photo"]
        image_bytes = file.read()

        detected_title = detect_landmark_with_placeholder(image_bytes)
        print(f"🔍 Erkanntes Objekt: {detected_title}")

        if not detected_title:
            return jsonify({"error": "Kein bekanntes Objekt erkannt."}), 404

        wikipedia.set_lang(lang)
        page = wikipedia.page(detected_title)
        text = page.content
        summary = '. '.join(text.split('. ')[:5]) + '.'

        filename = generate_tts(summary, lang)
        print("✅ Zusammenfassung + Audio fertig")
        return jsonify({
            "title": detected_title,
            "summary": summary,
            "audio_url": f"/static/audio/{filename}"
        })

    except Exception as e:
        print(f"❌ Fehler bei Analyse: {e}")
        return jsonify({"error": str(e)}), 500

def generate_tts(text, lang):
    lang_map = {
        "de": ("de-DE", "de-DE-Wavenet-F"),
        "en": ("en-US", "en-US-Wavenet-D"),
        "fr": ("fr-FR", "fr-FR-Wavenet-B"),
        "es": ("es-ES", "es-ES-Wavenet-A")
    }
    tts_lang, tts_voice = lang_map.get(lang, ("de-DE", "de-DE-Wavenet-F"))

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=tts_lang, name=tts_voice)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    filename = f"{uuid.uuid4().hex}.mp3"
    path = os.path.join("static", "audio")
    os.makedirs(path, exist_ok=True)
    output_path = os.path.join(path, filename)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

    return filename

def detect_landmark_with_placeholder(image_bytes):
    print("🖼️ Dummy-Erkennung aktiv – gebe fixen Titel zurück")
    return "Eiffelturm"  # Für Tests: Sicher ein Wikipedia-Artikel vorhanden

if __name__ == "__main__":
    app.run(debug=True)
