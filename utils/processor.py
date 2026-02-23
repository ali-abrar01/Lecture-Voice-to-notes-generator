"""
utils/processor.py  — FULLY REWRITTEN
=======================================
Processes transcript text and generates:
  • Summary       • Bullet points
  • Quiz (5 Q&A)  • Flashcards (5 cards)

"""

import os
import re
import time
import requests

# ── API Configuration ─────────────────────────────────────────────────────────
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', 'YOUR_HUGGINGFACE_API_TOKEN_HERE')
HF_BASE_URL  = "https://api-inference.huggingface.co/models"

# ── Models ────────────────────────────────────────────────────────────────────
SUMMARIZATION_MODEL = "facebook/bart-large-cnn"   # dedicated summariser
TEXT_GEN_MODEL      = "google/flan-t5-large"      # reliable on free HF tier


# ════════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def process_transcript(transcript: str) -> dict:
    """
    Main pipeline. Returns dict with summary, bullets, quiz, flashcards.
    Always returns non-empty values — uses Python fallbacks if API fails.
    """
    if HF_API_TOKEN == 'YOUR_HUGGINGFACE_API_TOKEN_HERE':
        print("[Processor] No HF token — using Python-only fallback.")
        return _full_python_fallback(transcript)

    # Trim to safe length (flan-t5-large input limit ~512 tokens ≈ 2000 chars)
    text = transcript[:2500].strip()

    results = {}

    print("[Processor] 1/4 — Generating summary ...")
    results['summary'] = _generate_summary(text)

    print("[Processor] 2/4 — Extracting key points ...")
    results['bullets'] = _generate_bullets(text)

    print("[Processor] 3/4 — Generating quiz ...")
    results['quiz'] = _generate_quiz(text)

    print("[Processor] 4/4 — Generating flashcards ...")
    results['flashcards'] = _generate_flashcards(text)

    # Guarantee non-empty output — fill any blank section with Python fallback
    fb = _full_python_fallback(transcript)
    if not results.get('summary'):     results['summary']    = fb['summary']
    if not results.get('bullets'):     results['bullets']    = fb['bullets']
    if not results.get('quiz'):        results['quiz']       = fb['quiz']
    if not results.get('flashcards'):  results['flashcards'] = fb['flashcards']

    return results


# ════════════════════════════════════════════════════════════════════════════════
#  INDIVIDUAL GENERATORS
# ════════════════════════════════════════════════════════════════════════════════

def _generate_summary(text: str) -> str:
    """BART summarisation — dedicated seq2seq model for this task."""
    payload = {
        "inputs": text,
        "parameters": {"max_length": 180, "min_length": 40, "do_sample": False},
    }
    raw = _call_hf_api(SUMMARIZATION_MODEL, payload)
    if isinstance(raw, list) and raw:
        return raw[0].get("summary_text", "").strip()
    return ""


def _generate_bullets(text: str) -> list:
    """Ask flan-t5 to produce a numbered list of key points."""
    prompt = (
        "List 6 key facts from the following lecture text. "
        "Write each fact as a complete sentence on a new line numbered 1 to 6.\n\n"
        f"Lecture text: {text}"
    )
    raw_text = _call_text_gen(prompt, max_new_tokens=300)
    bullets  = _parse_numbered_lines(raw_text)
    return bullets[:6]


def _generate_quiz(text: str) -> list:
    """
    Generate 5 quiz Q&A pairs.
    One API call per question — smaller, more reliable, easier to parse.
    """
    quiz = []
    short_text = text[:1200]

    for i in range(1, 6):
        prompt = (
            f"Read the lecture below and write quiz question number {i} "
            f"with its correct answer.\n"
            f"Reply in this exact format:\n"
            f"Question: [your question]\n"
            f"Answer: [your answer]\n\n"
            f"Lecture: {short_text}"
        )
        raw = _call_text_gen(prompt, max_new_tokens=150)
        qa  = _parse_single_qa(raw)
        if qa:
            quiz.append(qa)
        if len(quiz) >= 5:
            break

    return quiz


def _generate_flashcards(text: str) -> list:
    """
    Generate 5 study flashcards.
    One API call per card for reliable parsing.
    """
    cards = []
    short_text = text[:1200]

    for i in range(1, 6):
        prompt = (
            f"Read the lecture below and create flashcard number {i}. "
            f"Pick one important term or concept and define it.\n"
            f"Reply in this exact format:\n"
            f"Term: [term or concept]\n"
            f"Definition: [clear explanation]\n\n"
            f"Lecture: {short_text}"
        )
        raw  = _call_text_gen(prompt, max_new_tokens=120)
        card = _parse_single_flashcard(raw)
        if card:
            cards.append(card)
        if len(cards) >= 5:
            break

    return cards


# ════════════════════════════════════════════════════════════════════════════════
#  HUGGINGFACE API HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _call_hf_api(model: str, payload: dict, retries: int = 3, wait: int = 25):
    """
    POST to HuggingFace Inference API with retry on 503 (model loading).
    Returns parsed JSON or None.
    BUG FIX: headers built here, not at module level.
    """
    # Build headers fresh every call so token changes are picked up
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type":  "application/json",
    }
    url = f"{HF_BASE_URL}/{model}"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 503:
                # Model is cold-starting — read the estimated wait time
                try:
                    eta = float(resp.json().get("estimated_time", wait))
                except Exception:
                    eta = float(wait)
                sleep_sec = min(eta, 60)
                print(f"[HF] Model loading (attempt {attempt}/{retries}), "
                      f"sleeping {sleep_sec:.0f}s ...")
                time.sleep(sleep_sec)
                continue

            if resp.status_code == 401:
                print("[HF] Bad API token. Set HF_API_TOKEN correctly.")
                return None

            if resp.status_code == 429:
                print(f"[HF] Rate limited. Sleeping {wait}s ...")
                time.sleep(wait)
                continue

            print(f"[HF] HTTP {resp.status_code}: {resp.text[:250]}")
            return None

        except requests.exceptions.Timeout:
            print(f"[HF] Timeout attempt {attempt}/{retries}")
            if attempt < retries:
                time.sleep(10)
        except Exception as exc:
            print(f"[HF] Exception: {exc}")
            return None

    return None


def _call_text_gen(prompt: str, max_new_tokens: int = 200) -> str:
    """
    Call flan-t5-large and return the generated string.
    flan-t5 is seq2seq: it never echoes the prompt back (unlike GPT-style models).
    """
    payload = {
        "inputs":     prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "do_sample":      False,   # greedy decode = consistent output
        },
    }
    result = _call_hf_api(TEXT_GEN_MODEL, payload)

    if result is None:
        return ""
    if isinstance(result, list) and result:
        return result[0].get("generated_text", "").strip()
    if isinstance(result, str):
        return result.strip()
    return ""


# ════════════════════════════════════════════════════════════════════════════════
#  PARSERS  — multi-strategy, never return None
# ════════════════════════════════════════════════════════════════════════════════

def _parse_numbered_lines(text: str) -> list:
    """Extract items from a numbered/bulleted list. Tries multiple formats."""
    if not text:
        return []

    items = []

    # Strategy 1: lines starting with a digit
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^[\d]+[.):\-]\s*(.+)', line)
        if m and len(m.group(1).strip()) > 8:
            items.append(m.group(1).strip())

    if items:
        return items

    # Strategy 2: bullet markers
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^[-*•]\s*(.+)', line)
        if m and len(m.group(1).strip()) > 8:
            items.append(m.group(1).strip())

    if items:
        return items

    # Strategy 3: any non-empty line longer than 25 chars
    return [l.strip() for l in text.splitlines() if len(l.strip()) > 25]


def _parse_single_qa(text: str):
    """
    Parse a Question/Answer pair from raw model output.
    Returns {"question": ..., "answer": ...} or None.
    """
    if not text:
        return None

    question = ""
    answer   = ""

    # Strategy 1: look for explicit Question: / Answer: labels
    q_match = re.search(r'(?:Question|Q)\s*\d*\s*[:\-]\s*(.+)', text, re.IGNORECASE)
    a_match = re.search(r'(?:Answer|A)\s*\d*\s*[:\-]\s*(.+)',   text, re.IGNORECASE)

    if q_match:
        question = q_match.group(1).strip()
    if a_match:
        answer   = a_match.group(1).strip()

    if question and answer:
        return {"question": question, "answer": answer}

    # Strategy 2: first two non-empty lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 2:
        return {"question": lines[0], "answer": lines[1]}

    # Strategy 3: one long line → treat as question
    if lines and len(lines[0]) > 15:
        return {"question": lines[0], "answer": "(See lecture notes)"}

    return None


def _parse_single_flashcard(text: str):
    """
    Parse a Term/Definition flashcard from raw model output.
    Returns {"front": ..., "back": ...} or None.
    """
    if not text:
        return None

    front = ""
    back  = ""

    # Strategy 1: explicit labels
    f_match = re.search(
        r'(?:Term|Front|Concept|Topic|Key\s*term)\s*[:\-]\s*(.+)',
        text, re.IGNORECASE
    )
    b_match = re.search(
        r'(?:Definition|Back|Explanation|Meaning|Description)\s*[:\-]\s*(.+)',
        text, re.IGNORECASE
    )

    if f_match:
        front = f_match.group(1).strip()
    if b_match:
        back  = b_match.group(1).strip()

    if front and back:
        return {"front": front, "back": back}

    # Strategy 2: first line = term, rest = definition
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 2:
        return {"front": lines[0], "back": " ".join(lines[1:])}
    if len(lines) == 1 and len(lines[0]) > 10:
        words = lines[0].split()
        return {"front": " ".join(words[:min(4, len(words))]), "back": lines[0]}

    return None


# ════════════════════════════════════════════════════════════════════════════════
#  PURE-PYTHON FALLBACK  (zero internet required — always produces output)
# ════════════════════════════════════════════════════════════════════════════════

def _extract_sentences(text: str) -> list:
    """Split text into clean sentences longer than 20 chars."""
    text = re.sub(r'\s+', ' ', text.strip())
    raw  = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    for chunk in raw:
        for sub in chunk.splitlines():
            sub = sub.strip(' -•*')
            if len(sub) > 20:
                sentences.append(sub)
    return sentences


def _full_python_fallback(transcript: str) -> dict:
    """
    Extract summary, bullets, quiz and flashcards directly from the
    transcript text using only Python — no API calls needed.
    This is both the no-token fallback AND the guarantee layer when
    API calls return empty results.
    """
    sentences = _extract_sentences(transcript)

    # Absolute last resort
    if not sentences:
        return {
            "summary":    transcript[:400] or "Transcript unavailable.",
            "bullets":    ["Review the full transcript for key points."],
            "quiz":       [{"question": "What was the main topic?",
                            "answer": "Review the transcript."}],
            "flashcards": [{"front": "Main topic",
                            "back": transcript[:150] or "See transcript."}],
        }

    # ── Summary: first 5 sentences ────────────────────────────────────────────
    summary = ' '.join(sentences[:5])

    # ── Bullets: evenly spaced across the lecture ─────────────────────────────
    step = max(1, len(sentences) // 6)
    bullets = []
    for i in range(0, len(sentences), step):
        if len(sentences[i]) > 25:
            bullets.append(sentences[i])
        if len(bullets) >= 6:
            break
    # Top-up to 6 if needed
    for s in sentences:
        if s not in bullets and len(s) > 25:
            bullets.append(s)
        if len(bullets) >= 6:
            break

    # ── Quiz: fill-in-the-blank from content sentences ────────────────────────
    quiz  = []
    pool  = [s for s in sentences if len(s.split()) >= 6]
    for s in pool[:8]:
        words = s.split()
        # Find rightmost word with length > 3 (skip articles/prepositions)
        key_idx = len(words) - 1
        while key_idx > 0 and len(words[key_idx].rstrip('.,!?;:"')) <= 3:
            key_idx -= 1
        key = words[key_idx].strip('.,!?;:"\'')
        blanked = words[:key_idx] + ['______'] + words[key_idx+1:]
        question = ' '.join(blanked).rstrip('.,!?') + '?'
        quiz.append({"question": question, "answer": key})
        if len(quiz) >= 5:
            break

    # ── Flashcards: first N words as term, full sentence as definition ─────────
    flashcards = []
    pool2 = [s for s in sentences if len(s.split()) >= 7]
    for s in pool2:
        words     = s.split()
        front_len = min(4, max(2, len(words) // 5))
        front     = ' '.join(words[:front_len]).rstrip('.,!?;:"\'')
        flashcards.append({"front": front, "back": s})
        if len(flashcards) >= 5:
            break

    return {
        "summary":    summary,
        "bullets":    bullets[:6],
        "quiz":       quiz[:5],
        "flashcards": flashcards[:5],
    }