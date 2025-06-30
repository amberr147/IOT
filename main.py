
from flask import Flask, request, send_from_directory, jsonify
import os, uuid, asyncio
import edge_tts
from pydub import AudioSegment
import socket


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


app = Flask(__name__)
AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)


local_ip = get_local_ip()


@app.route("/")
def home():
    return f"""
    <h1>🎤 TTS Server</h1>
    <p>Server IP: {local_ip}:5000</p>
    <p><a href="/test">Test Server</a></p>
    <p><a href="/speak?text=hello">Test TTS</a></p>
    """


@app.route("/test")
def test():
    return jsonify({
        "status": "OK",
        "message": "TTS Server is running",
        "ip": local_ip,
        "port": 5000,
        "endpoints": ["/", "/test", "/speak", "/audio/<filename>"]
    })


@app.route("/speak")
def speak():
    try:
        client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        print(f"📝 TTS Request from {client_ip}")
       
        text = request.args.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400


        print(f"🗣️  Generating TTS: '{text}'")
       
        file_id = str(uuid.uuid4())
        raw_path = os.path.join(AUDIO_FOLDER, file_id + "_raw.mp3")
        mp3_path = os.path.join(AUDIO_FOLDER, file_id + ".mp3")
       
        # Generate TTS
        asyncio.run(generate_tts(text, raw_path, mp3_path))
       
        # Return URL
        file_url = f"http://{local_ip}:5000/audio/{file_id}.mp3"  # Đổi thành MP3
        print(f"✅ Generated: {file_url}")
       
        return jsonify({"url": file_url, "filename": f"{file_id}.mp3"})
       
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


async def generate_tts(text, raw_path, mp3_path):
    try:
        print("🎵 Creating TTS...")
        tts = edge_tts.Communicate(text, "en-US-JennyNeural")
        await tts.save(raw_path)
       
        print("🔄 Converting to MP3...")
        sound = AudioSegment.from_file(raw_path)
        # Giữ nguyên MP3 cho ESP32
        sound = sound.set_channels(1).set_frame_rate(22050)  # Tần số phù hợp cho ESP32
        sound.export(mp3_path, format="mp3", bitrate="128k")
       
        if os.path.exists(raw_path):
            os.remove(raw_path)
        print("✅ MP3 ready")
       
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


if __name__ == "__main__":
    print("🚀 Starting TTS Server...")
    print(f"📍 Server IP: {local_ip}")
    print(f"🌐 Access at: http://{local_ip}:5000")
    print("Press Ctrl+C to stop")
   
    app.run(host='0.0.0.0', port=5000)
