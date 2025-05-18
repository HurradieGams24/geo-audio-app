from flask import Flask, render_template, request, jsonify
import os
import json
import wikipedia
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import base64
import io
import requests

app = Flask(__name__)

# Konfiguration
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "heic"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lade Landmark-Daten
with open("landmarks.json", "r", encoding="utf-8") as f:
    landmarks = json.load(f)

# Hilfsfunktionen

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_gps_from_exif(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None
        gps_info = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = value[t]
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = convert_to_degrees(gps_info["GPSLatitude"])
            lon = convert_to_degrees(gps_info["GPSLongitude"])
            return (lat, lon)
        return None
    except Exception as e:
        print(f"EXIF-GPS-Fehler: {e}")
        return None

def convert_to_degrees(value):
    d, m, s = value
    return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

def find_landmark_by_coords(coords, threshold=0.0005):
    lat, lon = coords
    for landmark in landmarks:
        d_lat = abs(lat - landmark["latitude"])
        d_lon = abs(lon - landmark["longitude"])
        if d_lat < threshold and d_lon < threshold:
            return landmark
    return None

def find_landmark_by_name(name):
    for l in landmarks:
        if l["name"].lower() == name.lower():
            return l
    return None

def get_structured_summary(title):
    try:
        wikipedia.set_lang("de")
        summary = wikipedia.summary(title, sentences=5)
        return f"<h2>{title}</h2><p>{summary}</p>"
    except Exception as e:
        return f"<p>Fehler beim Laden der Wikipedia-Zusammenfassung für <strong>{title}</strong>: {str(e)}</p>"

def analyze_with_vision_api(image_path):
    try:
        with open(image_path, "rb") as image_file:
            content = base64.b64encode(image_file.read()).decode("utf-8")

        api_key = os.environ.get("GOOGLE_VISION_API_KEY")
        if not api_key:
            return None

        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "requests": [
                {
                    "image": {"content": content},
                    "features": [{"type": "LABEL_DETECTION", "maxResults": 5}]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        labels = response.json()["responses"][0].get("labelAnnotations", [])
        return [label["description"] for label in labels]
    except Exception as e:
        print(f"Vision API Fehler: {e}")
        return []

# Routen

@app.route("/")
def index():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return "Kein Bild ausgewählt."

    file = request.files["image"]
    if file.filename == "":
        return "Dateiname ist leer."

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        gps_coords = extract_gps_from_exif(filepath)
        landmark = find_landmark_by_coords(gps_coords) if gps_coords else None

        manual_landmark = request.form.get("manual_landmark")
        if not landmark and manual_landmark:
            landmark = find_landmark_by_name(manual_landmark)

        if landmark:
            summary = get_structured_summary(landmark["name"])
        else:
            labels = analyze_with_vision_api(filepath)
            summary = f"<p>Keine Landmark gefunden. Vision-Labels: {', '.join(labels)}</p>"

        return render_template("result.html", summary=summary)

    return "Ungültiger Dateityp."

if __name__ == "__main__":
    app.run(debug=True)
