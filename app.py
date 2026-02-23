"""
Lecture Voice-to-Notes Generator
=================================
Main Flask application file.
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import tempfile
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
from utils.transcriber import transcribe_audio
from utils.processor import process_transcript
from utils.pdf_generator import generate_pdf

# ── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'webm', 'm4a', 'ogg'}


def allowed_file(filename):
    """Check if uploaded file has an allowed audio extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Receive audio file or microphone recording,
    transcribe it via ElevenLabs, then process with HuggingFace.
    Returns JSON with transcript, summary, bullets, quiz, flashcards.
    """
    try:
        audio_file = None
        temp_path = None

        # ── Handle uploaded file ──────────────────────────────────────────
        if 'audio' in request.files:
            file = request.files['audio']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Use mp3/wav/webm/m4a/ogg'}), 400

            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)
            audio_file = temp_path

        # ── Handle base64 blob from microphone recording ──────────────────
        elif request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            if not data or 'audio_blob' not in data:
                return jsonify({'error': 'No audio data received'}), 400

            import base64
            audio_bytes = base64.b64decode(data['audio_blob'])
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'mic_recording.webm')
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            audio_file = temp_path

        else:
            return jsonify({'error': 'No audio provided'}), 400

        # ── Step 1: Transcribe audio ──────────────────────────────────────
        print("[INFO] Transcribing audio...")
        transcript = transcribe_audio(audio_file)
        if not transcript:
            return jsonify({'error': 'Transcription failed or returned empty text'}), 500

        # ── Step 2: Process transcript (summarize, quiz, flashcards) ─────
        print("[INFO] Processing transcript with AI...")
        results = process_transcript(transcript)

        # ── Cleanup temp file ─────────────────────────────────────────────
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({
            'success': True,
            'transcript': transcript,
            'summary': results.get('summary', ''),
            'bullets': results.get('bullets', []),
            'quiz': results.get('quiz', []),
            'flashcards': results.get('flashcards', []),
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/generate-pdf', methods=['POST'])
def create_pdf():
    """Generate a downloadable PDF from the notes data."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        pdf_path = generate_pdf(data)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name='lecture_notes.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"[ERROR] PDF generation: {str(e)}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("🎓 Lecture Voice-to-Notes Generator starting...")
    print("📌 Open your browser at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)