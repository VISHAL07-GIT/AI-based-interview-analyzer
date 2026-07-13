import re
from textblob import TextBlob
import pypdf

# Initialize Whisper fallback flag
whisper_model = None
try:
    import whisper
    # We will load the model lazily on demand or try to load it here
    # To prevent heavy memory usage at import, we'll load it when transcribing
except ImportError:
    whisper = None

# Technical skill dictionary
SKILL_KEYWORDS = [
    "java", "python", "sql", "html", "css", "react", "docker", "git", 
    "javascript", "node", "express", "flask", "django", "postgresql", 
    "mongodb", "kubernetes", "aws", "cloud", "api", "rest", "json", 
    "oop", "algorithms", "c++", "c#", "typescript", "angular", "vue"
]

# Filler words list
FILLER_WORDS = ["um", "uh", "actually", "basically", "like", "you know", "sort of", "kind of"]

# Grammatical issues list & corrections
GRAMMAR_RULES = [
    (r"\b(i|he|she|it|they|we|you)\s+goes\b", "go"),
    (r"\b(he|she|it)\s+don't\b", "doesn't"),
    (r"\b(i|they|we|you)\s+doesn't\b", "don't"),
    (r"\b(i)\s+is\b", "am"),
    (r"\b(he|she|it)\s+are\b", "is"),
    (r"\b(they|we|you)\s+is\b", "are"),
    (r"\b(am|is|are|was|were|be|been|being)\s+went\b", "gone"),
    (r"\b(has|have|had)\s+went\b", "gone"),
    (r"\b(has|have|had)\s+did\b", "done"),
    (r"\b(did)\s+(went|saw|came|took|done|ate)\b", "did [base verb, e.g. go/see/come/take/do/eat]"),
    (r"\b(more)\s+(better|faster|slower|stronger|easier|harder)\b", "\\2"), # remove "more" before comparative
]

def transcribe_audio(audio_path):
    """
    Transcribes audio file using OpenAI Whisper.
    Falls back to SpeechRecognition library (Google Web API),
    and if that fails, returns an error message or mock transcription.
    """
    global whisper_model
    
    # 1. Try Whisper
    if whisper is not None:
        try:
            if whisper_model is None:
                print("Loading Whisper model...")
                whisper_model = whisper.load_model("tiny")  # Use the small, fast model
            print(f"Transcribing {audio_path} using Whisper...")
            result = whisper_model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as e:
            print(f"Whisper transcription failed: {e}. Falling back to SpeechRecognition...")
    
    # 2. Fallback to SpeechRecognition (standard Google online recognizer)
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = r.record(source)
            print("Transcribing using SpeechRecognition (Google API)...")
            text = r.recognize_google(audio_data)
            return text.strip()
    except Exception as e:
        print(f"SpeechRecognition failed: {e}")
        
    # 3. Final mock fallback if everything fails (useful for local sandbox testing without input audio config)
    return "[Demo Speech]: I am a backend developer. Actually, I have strong experience in Python, SQL, and Git. Um, I enjoy building REST APIs with Flask. Basically, we use Docker for deployment, and it is more better."


def analyze_sentiment(text):
    """
    Determines if the statement is Positive, Neutral, or Negative.
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.15:
        return "Positive"
    elif polarity < -0.15:
        return "Negative"
    else:
        return "Neutral"


def calculate_speaking_speed(text, duration_seconds):
    """
    Calculates words per minute (WPM).
    Returns speed_score (out of 15) and WPM value.
    """
    words = text.split()
    word_count = len(words)
    
    if duration_seconds <= 0:
        return 15, 0
        
    wpm = int((word_count / duration_seconds) * 60)
    
    # Standard speaking rate: 110 - 150 WPM
    if 110 <= wpm <= 150:
        score = 15
    elif 90 <= wpm < 110 or 150 < wpm <= 170:
        score = 12
    elif 70 <= wpm < 90 or 170 < wpm <= 190:
        score = 9
    else:
        score = 6
        
    return score, wpm


def detect_filler_words(text):
    """
    Counts filler words: um, uh, actually, basically, like, you know.
    """
    text_lower = text.lower()
    total_fillers = 0
    filler_breakdown = {}
    
    for filler in FILLER_WORDS:
        # Match word boundaries to prevent matching parts of other words
        pattern = r'\b' + re.escape(filler) + r'\b'
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            filler_breakdown[filler] = matches
            total_fillers += matches
            
    return total_fillers, filler_breakdown


def check_grammar_and_vocab(text):
    """
    Analyzes grammar mistakes using regex rules.
    Analyzes vocabulary diversity (Type-Token Ratio).
    Returns grammar_score (out of 20), corrections list, and vocab_rating.
    """
    corrections = []
    text_lower = text.lower()
    
    # 1. Check rules
    for pattern, replacement in GRAMMAR_RULES:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            corrections.append({
                "mistake": match.group(0),
                "suggestion": replacement,
                "context": text[max(0, match.start()-15):min(len(text), match.end()+15)]
            })
            
    # Sentence ending punctuation check (heuristics)
    if len(text) > 5 and not text.strip()[-1] in ['.', '!', '?']:
        corrections.append({
            "mistake": "No ending punctuation",
            "suggestion": "End your sentences with a period.",
            "context": text[-10:]
        })
        
    # 2. Grammar Score Calculation (start at 20, subtract 3 per unique issue found, min 5)
    deductions = len(corrections) * 3
    grammar_score = max(5, 20 - deductions)
    
    # 3. Vocabulary richness check (TTR: Type-Token Ratio)
    words = [w.strip(".,!?\"'") for w in text_lower.split() if w]
    if not words:
        vocab_rating = "Low"
    else:
        unique_words = set(words)
        ttr = len(unique_words) / len(words)
        if ttr > 0.8:
            vocab_rating = "Excellent"
        elif ttr > 0.6:
            vocab_rating = "Good"
        else:
            vocab_rating = "Average"
            
    return grammar_score, corrections, vocab_rating


def analyze_technical_skills(text):
    """
    Detects technical skills in the text and scores technical knowledge (out of 25).
    """
    text_lower = text.lower()
    skills_found = []
    
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            skills_found.append(skill)
            
    # Calculate score
    # 10 pts for first skill, 7 for second, 8 for third -> Max 25
    count = len(skills_found)
    if count == 0:
        score = 5  # baseline score for trying
    elif count == 1:
        score = 15
    elif count == 2:
        score = 22
    else:
        score = 25
        
    return score, skills_found


def analyze_answer(text, question_text, duration_seconds, eye_contact_ratio, smile_ratio):
    """
    Performs full NLP and behavioral evaluations on a question response.
    Compiles scores:
      - Grammar: out of 20 (based on checks)
      - Communication: out of 20 (based on sentiment, vocabulary, sentence length)
      - Technical Knowledge: out of 25 (based on keywords)
      - Confidence: out of 20 (based on filler words penalty and eye contact)
      - Speaking Speed: out of 15 (based on WPM)
    Total Score is out of 100.
    """
    # 1. Sentiment
    sentiment = analyze_sentiment(text)
    
    # 2. Speaking speed
    speed_score, wpm = calculate_speaking_speed(text, duration_seconds)
    
    # 3. Filler words
    filler_count, filler_breakdown = detect_filler_words(text)
    
    # 4. Grammar
    grammar_score, corrections, vocab_rating = check_grammar_and_vocab(text)
    
    # 5. Technical Skills
    tech_score, skills_found = analyze_technical_skills(text)
    
    # 6. Communication Score (out of 20)
    # Higher for Good vocab, Positive sentiment, and reasonable sentence lengths
    comm_score = 12
    if vocab_rating == "Excellent":
        comm_score += 4
    elif vocab_rating == "Good":
        comm_score += 2
        
    if sentiment == "Positive":
        comm_score += 4
    elif sentiment == "Neutral":
        comm_score += 2
        
    # Cap communication score at 20, min at 5
    comm_score = min(20, max(5, comm_score))
    
    # 7. Confidence Score (out of 20)
    # Based on: Filler words penalty, eye contact ratio, and smile ratio
    # Fillers penalty: subtract 2 per filler word from 10 points (min 3)
    filler_pts = max(3, 10 - (filler_count * 2))
    # Eye contact contribution: eye_contact_ratio represents percentage (0-100)
    # We allocate 10 points for eye contact (ratio/10)
    eye_pts = int((eye_contact_ratio / 100) * 10)
    confidence_score = filler_pts + eye_pts
    
    # 8. Overall Question Score (Grammar [20] + Comm [20] + Tech [25] + Confidence [20] + Speed [15] = 100)
    overall_score = grammar_score + comm_score + tech_score + confidence_score + speed_score
    
    # Generate tailored feedback
    feedback_points = []
    if filler_count > 3:
        feedback_points.append(f"Try to reduce filler words. You used fillers (like {', '.join(filler_breakdown.keys())}) {filler_count} times.")
    else:
        feedback_points.append("Great job avoiding filler words! You spoke very clearly.")
        
    if grammar_score < 15:
        feedback_points.append("Review your grammar. Watch out for subject-verb agreement or phrasing errors.")
        
    if wpm < 90:
        feedback_points.append(f"Your speaking pace ({wpm} WPM) was a bit slow. Aim for around 110-150 WPM.")
    elif wpm > 160:
        feedback_points.append(f"You spoke quickly ({wpm} WPM). Try pausing between thoughts for clarity.")
    else:
        feedback_points.append(f"Excellent speaking pace at {wpm} WPM.")
        
    if eye_contact_ratio < 60:
        feedback_points.append(f"Try to maintain eye contact with the camera. Eye contact was around {eye_contact_ratio}%.")
        
    if not skills_found and tech_score < 15:
        feedback_points.append("Incorporate more relevant technical skills or industry keywords in your answer.")
        
    feedback_text = " ".join(feedback_points)
    
    return {
        "text": text,
        "sentiment": sentiment,
        "wpm": wpm,
        "filler_words_count": filler_count,
        "grammar_score": grammar_score,
        "communication_score": comm_score,
        "technical_score": tech_score,
        "confidence_score": confidence_score,
        "speed_score": speed_score,
        "overall_score": overall_score,
        "corrections": corrections,
        "skills_found": skills_found,
        "feedback_text": feedback_text
    }


def parse_resume(file_path):
    """
    Parses PDF/txt resume to find tech skills and matches against a general software job profile.
    Returns: match_score, matched_skills, missing_skills, experience_mentions.
    """
    text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        # Try raw text reading in case it is a simple text file
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return {"error": "Could not parse file. Please upload a PDF or Text file."}

    text_lower = text.lower()
    
    # 1. Identify skills
    matched_skills = []
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            matched_skills.append(skill)
            
    # Standard profile skills for Comparison
    required_profile_skills = ["python", "sql", "git", "docker", "javascript", "react", "api", "cloud"]
    
    missing_skills = [s for s in required_profile_skills if s not in matched_skills]
    
    # Calculate score
    found_required = [s for s in required_profile_skills if s in matched_skills]
    match_score = int((len(found_required) / len(required_profile_skills)) * 100)
    
    # Look for experience indicators (e.g. years of experience)
    years_matches = re.findall(r'(\d+)\+?\s*years?\s+of\s+experience', text_lower)
    exp = f"{years_matches[0]} Years" if years_matches else "Not explicitly specified (e.g. 'X years of experience')"

    return {
        "match_score": match_score,
        "matched_skills": [s.capitalize() for s in matched_skills],
        "missing_skills": [s.capitalize() for s in missing_skills],
        "experience": exp,
        "total_skills_count": len(matched_skills)
    }
