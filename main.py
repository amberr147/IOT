from flask import Flask, request, send_from_directory, jsonify
import os, uuid, asyncio
import edge_tts
from pydub import AudioSegment

app = Flask(__name__)
AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return f"""
    <h1>🎤 TTS Server on Render</h1>
    <p><a href="/test">Test Server</a></p>
    <p><a href="/speak?text=hello">Test TTS</a></p>
    """

@app.route("/test")
def test():
    return jsonify({
        "status": "OK",
        "message": "TTS Server is running",
        "endpoints": ["/", "/test", "/speak", "/audio/<filename>"]
    })

@app.route("/speak")
def speak():
    try:
        text = request.args.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400

        print(f"🗣️  Generating TTS: '{text}'")

        file_id = str(uuid.uuid4())
        raw_path = os.path.join(AUDIO_FOLDER, file_id + "_raw.mp3")
        mp3_path = os.path.join(AUDIO_FOLDER, file_id + ".mp3")

        asyncio.run(generate_tts(text, raw_path, mp3_path))

        file_url = f"/audio/{file_id}.mp3"
        base_url = request.url_root.strip("/")
        return jsonify({"url": base_url + file_url, "filename": f"{file_id}.mp3"})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

async def generate_tts(text, raw_path, mp3_path):
    try:
        tts = edge_tts.Communicate(text, "en-US-JennyNeural")
        await tts.save(raw_path)

        sound = AudioSegment.from_file(raw_path)
        sound = sound.set_channels(1).set_frame_rate(22050)
        sound.export(mp3_path, format="mp3", bitrate="128k")

        if os.path.exists(raw_path):
            os.remove(raw_path)

    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        raise

@app.route("/audio/<filename>")
def get_audio(filename):
    try:
        return send_from_directory(AUDIO_FOLDER, filename)
    except Exception as e:
        return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
