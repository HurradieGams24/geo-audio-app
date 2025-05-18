import os
import base64
import json

creds_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
if not creds_b64:
    print("❌ Umgebungsvariable GOOGLE_CREDENTIALS_BASE64 nicht gefunden.")
    exit(1)

try:
    creds_json = base64.b64decode(creds_b64).decode("utf-8")
    print("✅ Base64 erfolgreich dekodiert.")
except Exception as e:
    print(f"❌ Fehler beim Base64-Decode: {e}")
    exit(1)

try:
    creds = json.loads(creds_json)
    print("✅ JSON ist gültig. Projekt-ID:", creds.get("project_id"))
except Exception as e:
    print(f"❌ Fehler beim JSON-Parsing: {e}")
    exit(1)

# Optional: in Datei schreiben
with open("google-credentials.json", "w") as f:
    f.write(creds_json)
print("📁 Datei google-credentials.json geschrieben.")
