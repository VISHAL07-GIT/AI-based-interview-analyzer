# AI Smart Interview Analyzer

This is a comprehensive, state-of-the-art web application designed to evaluate mock interviews and parse resumes using Python, Flask, SQLite, and client-side MediaPipe Face Mesh.

## Features

- **User Registration & Login**: Multi-user session management with secure password hashing.
- **Dynamic Question Studio**: Practice behavioral, technical, or general mock interview questions one-at-a-time.
- **Audio Voice Recording**: Real-time browser-based microphone recording using the `MediaRecorder` API.
- **Behavioral Camera Tracking**: Client-side video tracking utilizing Google MediaPipe Face Mesh to monitor eye contact, smiles, and posture.
- **NLP Answer Analysis**: Core algorithm evaluating:
  - **OpenAI Whisper Speech-to-Text** (with local online fallback).
  - **Sentiment Analysis** (TextBlob polarity).
  - **Speaking Speed** (Words Per Minute calculation).
  - **Confidence Checks** (filler words tracking: *um, actually, basically*).
  - **Grammar Suggestions** (structural corrections).
  - **Technical Skills Review** (evaluating mentions of Java, Python, SQL, React, Git, Docker, etc.).
- **Interactive Results Page**: Radar graphs using `Chart.js` illustrating scoring dimensions alongside comprehensive question transcripts and mistake corrections.
- **Resume Scanner**: Drag-and-drop PDF resume uploader displaying job skill match ratings and missing requirements.

---

## Directory Structure

```text
AI-Smart-Interview-Analyzer/
├── frontend/
│   ├── index.html          # Landing Page
│   ├── login.html          # Login Page
│   ├── register.html       # Register Page
│   ├── dashboard.html      # User Dashboard (History, Resume Upload)
│   ├── interview.html      # Active Interview Page (Webcam + Audio)
│   ├── result.html         # Report Page (Charts, Feedback)
│   ├── profile.html        # Profile Page
│   ├── css/
│   │   └── style.css       # Unified premium design system
│   └── js/
│       ├── auth.js         # Register, Login, Session handling
│       ├── dashboard.js    # Dashboard stats, list history, resume upload
│       ├── interview.js    # Recording, MediaPipe, progress tracker
│       └── result.js       # Chart.js integration & report parsing
└── backend/
    ├── app.py              # Main Flask server & API endpoints
    ├── database.py         # SQLAlchemy Database models
    ├── analyzer.py         # Whisper Transcription & NLP analysis
    ├── test_analyzer.py    # Verification testing suite
    └── requirements.txt    # Python dependencies
```

---

## Installation & Setup

### 1. Backend Setup (Flask Server)

1. Open a terminal and navigate to the project directory:
   ```bash
   cd c:\Users\ELCOT\project
   ```

2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows (Command Prompt)**:
     ```cmd
     venv\Scripts\activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\activate
     ```
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```

4. Install the required backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
   *Note*: To enable localized TextBlob corpora, run:
   ```bash
   python -m textblob.download_corpora
   ```

---

## Running Verification Tests

To verify that the database seeding, user registration hashing, filler word analysis, and grammar check algorithms are working correctly, run the integration test script:

```bash
python backend/test_analyzer.py
```

---

## Running the Web Application

1. **Launch the Flask Server**:
   ```bash
   python backend/app.py
   ```
   The API server will boot up at `http://localhost:5000`.

2. **Open the Frontend**:
   Simply open `frontend/index.html` in any modern web browser. Since it relies on static pages making asynchronous `fetch` requests to your local Flask backend, you do not need a separate frontend build server. You can double-click `index.html` or serve it using any simple static files extension (e.g., Live Server in VS Code, or `python -m http.server 8000` from the `frontend/` directory).

3. **Try the Flow**:
   - Register a new account on the register page.
   - Login to view the Dashboard.
   - Try dropping a PDF resume in the Resume Skill Check card.
   - Set up an interview session (e.g., select Technical category and 3 questions) and click **Start Interview**.
   - Grant camera and microphone access. Watch MediaPipe adjust eye contact and smiles as you move your head.
   - Record your answers and submit.
   - View your animated evaluation graphs and question scorecards!
