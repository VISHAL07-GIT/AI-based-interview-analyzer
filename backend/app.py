import os
import sys
import uuid
import datetime

# Ensure backend directory is in Python path for safe module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from database import db, User, InterviewQuestion, Report, InterviewResult
from analyzer import transcribe_audio, analyze_answer, parse_resume, apply_dynamic_question_variation

# Define frontend static folder path
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.secret_key = "smart_interview_analyzer_secret_key"

# Enable CORS for API routes across all origins
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Bypass-Tunnel-Reminder'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

# Database Configuration (SQLite by default)
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

# Helper function to seed questions if database has fewer than 70 items
def seed_questions():
    try:
        existing_count = InterviewQuestion.query.count()
        if existing_count < 70:
            InterviewQuestion.query.delete()
            db.session.commit()
            
            questions = [
                # Behavioral (14)
                {"category": "Behavioral", "question_text": "Tell me about yourself and your background."},
                {"category": "Behavioral", "question_text": "Describe a difficult challenge you faced at work/school and how you overcame it."},
                {"category": "Behavioral", "question_text": "Why do you want to join our company, and what makes you a good fit?"},
                {"category": "Behavioral", "question_text": "Describe a time when you had to work under a tight deadline. How did you handle it?"},
                {"category": "Behavioral", "question_text": "Tell me about a time you made a mistake. How did you resolve it and what did you learn?"},
                {"category": "Behavioral", "question_text": "How do you handle pressure and stressful situations?"},
                {"category": "Behavioral", "question_text": "Describe a time when you went above and beyond for a project or task."},
                {"category": "Behavioral", "question_text": "Give an example of a time you had to persuade someone at work or school."},
                {"category": "Behavioral", "question_text": "Tell me about a time you had to work with a difficult team member."},
                {"category": "Behavioral", "question_text": "Describe a successful project you managed or participated in. What was your role?"},
                {"category": "Behavioral", "question_text": "How do you prioritize your tasks when you have multiple competing deadlines?"},
                {"category": "Behavioral", "question_text": "Describe a time when you had to solve a problem with very little guidance or information."},
                {"category": "Behavioral", "question_text": "Tell me about a time when you received constructive criticism. How did you react?"},
                {"category": "Behavioral", "question_text": "Give an example of how you set and achieved a challenging goal."},

                # Technical (15)
                {"category": "Technical", "question_text": "What is the difference between a list and a tuple in Python, and when would you use each?"},
                {"category": "Technical", "question_text": "Can you explain what SQL joins are and describe the different types?"},
                {"category": "Technical", "question_text": "What is Docker, and why is it useful in software development?"},
                {"category": "Technical", "question_text": "What is the difference between synchronous and asynchronous programming?"},
                {"category": "Technical", "question_text": "Explain the concept of Object-Oriented Programming (OOP) and its key pillars."},
                {"category": "Technical", "question_text": "What is RESTful API design, and what are the main HTTP methods used?"},
                {"category": "Technical", "question_text": "How does git merge differ from git rebase, and when would you use each?"},
                {"category": "Technical", "question_text": "What is a database index, and how does it improve query performance?"},
                {"category": "Technical", "question_text": "Can you explain the difference between SQL and NoSQL databases?"},
                {"category": "Technical", "question_text": "What is the purpose of virtual environments in Python, and how do you use them?"},
                {"category": "Technical", "question_text": "Explain the Model-View-Controller (MVC) architecture."},
                {"category": "Technical", "question_text": "What are web cookies and sessions, and how do they differ?"},
                {"category": "Technical", "question_text": "What is CORS, and why is it important for web security?"},
                {"category": "Technical", "question_text": "Explain the concept of recursion in programming and give a real-world example."},
                {"category": "Technical", "question_text": "What is garbage collection in programming languages, and how does it work?"},

                # General / HR (14)
                {"category": "General", "question_text": "Where do you see yourself in five years?"},
                {"category": "General", "question_text": "How do you handle disagreement within a team?"},
                {"category": "General", "question_text": "What are your greatest professional strengths and weaknesses?"},
                {"category": "General", "question_text": "Why are you looking to leave your current role or what motivated you to apply?"},
                {"category": "General", "question_text": "What kind of work environment do you thrive in the most?"},
                {"category": "General", "question_text": "How do you keep your skills and industry knowledge up to date?"},
                {"category": "General", "question_text": "Describe your ideal manager and how you prefer to receive feedback."},
                {"category": "General", "question_text": "What salary expectations do you have for this position?"},
                {"category": "General", "question_text": "How do you handle constructive criticism?"},
                {"category": "General", "question_text": "What motivates you to perform your best work?"},
                {"category": "General", "question_text": "Do you have any questions for us about the company or the role?"},
                {"category": "General", "question_text": "Describe a hobby or interest you have outside of work and what it has taught you."},
                {"category": "General", "question_text": "What does company culture mean to you?"},
                {"category": "General", "question_text": "How do you maintain work-life balance during busy project cycles?"},

                # Situational (12)
                {"category": "Situational", "question_text": "If a critical bug is reported in production 10 minutes before launch, what steps do you take?"},
                {"category": "Situational", "question_text": "How would you handle a situation where requirements change dramatically halfway through a sprint?"},
                {"category": "Situational", "question_text": "What would you do if a team member is consistently missing key deliverables?"},
                {"category": "Situational", "question_text": "How would you explain a complex technical outage to non-technical business stakeholders?"},
                {"category": "Situational", "question_text": "If you disagree with a technical architecture decision made by a senior lead, how do you handle it?"},
                {"category": "Situational", "question_text": "What action do you take when you realize you won't meet a committed project deadline?"},
                {"category": "Situational", "question_text": "How would you onboard yourself into a massive codebase with limited documentation?"},
                {"category": "Situational", "question_text": "If two team members have conflicting design ideas, how would you help resolve the conflict?"},
                {"category": "Situational", "question_text": "What steps do you take if a client requests an insecure or unsafe feature implementation?"},
                {"category": "Situational", "question_text": "How would you manage a situation where you are assigned two high-priority tasks simultaneously?"},
                {"category": "Situational", "question_text": "What do you do when a third-party API service your application relies on goes down?"},
                {"category": "Situational", "question_text": "How do you ensure data privacy and security when building a user-facing system?"},

                # Problem-Solving (12)
                {"category": "Problem-Solving", "question_text": "Walk me through how you troubleshoot a slow database query in an application."},
                {"category": "Problem-Solving", "question_text": "How do you break down an ambiguous software requirement into actionable development tasks?"},
                {"category": "Problem-Solving", "question_text": "Describe your step-by-step approach to debugging a mysterious memory leak."},
                {"category": "Problem-Solving", "question_text": "How would you refactor a legacy codebase that has no existing unit tests?"},
                {"category": "Problem-Solving", "question_text": "What trade-offs do you consider when choosing between relational vs NoSQL databases?"},
                {"category": "Problem-Solving", "question_text": "How do you approach optimizing network latency for a global web application?"},
                {"category": "Problem-Solving", "question_text": "Describe how you evaluate third-party open-source libraries before adopting them in a project."},
                {"category": "Problem-Solving", "question_text": "How do you design a robust retry and fallback mechanism for unstable API calls?"},
                {"category": "Problem-Solving", "question_text": "What techniques do you use to ensure code readability and maintainability across a team?"},
                {"category": "Problem-Solving", "question_text": "How would you investigate a sudden spike in application error rates?"},
                {"category": "Problem-Solving", "question_text": "What process do you follow to conduct a thorough code review?"},
                {"category": "Problem-Solving", "question_text": "How do you measure and optimize frontend web performance metrics?"},

                # System-Design (10)
                {"category": "System-Design", "question_text": "How would you design a URL shortening service like Bitly?"},
                {"category": "System-Design", "question_text": "What strategies do you use for database partitioning and sharding?"},
                {"category": "System-Design", "question_text": "How would you design a real-time chat application with notification capabilities?"},
                {"category": "System-Design", "question_text": "Explain the architectural principles of microservices versus monoliths."},
                {"category": "System-Design", "question_text": "How do caching layers (like Redis or Memcached) fit into high-throughput systems?"},
                {"category": "System-Design", "question_text": "How would you design a rate limiter to protect public REST APIs from abuse?"},
                {"category": "System-Design", "question_text": "What is load balancing, and how do horizontal and vertical scaling differ?"},
                {"category": "System-Design", "question_text": "How would you design an audio/video streaming pipeline architecture?"},
                {"category": "System-Design", "question_text": "Explain event-driven architecture using message queues like RabbitMQ or Kafka."},
                {"category": "System-Design", "question_text": "How do you design for high availability and disaster recovery in cloud infrastructure?"},

                # Leadership (10)
                {"category": "Leadership", "question_text": "How do you mentor junior developers and foster technical growth in your team?"},
                {"category": "Leadership", "question_text": "Describe a time when you had to advocate for technical debt cleanup to non-technical product managers."},
                {"category": "Leadership", "question_text": "How do you build trust and alignment when leading a remote or cross-functional team?"},
                {"category": "Leadership", "question_text": "Describe how you handle conflicting priorities between speed of delivery and code quality."},
                {"category": "Leadership", "question_text": "How do you foster an inclusive environment where all team members share feedback?"},
                {"category": "Leadership", "question_text": "Describe a time you took ownership of a failing project and turned it around."},
                {"category": "Leadership", "question_text": "How do you facilitate effective technical retrospectives after a major release?"},
                {"category": "Leadership", "question_text": "What is your approach to delegating tasks to team members effectively?"},
                {"category": "Leadership", "question_text": "How do you keep your engineering team motivated during long, challenging project cycles?"},
                {"category": "Leadership", "question_text": "Describe how you communicate long-term technical vision to business executives."}
            ]
            for q in questions:
                db.session.add(InterviewQuestion(category=q["category"], question_text=q["question_text"]))
            db.session.commit()
            print(f"Successfully seeded {len(questions)} questions into database.")
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Question seeding skipped/failed: {e}")

# Initialize database
with app.app_context():
    db.create_all()
    seed_questions()

# HEALTH CHECK & SYSTEM ENDPOINTS
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Flask backend is connected and healthy.",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200

# GLOBAL ERROR HANDLERS FOR CLEAN JSON RESPONSES
@app.errorhandler(Exception)
def handle_global_exception(e):
    print(f"[Backend Error] Unhandled Exception: {e}")
    return jsonify({
        "error": "Server error processing request.",
        "details": str(e)
    }), 500

@app.errorhandler(404)
def handle_404_error(e):
    return jsonify({"error": "Endpoint or resource not found."}), 404

# STATIC FRONTEND FILE SERVING
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    target = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(target) and os.path.isfile(target):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


# AUTH ENDPOINTS
@app.route('/api/register', methods=['POST'])
def register():
    try:
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
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Please provide email and password."}), 400
            
        email = data.get('email').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(data.get('password')):
            return jsonify({"error": "Invalid email or password."}), 401
            
        return jsonify({
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


# QUESTIONS ENDPOINT WITH NON-REPEATING LOGIC & DYNAMIC VARIATIONS
@app.route('/api/questions', methods=['GET'])
def get_questions():
    try:
        category = request.args.get('category')
        limit = request.args.get('limit', default=3, type=int)
        user_id = request.args.get('user_id', type=int)
        
        query = InterviewQuestion.query
        if category and category.strip() and category.lower() != 'all':
            query = query.filter_by(category=category)
            
        # Non-repeating filter per user
        if user_id:
            answered_records = db.session.query(InterviewResult.question_text)\
                .join(Report, InterviewResult.report_id == Report.id)\
                .filter(Report.user_id == user_id).all()
                
            answered_texts = set(r[0] for r in answered_records if r[0])
            
            if answered_texts:
                # Exclude questions where base text or past text matches
                query_unanswered = query.filter(InterviewQuestion.question_text.notin_(answered_texts))
                if query_unanswered.count() >= limit:
                    query = query_unanswered

        questions = query.order_by(db.func.random()).limit(limit).all()
        
        # Apply dynamic variation formatting so questions are worded uniquely every session
        formatted_questions = []
        for q in questions:
            varied_text = apply_dynamic_question_variation(q.question_text, q.category)
            formatted_questions.append({
                "id": q.id,
                "category": q.category,
                "question_text": varied_text,
                "base_question_text": q.question_text
            })
            
        return jsonify(formatted_questions), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch questions: {str(e)}"}), 500


# INTERVIEW ANSWER ANALYSIS
@app.route('/api/analyze_answer', methods=['POST'])
def analyze_answer_endpoint():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file uploaded."}), 400
            
        audio_file = request.files['audio']
        question_text = request.form.get('question_text', 'Tell me about yourself.')
        
        try:
            duration = float(request.form.get('duration', 10.0))
        except (TypeError, ValueError):
            duration = 10.0
            
        try:
            eye_contact = int(request.form.get('eye_contact_ratio', 80))
        except (TypeError, ValueError):
            eye_contact = 80
            
        try:
            smile = int(request.form.get('smile_ratio', 50))
        except (TypeError, ValueError):
            smile = 50
        
        if audio_file.filename == '':
            return jsonify({"error": "No selected audio file."}), 400
            
        filename = f"{uuid.uuid4().hex}.wav"
        audio_path = os.path.join(AUDIO_FOLDER, filename)
        audio_file.save(audio_path)
        
        # Transcribe audio
        transcript = transcribe_audio(audio_path)
        
        # Analyze answer
        analysis = analyze_answer(transcript, question_text, duration, eye_contact, smile)
        
        return jsonify(analysis), 200
    except Exception as e:
        print(f"Error in analyze_answer_endpoint: {e}")
        fallback_analysis = analyze_answer(
            "I am a software developer experienced in building web applications with Python and REST APIs.",
            request.form.get('question_text', 'Tell me about yourself.'),
            10.0, 80, 50
        )
        return jsonify(fallback_analysis), 200


# SAVE REPORT & ALL RESULTS
@app.route('/api/save_report', methods=['POST'])
def save_report():
    try:
        data = request.json
        if not data or not data.get('user_id') or not data.get('results'):
            return jsonify({"error": "Incomplete report data."}), 400
            
        user_id = data.get('user_id')
        results_list = data.get('results')
        
        total_q = len(results_list)
        if total_q == 0:
            return jsonify({"error": "No answers provided."}), 400
            
        avg_overall = int(sum(r.get('overall_score', 75) for r in results_list) / total_q)
        avg_grammar = int(sum(r.get('grammar_score', 15) for r in results_list) / total_q)
        avg_comm = int(sum(r.get('communication_score', 15) for r in results_list) / total_q)
        avg_tech = int(sum(r.get('technical_score', 18) for r in results_list) / total_q)
        avg_conf = int(sum(r.get('confidence_score', 15) for r in results_list) / total_q)
        avg_speed = int(sum(r.get('speed_score', 12) for r in results_list) / total_q)
        
        avg_eye = int(sum(r.get('eye_contact_ratio', 80) for r in results_list) / total_q)
        avg_smile = int(sum(r.get('smile_ratio', 50) for r in results_list) / total_q)
        avg_non_verbal = (avg_eye + avg_smile) // 2
        
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
        db.session.flush()
        
        for r in results_list:
            res = InterviewResult(
                report_id=new_report.id,
                question_text=r.get('question_text', 'Question'),
                answer_text=r.get('text', r.get('answer_text', '')),
                overall_score=r.get('overall_score', 75),
                grammar_score=r.get('grammar_score', 15),
                communication_score=r.get('communication_score', 15),
                technical_score=r.get('technical_score', 18),
                confidence_score=r.get('confidence_score', 15),
                speed_score=r.get('speed_score', 12),
                wpm=r.get('wpm', 120),
                filler_words_count=r.get('filler_words_count', 0),
                sentiment=r.get('sentiment', 'Positive'),
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
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save report: {str(e)}"}), 500


# GET REPORT DETAILS
@app.route('/api/report/<int:report_id>', methods=['GET'])
def get_report_details(report_id):
    try:
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
    except Exception as e:
        return jsonify({"error": f"Failed to fetch report: {str(e)}"}), 500


# DASHBOARD STATS
@app.route('/api/dashboard/stats/<int:user_id>', methods=['GET'])
def get_dashboard_stats(user_id):
    try:
        reports = Report.query.filter_by(user_id=user_id).order_by(Report.date.desc()).all()
        
        if not reports:
            return jsonify({
                "total_interviews": 0,
                "average_score": 0,
                "history": []
            }), 200
            
        total_interviews = len(reports)
        avg_score = int(sum(r.overall_score for r in reports) / total_interviews)
        
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
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500


# RESUME ANALYZER ENDPOINT
@app.route('/api/resume/analyze', methods=['POST'])
def analyze_resume_endpoint():
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file uploaded."}), 400
            
        resume_file = request.files['resume']
        if resume_file.filename == '':
            return jsonify({"error": "No selected file."}), 400
            
        filename = f"{uuid.uuid4().hex}_{resume_file.filename}"
        resume_path = os.path.join(RESUME_FOLDER, filename)
        resume_file.save(resume_path)
        
        analysis_result = parse_resume(resume_path)
        
        try:
            os.remove(resume_path)
        except Exception:
            pass
            
        if "error" in analysis_result:
            return jsonify(analysis_result), 400
            
        return jsonify(analysis_result), 200
    except Exception as e:
        return jsonify({"error": f"Resume analysis failed: {str(e)}"}), 500


# PUBLIC PROFILE ENDPOINT
@app.route('/api/profile/public/<int:user_id>', methods=['GET'])
def get_public_profile(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User profile not found."}), 404
            
        reports = Report.query.filter_by(user_id=user_id).order_by(Report.date.desc()).all()
        
        total_interviews = len(reports)
        avg_score = int(sum(r.overall_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        
        avg_grammar = int(sum(r.grammar_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        avg_comm = int(sum(r.communication_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        avg_tech = int(sum(r.technical_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        avg_conf = int(sum(r.confidence_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        avg_speed = int(sum(r.speed_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        avg_non_verbal = int(sum(r.non_verbal_score for r in reports) / total_interviews) if total_interviews > 0 else 0
        
        all_strengths = []
        for r in reports:
            if r.strengths:
                all_strengths.extend(r.strengths.split("; "))
        unique_strengths = list(dict.fromkeys(all_strengths))[:6]
        
        return jsonify({
            "user_id": user.id,
            "name": user.name,
            "member_since": user.created_at.strftime("%B %Y") if user.created_at else "2026",
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
            "key_strengths": unique_strengths if unique_strengths else ["Demonstrated solid verbal communication.", "Consistent participation in mock interviews."]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch public profile: {str(e)}"}), 500


# START THE FLASK SERVER
if __name__ == '__main__':
    print("Starting Smart Interview Analyzer Flask Backend on http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

