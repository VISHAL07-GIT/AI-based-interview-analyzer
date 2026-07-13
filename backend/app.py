import os
import uuid
import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from database import db, User, InterviewQuestion, Report, InterviewResult
from analyzer import transcribe_audio, analyze_answer, parse_resume

app = Flask(__name__)
app.secret_key = "smart_interview_analyzer_secret_key"
CORS(app, supports_credentials=True)

# Database Configuration (SQLite by default, easy to point to MySQL)
# Example MySQL URI: mysql+pymysql://username:password@localhost/db_name
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_interview.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create folders for uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, "audio")
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, "resumes")
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)

# Helper function to seed questions if database is empty
def seed_questions():
    if InterviewQuestion.query.first() is None:
        questions = [
            # Behavioral
            {"category": "Behavioral", "question_text": "Tell me about yourself and your background."},
            {"category": "Behavioral", "question_text": "Describe a difficult challenge you faced at work/school and how you overcame it."},
            {"category": "Behavioral", "question_text": "Why do you want to join our company, and what makes you a good fit?"},
            
            # Technical
            {"category": "Technical", "question_text": "What is the difference between a list and a tuple in Python, and when would you use each?"},
            {"category": "Technical", "question_text": "Can you explain what SQL joins are and describe the different types?"},
            {"category": "Technical", "question_text": "What is Docker, and why is it useful in software development?"},
            
            # Communication / General
            {"category": "General", "question_text": "Where do you see yourself in five years?"},
            {"category": "General", "question_text": "How do you handle disagreement within a team?"}
        ]
        for q in questions:
            db.session.add(InterviewQuestion(category=q["category"], question_text=q["question_text"]))
        db.session.commit()
        print("Questions seeded successfully.")

# Create database tables
with app.app_context():
    db.create_all()
    seed_questions()


# AUTH ENDPOINTS
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Please provide name, email and password."}), 400
        
    email = data.get('email').strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409
        
    new_user = User(name=data.get('name'), email=email)
    new_user.set_password(data.get('password'))
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "message": "User registered successfully.",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email
        }
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Please provide email and password."}), 400
        
    email = data.get('email').strip().lower()
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({"error": "Invalid email or password."}), 401
        
    # Return user details for frontend storage
    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }), 200


# QUESTIONS ENDPOINT
@app.route('/api/questions', methods=['GET'])
def get_questions():
    category = request.args.get('category')
    limit = request.args.get('limit', default=3, type=int)
    
    query = InterviewQuestion.query
    if category:
        query = query.filter_by(category=category)
        
    # Return a random sample or simple limit
    questions = query.order_by(db.func.random()).limit(limit).all()
    
    return jsonify([{
        "id": q.id,
        "category": q.category,
        "question_text": q.question_text
    } for q in questions]), 200


# INTERVIEW ANSWER ANALYSIS
@app.route('/api/analyze_answer', methods=['POST'])
def analyze_answer_endpoint():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400
        
    audio_file = request.files['audio']
    question_text = request.form.get('question_text', 'Tell me about yourself.')
    duration = float(request.form.get('duration', 10.0))
    eye_contact = int(request.form.get('eye_contact_ratio', 80))
    smile = int(request.form.get('smile_ratio', 50))
    
    if audio_file.filename == '':
        return jsonify({"error": "No selected audio file."}), 400
        
    # Save the audio file temporarily
    filename = f"{uuid.uuid4().hex}.wav"
    audio_path = os.path.join(AUDIO_FOLDER, filename)
    audio_file.save(audio_path)
    
    # 1. Transcribe the audio
    transcript = transcribe_audio(audio_path)
    
    # Clean up file after transcription if desired, or keep for records
    # For simplicity of analysis and debugging, we keep it in the uploads folder
    
    # 2. Analyze the answer
    analysis = analyze_answer(transcript, question_text, duration, eye_contact, smile)
    
    return jsonify(analysis), 200


# SAVE REPORT & ALL RESULTS
@app.route('/api/save_report', methods=['POST'])
def save_report():
    data = request.json
    if not data or not data.get('user_id') or not data.get('results'):
        return jsonify({"error": "Incomplete report data."}), 400
        
    user_id = data.get('user_id')
    results_list = data.get('results')
    
    # Aggregate average scores for the report
    total_q = len(results_list)
    if total_q == 0:
        return jsonify({"error": "No answers provided."}), 400
        
    avg_overall = int(sum(r['overall_score'] for r in results_list) / total_q)
    avg_grammar = int(sum(r['grammar_score'] for r in results_list) / total_q)
    avg_comm = int(sum(r['communication_score'] for r in results_list) / total_q)
    avg_tech = int(sum(r['technical_score'] for r in results_list) / total_q)
    avg_conf = int(sum(r['confidence_score'] for r in results_list) / total_q)
    avg_speed = int(sum(r['speed_score'] for r in results_list) / total_q)
    
    # Average non-verbal components
    avg_eye = int(sum(r.get('eye_contact_ratio', 80) for r in results_list) / total_q)
    avg_smile = int(sum(r.get('smile_ratio', 50) for r in results_list) / total_q)
    avg_non_verbal = (avg_eye + avg_smile) // 2
    
    # Generate generic strengths & improvements based on averages
    strengths = []
    improvements = []
    
    if avg_grammar >= 15:
        strengths.append("Demonstrated solid grammar and sentence structures.")
    else:
        improvements.append("Work on subject-verb agreements and general grammatical phrasing.")
        
    if avg_comm >= 15:
        strengths.append("Expressive communication with a high level of vocabulary diversity.")
    else:
        improvements.append("Try using more precise industry-specific terms and direct explanations.")
        
    if avg_tech >= 18:
        strengths.append("Strong technical knowledge, naturally referencing core stack and engineering practices.")
    else:
        improvements.append("Focus on integrating relevant keywords (e.g. databases, tools, workflows) in your descriptions.")
        
    if avg_conf >= 15:
        strengths.append("High confidence, maintaining good eye contact and speaking with minimal fillers.")
    else:
        improvements.append("Reduce filler words (like 'um', 'actually', 'basically') and look directly at the camera.")
        
    if avg_speed >= 12:
        strengths.append("Controlled speaking pace, comfortable to follow.")
    else:
        improvements.append("Adjust speaking speed to 110-150 words per minute for optimal audience comprehension.")

    new_report = Report(
        user_id=user_id,
        overall_score=avg_overall,
        grammar_score=avg_grammar,
        communication_score=avg_comm,
        technical_score=avg_tech,
        confidence_score=avg_conf,
        speed_score=avg_speed,
        non_verbal_score=avg_non_verbal,
        strengths="; ".join(strengths),
        improvements="; ".join(improvements)
    )
    
    db.session.add(new_report)
    db.session.flush() # Populate the report.id field
    
    # Store individual question results
    for r in results_list:
        res = InterviewResult(
            report_id=new_report.id,
            question_text=r['question_text'],
            answer_text=r['text'],
            overall_score=r['overall_score'],
            grammar_score=r['grammar_score'],
            communication_score=r['communication_score'],
            technical_score=r['technical_score'],
            confidence_score=r['confidence_score'],
            speed_score=r['speed_score'],
            wpm=r['wpm'],
            filler_words_count=r['filler_words_count'],
            sentiment=r['sentiment'],
            eye_contact_ratio=r.get('eye_contact_ratio', 80),
            smile_ratio=r.get('smile_ratio', 50),
            feedback_text=r.get('feedback_text', '')
        )
        db.session.add(res)
        
    db.session.commit()
    
    return jsonify({
        "message": "Report saved successfully.",
        "report_id": new_report.id
    }), 201


# GET REPORT
@app.route('/api/report/<int:report_id>', methods=['GET'])
def get_report_details(report_id):
    report = Report.query.get(report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404
        
    results = InterviewResult.query.filter_by(report_id=report_id).all()
    
    return jsonify({
        "id": report.id,
        "user_id": report.user_id,
        "date": report.date.isoformat(),
        "overall_score": report.overall_score,
        "grammar_score": report.grammar_score,
        "communication_score": report.communication_score,
        "technical_score": report.technical_score,
        "confidence_score": report.confidence_score,
        "speed_score": report.speed_score,
        "non_verbal_score": report.non_verbal_score,
        "strengths": report.strengths.split("; ") if report.strengths else [],
        "improvements": report.improvements.split("; ") if report.improvements else [],
        "answers": [{
            "id": r.id,
            "question_text": r.question_text,
            "answer_text": r.answer_text,
            "overall_score": r.overall_score,
            "grammar_score": r.grammar_score,
            "communication_score": r.communication_score,
            "technical_score": r.technical_score,
            "confidence_score": r.confidence_score,
            "speed_score": r.speed_score,
            "wpm": r.wpm,
            "filler_words_count": r.filler_words_count,
            "sentiment": r.sentiment,
            "eye_contact_ratio": r.eye_contact_ratio,
            "smile_ratio": r.smile_ratio,
            "feedback_text": r.feedback_text
        } for r in results]
    }), 200


# DASHBOARD STATS
@app.route('/api/dashboard/stats/<int:user_id>', methods=['GET'])
def get_dashboard_stats(user_id):
    reports = Report.query.filter_by(user_id=user_id).order_by(Report.date.desc()).all()
    
    if not reports:
        return jsonify({
            "total_interviews": 0,
            "average_score": 0,
            "history": []
        }), 200
        
    total_interviews = len(reports)
    avg_score = int(sum(r.overall_score for r in reports) / total_interviews)
    
    # Fetch details of past reports
    history = [{
        "id": r.id,
        "date": r.date.strftime("%Y-%m-%d %H:%M"),
        "overall_score": r.overall_score,
        "grammar_score": r.grammar_score,
        "communication_score": r.communication_score,
        "technical_score": r.technical_score,
        "confidence_score": r.confidence_score,
        "speed_score": r.speed_score,
        "non_verbal_score": r.non_verbal_score
    } for r in reports]
    
    # Calculate dimensional averages
    avg_grammar = int(sum(r.grammar_score for r in reports) / total_interviews)
    avg_comm = int(sum(r.communication_score for r in reports) / total_interviews)
    avg_tech = int(sum(r.technical_score for r in reports) / total_interviews)
    avg_conf = int(sum(r.confidence_score for r in reports) / total_interviews)
    avg_speed = int(sum(r.speed_score for r in reports) / total_interviews)
    avg_non_verbal = int(sum(r.non_verbal_score for r in reports) / total_interviews)
    
    return jsonify({
        "total_interviews": total_interviews,
        "average_score": avg_score,
        "averages": {
            "overall": avg_score,
            "grammar": avg_grammar,
            "communication": avg_comm,
            "technical": avg_tech,
            "confidence": avg_conf,
            "speed": avg_speed,
            "non_verbal": avg_non_verbal
        },
        "history": history
    }), 200


# RESUME ANALYZER ENDPOINT
@app.route('/api/resume/analyze', methods=['POST'])
def analyze_resume_endpoint():
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file uploaded."}), 400
        
    resume_file = request.files['resume']
    if resume_file.filename == '':
        return jsonify({"error": "No selected file."}), 400
        
    filename = f"{uuid.uuid4().hex}_{resume_file.filename}"
    resume_path = os.path.join(RESUME_FOLDER, filename)
    resume_file.save(resume_path)
    
    analysis_result = parse_resume(resume_path)
    
    # Optionally delete file after reading to save disk space
    try:
        os.remove(resume_path)
    except Exception:
        pass
        
    return jsonify(analysis_result), 200


# START THE FLASK SERVER
if __name__ == '__main__':
    app.run(debug=True, port=5000)
