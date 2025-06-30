from flask import Flask, request, send_from_directory, jsonify
import os, uuid, asyncio, threading, time
import edge_tts
from werkzeug.exceptions import NotFound

app = Flask(__name__)
AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Cleanup old files thread
def cleanup_old_files():
    """Clean up audio files older than 1 hour"""
    while True:
        try:
            current_time = time.time()
            for filename in os.listdir(AUDIO_FOLDER):
                file_path = os.path.join(AUDIO_FOLDER, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        print(f"🗑️ Cleaned up old file: {filename}")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
        
        time.sleep(1800)  # Run every 30 minutes

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

# Async TTS generation function
async def generate_tts(text, output_path):
    """Generate TTS audio file using edge-tts"""
    voice = "en-US-JennyNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎤 WeatherBee TTS Server</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2196F3; text-align: center; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2196F3; }
            .endpoint code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
            a { color: #2196F3; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .status { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 WeatherBee TTS Server</h1>
            <p class="status">✅ Server is running</p>
            
            <div class="endpoint">
                <h3>Test Endpoints:</h3>
                <p><a href="/test">🔧 Test Server Status</a></p>
                <p><a href="/speak?text=Hello from WeatherBee">🗣️ Test TTS</a></p>
            </div>
            
            <div class="endpoint">
                <h3>API Usage:</h3>
                <p><code>GET /speak?text=YOUR_TEXT</code></p>
                <p>Returns JSON with audio URL for MP3 file</p>
            </div>
            
            <div class="endpoint">
                <h3>Example:</h3>
                <p><code>/speak?text=The temperature is 25 degrees</code></p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/test")
def test():
    return jsonify({
        "status": "OK",
        "message": "WeatherBee TTS Server is running",
        "version": "1.1",
        "endpoints": ["/", "/test", "/speak", "/audio/<filename>"],
        "voice": "en-US-JennyNeural"
    })

@app.route("/speak")
def speak():
    try:
        text = request.args.get("text", "").strip()
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Limit text length
        if len(text) > 500:
            return jsonify({"error": "Text too long (max 500 characters)"}), 400

        print(f"🗣️ Generating TTS: '{text}'")

        file_id = str(uuid.uuid4())
        mp3_path = os.path.join(AUDIO_FOLDER, file_id + ".mp3")

        # Run TTS generation
        try:
            asyncio.run(generate_tts(text, mp3_path))
        except Exception as tts_error:
            print(f"❌ TTS Generation Error: {str(tts_error)}")
            return jsonify({"error": "TTS generation failed"}), 500

        # Check if file was created
        if not os.path.exists(mp3_path):
            return jsonify({"error": "Audio file not generated"}), 500

        # Build URL - use request.url_root to get the base URL
        file_url = request.url_root + f"audio/{file_id}.mp3"
        
        print(f"✅ TTS generated: {file_url}")
        
        return jsonify({
            "status": "success",
            "message": "TTS generated successfully",
            "url": file_url,
            "file_id": file_id,
            "text": text
        })

    except Exception as e:
        print(f"❌ Error in /speak: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve audio files"""
    try:
        return send_from_directory(AUDIO_FOLDER, filename)
    except NotFound:
        return jsonify({"error": "Audio file not found"}), 404

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("🚀 Starting WeatherBee TTS Server...")
    print(f"📁 Audio folder: {os.path.abspath(AUDIO_FOLDER)}")
    
    # Create audio directory if it doesn't exist
    os.makedirs(AUDIO_FOLDER, exist_ok=True)
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)