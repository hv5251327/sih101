import os
import sqlite3
import urllib.parse
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

@app.route("/api/translate", methods=["POST"])
def translate_api():
    data = request.json or {}
    text = data.get("text", "")
    target = data.get("target_lang", "en")
    
    if target == "en" or not text.strip():
        return jsonify({"translated_text": text})

    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&q={urllib.parse.quote(text)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        res = r.json()
        if res and res[0]:
            out = "".join([segment[0] for segment in res[0] if segment and segment[0]])
            return jsonify({"translated_text": out})
    except Exception as e:
        print("Translation API error:", e)

    return jsonify({"translated_text": text})

if __name__ == "__main__":
    app.run(port=5000, debug=False)