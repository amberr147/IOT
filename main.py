from flask import Flask, request, send_from_directory, jsonify
import os, uuid, asyncio
import edge_tts

app = Flask(__name__)
AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return """
    <h1>🎤 TTS Server</h1>
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

        print(f"🗣️ Generating TTS: '{text}'")

        file_id = str(uuid.uuid4())
        mp3_path = os.path.join(AUDIO_FOLDER, file_id + ".mp3")

        try:
            # 🔥 Gọi async TTS và bắt lỗi cụ thể
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(generate_tts(text, mp3_path))
        except Exception as err:
            print(f"❌ Async error: {str(err)}")
            return jsonify({"error": "TTS generation failed"}), 500

        base_url = request.host_url.rstrip('/')
        file_url = f"{base_url}/audio/{file_id}.mp3"
        print(f"✅ Generated: {file_url}")

        return jsonify({"url": file_url, "filename": f"{file_id}.mp3"})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


async def generate_tts(text, mp3_path):
    try:
        print("🔧 Starting edge_tts...")
        tts = edge_tts.Communicate(text, "en-US-JennyNeural")
        await tts.save(mp3_path)
        print("✅ MP3 ready at:", mp3_path)
    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        raise

@app.route("/audio/<filename>")
def get_audio(filename):
    try:
        return send_from_directory(AUDIO_FOLDER, filename)
    except Exception as e:
        print(f"❌ Audio error: {str(e)}")
        return "File not found", 404

@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    print("🚀 Starting TTS Server...")
    app.run(host='0.0.0.0', port=5000)