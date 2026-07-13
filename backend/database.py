import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    reports = db.relationship('Report', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'Behavioral', 'Technical', 'General'
    question_text = db.Column(db.Text, nullable=False)


class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    overall_score = db.Column(db.Integer, nullable=False)
    grammar_score = db.Column(db.Integer, nullable=False)
    communication_score = db.Column(db.Integer, nullable=False)
    technical_score = db.Column(db.Integer, nullable=False)
    confidence_score = db.Column(db.Integer, nullable=False)
    speed_score = db.Column(db.Integer, nullable=False)
    non_verbal_score = db.Column(db.Integer, nullable=False)
    
    strengths = db.Column(db.Text, nullable=True)        # JSON or text containing key strengths
    improvements = db.Column(db.Text, nullable=True)     # JSON or text containing suggestions
    
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    results = db.relationship('InterviewResult', backref='report', lazy=True, cascade="all, delete-orphan")


class InterviewResult(db.Model):
    __tablename__ = 'interview_results'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    
    # Scores for this specific question
    overall_score = db.Column(db.Integer, nullable=False)
    grammar_score = db.Column(db.Integer, nullable=False)
    communication_score = db.Column(db.Integer, nullable=False)
    technical_score = db.Column(db.Integer, nullable=False)
    confidence_score = db.Column(db.Integer, nullable=False)
    speed_score = db.Column(db.Integer, nullable=False)
    
    # NLP and behavioral metrics
    wpm = db.Column(db.Integer, nullable=False)
    filler_words_count = db.Column(db.Integer, nullable=False)
    sentiment = db.Column(db.String(20), nullable=False)  # 'Positive', 'Neutral', 'Negative'
    eye_contact_ratio = db.Column(db.Integer, nullable=False) # Percentage (0-100)
    smile_ratio = db.Column(db.Integer, nullable=False)       # Percentage (0-100)
    
    feedback_text = db.Column(db.Text, nullable=True)
