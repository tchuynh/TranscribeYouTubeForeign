from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, VideoUnavailable, TranscriptsDisabled
import requests
import re
import os
from flask import Flask, request, jsonify, render_template
from youtube_transcript_api.formatters import TextFormatter

app = Flask(__name__)

# Optional proxy support — toggle with USE_PROXY
USE_PROXY = True
PROXY_CREDS = os.getenv('PROXY_CREDS')

PROXY = {
    "http": f"http://{PROXY_CREDS}@p.webshare.io:9999",
    "https": f"http://{PROXY_CREDS}@p.webshare.io:9999"
}

if USE_PROXY:
    original_get = requests.get
    def proxied_get(*args, **kwargs):
        kwargs.setdefault("proxies", PROXY)
        return original_get(*args, **kwargs)
    requests.get = proxied_get

@app.route('/')
def home():
    return render_template('index.html')

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies = PROXY)

        try:
            # Try native English
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            # Fallback: try to translate an auto-generated transcript
            transcript = next(
                (t.translate('en') for t in transcript_list if t.is_generated and t.is_translatable),
                None
            )
            if not transcript:
                return {"error": "No usable transcript found."}

        # return {"transcript": transcript.fetch()}  # JSON-safe format
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript.fetch())
        return {"transcript": text}

    except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound) as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        data = request.get_json(force=True)
        url = data.get("url")
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        result = get_transcript(video_id)
        print("result", result)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
