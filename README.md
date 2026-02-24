# 🎓 Lecture Voice-to-Notes Generator

> Turn any lecture recording into instant study materials — transcript, summary, quiz, flashcards, and a downloadable PDF — powered by **ElevenLabs** (speech-to-text) and **HuggingFace** (AI notes).

---

## 📁 Project Structure

```
Lecture-voice to notes/
├── app.py                    ← Flask backend (main entry point)
├── requirements.txt          ← Python dependencies
├── .env                      ← API keys (ELEVENLABS_API_KEY, HF_API_TOKEN)
├── README.md                 ← This file
│
├── templates/
│   └── index.html            ← Main web UI
│
├── static/
│   ├── favicon.ico           ← Site favicon
│   ├── favicon-32x32.png     ← Favicon variants
│   ├── favicon-16x16.png     ← Favicon variants
│   ├── app.js                ← Frontend logic (recording, uploads, results)
│   ├── style.css             ← Styling
│   ├── css/                  ← Additional CSS (future use)
│   └── js/                   ← Additional JavaScript (future use)
│
├── utils/
│   ├── __init__.py
│   ├── transcriber.py        ← ElevenLabs Speech-to-Text module
│   ├── processor.py          ← HuggingFace AI (summary, quiz, flashcards)
│   └── pdf_generator.py      ← PDF creation with ReportLab
│
├── venv/                     ← Virtual environment (locally installed)
│   └── (created by: python -m venv venv)
│
└── __pycache__/              ← Python cache files (auto-generated)
```

---

## ⚡ Setup Instructions

### Step 1 — Open the project folder

```bash
cd "d:\My_projects\Lecture-voice to notes"
```

---

### Step 2 — Create and activate Python virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell):
venv\Scripts\Activate.ps1

# Or Windows Command Prompt:
venv\Scripts\activate
```

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Create `.env` file with API keys

In the project root, create a `.env` file with your API credentials:

```dotenv
# .env
ELEVENLABS_API_KEY=sk_your_elevenlabs_api_key_here
HF_API_TOKEN=hf_your_huggingface_token_here
```

**Get your API keys:**
- **ElevenLabs**: https://elevenlabs.io → Sign up → Profile → API Keys
- **HuggingFace**: https://huggingface.co → Sign up → Settings → Access Tokens → New Token

⚠️ **Never commit `.env` to git — it contains secrets!**

---

### Step 5 — Run the app

```bash
python app.py
```

Open your browser and go to: **http://localhost:5000**

---

## 🎮 How to Use

1. **Upload** an audio file (MP3, WAV, M4A, OGG, WebM) **OR** click **Record** to record directly from your microphone
2. Click **✨ Generate Notes**
3. Wait ~30–60 seconds for AI processing
4. Browse your results:
   - 📝 **Transcript** — Full text of the lecture
   - 📋 **Summary** — Short paragraph overview
   - ⭐ **Key Points** — Bullet points to remember
   - ❓ **Quiz** — 5 questions (click to reveal answers)
   - 🃏 **Flashcards** — Flip cards for active recall
5. Click **⬇️ Download PDF** to get all notes in a styled PDF

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `ElevenLabs API key not configured` | Set `ELEVENLABS_API_KEY` env variable |
| `HuggingFace API token not configured` | Set `HF_API_TOKEN` env variable |
| Microphone not working | Allow microphone in browser permissions |
| Model loading slowly | HuggingFace cold-starts models; wait 30s and retry |
| 50MB file size limit | Split large audio files using Audacity or FFmpeg |

---

## 📝 API Cost Optimization

This project is designed to minimize API costs:
- Transcription: One call per audio file (ElevenLabs free tier = 10 min/month)
- AI Processing: Text is truncated to 3,000 chars before sending to HuggingFace
- HuggingFace Inference API: **Free** for standard models
- All results are cached in-browser for the session

---

## 🎓 Technologies Used

| Layer | Tech |
|---|---|
| Backend | Python + Flask |
| Speech-to-Text | ElevenLabs Scribe v1 |
| Summarization | facebook/bart-large-cnn |
| Quiz & Flashcards | mistralai/Mistral-7B-Instruct-v0.3 |
| PDF Generation | ReportLab |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Recording | Browser MediaRecorder API |

---

## 📄 License

MIT — Free to use, modify, and submit for your university project!
