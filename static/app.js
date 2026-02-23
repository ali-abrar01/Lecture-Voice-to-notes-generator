/**
 * app.js — Lecture Voice-to-Notes Generator
 * ==========================================
 * Handles:
 *  - Tab switching (Upload / Record)
 *  - Drag & drop file upload
 *  - Microphone recording using MediaRecorder API
 *  - Sending audio to Flask backend
 *  - Displaying results (transcript, summary, bullets, quiz, flashcards)
 *  - PDF download
 *  - Error handling & toasts
 */

// ── State ────────────────────────────────────────────────────────────────────
let mediaRecorder = null;     // MediaRecorder instance for mic
let audioChunks = [];         // Collected audio data blobs
let recordingTimer = null;    // Interval ID for the timer
let recordingSeconds = 0;     // Elapsed seconds
let uploadedFile = null;      // File object from file input or drop
let recordedBlob = null;      // Blob from microphone recording
let activeMode = 'upload';    // 'upload' or 'record'
let notesData = {};           // Stores results for PDF download

// ── DOM References ───────────────────────────────────────────────────────────
const tabBtns      = document.querySelectorAll('.tab');
const tabContents  = document.querySelectorAll('.tab-content');
const dropzone     = document.getElementById('dropzone');
const fileInput    = document.getElementById('file-input');
const filePreview  = document.getElementById('file-preview');
const fileNameDisp = document.getElementById('file-name-display');
const removeFileBtn= document.getElementById('remove-file');
const recordBtn    = document.getElementById('record-btn');
const stopBtn      = document.getElementById('stop-btn');
const timerEl      = document.getElementById('timer');
const recStatus    = document.getElementById('recorder-status');
const micVisual    = document.getElementById('mic-visual');
const audioPlayback= document.getElementById('audio-playback');
const generateBtn  = document.getElementById('generate-btn');
const btnText      = document.querySelector('.btn-text');
const btnLoader    = document.querySelector('.btn-loader');
const overlay      = document.getElementById('processing-overlay');
const resultsSection = document.getElementById('results-section');
const downloadBtn  = document.getElementById('download-pdf-btn');
const errorToast   = document.getElementById('error-toast');
const toastMsg     = document.getElementById('toast-message');
const toastClose   = document.getElementById('toast-close');

// ── Tab Switching ────────────────────────────────────────────────────────────
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    activeMode = btn.dataset.tab;
    document.getElementById(`tab-${activeMode}`).classList.add('active');
    updateGenerateBtn();
  });
});

// ── Drag & Drop ──────────────────────────────────────────────────────────────
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});

// Click anywhere on dropzone to open file picker
dropzone.addEventListener('click', (e) => {
  if (e.target !== fileInput) fileInput.click();
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
});

function handleFileSelect(file) {
  // Validate file type
  const allowed = ['audio/mpeg', 'audio/wav', 'audio/webm', 'audio/ogg',
                   'audio/mp4', 'video/mp4', 'audio/x-m4a'];
  if (!allowed.includes(file.type) && !file.name.match(/\.(mp3|wav|webm|ogg|m4a|mp4)$/i)) {
    showError('Please upload an audio file (MP3, WAV, WebM, OGG, M4A)');
    return;
  }
  uploadedFile = file;
  fileNameDisp.textContent = `📎 ${file.name} (${formatBytes(file.size)})`;
  filePreview.classList.remove('hidden');
  updateGenerateBtn();
}

removeFileBtn.addEventListener('click', () => {
  uploadedFile = null;
  fileInput.value = '';
  filePreview.classList.add('hidden');
  updateGenerateBtn();
});

// ── Microphone Recording ─────────────────────────────────────────────────────
recordBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);

async function startRecording() {
  try {
    // Request microphone permission
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Reset state
    audioChunks = [];
    recordedBlob = null;
    recordingSeconds = 0;
    timerEl.textContent = '00:00';
    audioPlayback.classList.add('hidden');
    audioPlayback.src = '';

    // Create MediaRecorder with webm format (widely supported)
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      // Combine chunks into a single Blob
      recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const audioURL = URL.createObjectURL(recordedBlob);
      audioPlayback.src = audioURL;
      audioPlayback.classList.remove('hidden');
      stream.getTracks().forEach(t => t.stop());  // Release microphone
      updateGenerateBtn();
    };

    mediaRecorder.start(1000);  // Collect data every 1 second

    // ── UI Updates ────────────────────────────────────────────────────────
    recordBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    micVisual.classList.add('recording');
    recStatus.textContent = '🔴 Recording in progress...';

    // Start timer
    recordingTimer = setInterval(() => {
      recordingSeconds++;
      const m = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
      const s = String(recordingSeconds % 60).padStart(2, '0');
      timerEl.textContent = `${m}:${s}`;
    }, 1000);

  } catch (err) {
    showError('Microphone access denied. Please allow microphone permission in your browser.');
    console.error('[Recording Error]', err);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  clearInterval(recordingTimer);

  // Reset UI
  recordBtn.classList.remove('hidden');
  stopBtn.classList.add('hidden');
  micVisual.classList.remove('recording');
  recStatus.textContent = '✅ Recording saved! Preview below.';
}

// ── Generate Button State ────────────────────────────────────────────────────
function updateGenerateBtn() {
  const hasUpload = activeMode === 'upload' && uploadedFile !== null;
  const hasRecord = activeMode === 'record' && recordedBlob !== null;
  generateBtn.disabled = !(hasUpload || hasRecord);
}

// ── Main: Send Audio & Get Notes ─────────────────────────────────────────────
generateBtn.addEventListener('click', async () => {
  setLoading(true);
  showProcessingOverlay();

  try {
    let response;

    if (activeMode === 'upload' && uploadedFile) {
      // ── File Upload mode: use FormData ────────────────────────────────
      const formData = new FormData();
      formData.append('audio', uploadedFile);

      setStep('transcribe');
      response = await fetch('/transcribe', {
        method: 'POST',
        body: formData
      });

    } else if (activeMode === 'record' && recordedBlob) {
      // ── Microphone mode: convert to base64 and send JSON ──────────────
      const base64 = await blobToBase64(recordedBlob);

      setStep('transcribe');
      response = await fetch('/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_blob: base64 })
      });
    }

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || `HTTP ${response.status}`);
    }

    setStep('summarize');
    const data = await response.json();

    if (!data.success) throw new Error(data.error || 'Unknown error');

    setStep('quiz');
    notesData = data;   // Store for PDF download

    setTimeout(() => {
      setStep('flash');
      setTimeout(() => {
        hideProcessingOverlay();
        setLoading(false);
        displayResults(data);
      }, 600);
    }, 600);

  } catch (err) {
    hideProcessingOverlay();
    setLoading(false);
    showError(err.message);
    console.error('[Generate Error]', err);
  }
});

// ── Display Results ───────────────────────────────────────────────────────────
function displayResults(data) {
  resultsSection.classList.remove('hidden');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Transcript
  document.getElementById('transcript-text').textContent =
    data.transcript || 'Transcript not available.';

  // Summary
  document.getElementById('summary-text').textContent =
    data.summary || 'Summary not available.';

  // Bullet Points
  const bulletsList = document.getElementById('bullets-list');
  bulletsList.innerHTML = '';
  (data.bullets || []).forEach(point => {
    const li = document.createElement('li');
    li.textContent = point;
    bulletsList.appendChild(li);
  });

  // Quiz
  const quizGrid = document.getElementById('quiz-grid');
  quizGrid.innerHTML = '';
  (data.quiz || []).forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'quiz-item';
    div.innerHTML = `
      <div class="quiz-number">Question ${i + 1}</div>
      <div class="quiz-question">${escapeHtml(item.question)}</div>
      <button class="quiz-answer-toggle" onclick="toggleAnswer(this)">👁 Reveal Answer</button>
      <div class="quiz-answer">${escapeHtml(item.answer)}</div>
    `;
    quizGrid.appendChild(div);
  });

  // Flashcards
  const flashGrid = document.getElementById('flashcard-grid');
  flashGrid.innerHTML = '';
  (data.flashcards || []).forEach(card => {
    const div = document.createElement('div');
    div.className = 'flashcard';
    div.innerHTML = `
      <div class="flashcard-inner">
        <div class="flashcard-front">${escapeHtml(card.front)}</div>
        <div class="flashcard-back">${escapeHtml(card.back)}</div>
      </div>
    `;
    div.addEventListener('click', () => div.classList.toggle('flipped'));
    flashGrid.appendChild(div);
  });
}

// ── Result Tabs ───────────────────────────────────────────────────────────────
document.querySelectorAll('.result-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.result-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`result-${tab.dataset.result}`).classList.add('active');
  });
});

// ── Quiz Answer Toggle ────────────────────────────────────────────────────────
function toggleAnswer(btn) {
  const answerDiv = btn.nextElementSibling;
  const isVisible = answerDiv.style.display === 'block';
  answerDiv.style.display = isVisible ? 'none' : 'block';
  btn.textContent = isVisible ? '👁 Reveal Answer' : '🙈 Hide Answer';
}

// ── PDF Download ──────────────────────────────────────────────────────────────
downloadBtn.addEventListener('click', async () => {
  try {
    downloadBtn.textContent = '⏳ Generating PDF...';
    downloadBtn.disabled = true;

    const response = await fetch('/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(notesData)
    });

    if (!response.ok) throw new Error('PDF generation failed');

    // Trigger browser download
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lecture_notes.pdf';
    a.click();
    URL.revokeObjectURL(url);

  } catch (err) {
    showError('Failed to generate PDF: ' + err.message);
  } finally {
    downloadBtn.textContent = '⬇️ Download PDF';
    downloadBtn.disabled = false;
  }
});

// ── Processing Overlay Helpers ────────────────────────────────────────────────
const steps = ['transcribe', 'summarize', 'quiz', 'flash'];

function showProcessingOverlay() {
  overlay.classList.remove('hidden');
  steps.forEach(s => {
    const el = document.getElementById(`step-${s}`);
    el.classList.remove('active', 'done');
  });
}

function hideProcessingOverlay() {
  overlay.classList.add('hidden');
}

function setStep(currentStep) {
  const idx = steps.indexOf(currentStep);
  steps.forEach((s, i) => {
    const el = document.getElementById(`step-${s}`);
    el.classList.remove('active', 'done');
    if (i < idx) el.classList.add('done');
    else if (i === idx) el.classList.add('active');
  });
}

// ── Loading State ─────────────────────────────────────────────────────────────
function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  btnText.classList.toggle('hidden', isLoading);
  btnLoader.classList.toggle('hidden', !isLoading);
}

// ── Error Toast ───────────────────────────────────────────────────────────────
function showError(message) {
  toastMsg.textContent = message;
  errorToast.classList.remove('hidden');
  // Auto-hide after 6 seconds
  setTimeout(() => errorToast.classList.add('hidden'), 6000);
}

toastClose.addEventListener('click', () => errorToast.classList.add('hidden'));

// ── Utilities ─────────────────────────────────────────────────────────────────

/** Convert a Blob to base64 string (returns just the data part, no prefix) */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // reader.result is "data:audio/webm;base64,<data>"
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/** Format bytes to human-readable size */
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Escape HTML special chars to prevent XSS */
function escapeHtml(text) {
  if (!text) return '';
  return text.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}