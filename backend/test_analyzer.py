import os
import sys

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db, User, InterviewQuestion
from analyzer import analyze_answer, check_grammar_and_vocab, detect_filler_words, parse_resume
from app import app

def run_tests():
    print("==================================================")
    print("      RUNNING INTEGRATED ANALYZER TESTS           ")
    print("==================================================")

    # 1. Test Text Analysis Metrics
    print("\n--- 1. Testing Text Analysis Logic ---")
    test_text = "I am a Java software engineer. Actually, I goes to work and write SQL queries. Basically, it is more better."
    
    fillers_count, fillers_breakdown = detect_filler_words(test_text)
    print(f"Detected {fillers_count} filler words: {fillers_breakdown}")
    assert fillers_count == 2, "Filler word count should be 2 ('actually', 'basically')"

    grammar_score, corrections, vocab_rating = check_grammar_and_vocab(test_text)
    print(f"Grammar Score: {grammar_score}/20")
    print(f"Vocabulary Diversity: {vocab_rating}")
    print(f"Grammar Corrections: {corrections}")
    assert len(corrections) > 0, "Should detect grammar errors ('goes', 'more better')"

    # 2. Test Complete Question Answer Analysis Scorer
    print("\n--- 2. Testing Answer Analysis Scoring Pipeline ---")
    analysis = analyze_answer(
        text=test_text,
        question_text="What is your background?",
        duration_seconds=30.0,
        eye_contact_ratio=80,
        smile_ratio=60
    )
    print(f"Overall Score: {analysis['overall_score']}/100")
    print(f"Sentiment: {analysis['sentiment']}")
    print(f"Speaking Pace (WPM): {analysis['wpm']}")
    print(f"Skills Found: {analysis['skills_found']}")
    print(f"Scores breakdown: Grammar={analysis['grammar_score']}, Comm={analysis['communication_score']}, Tech={analysis['technical_score']}, Conf={analysis['confidence_score']}, Speed={analysis['speed_score']}")
    
    # 3. Test Database Connection and Tables
    print("\n--- 3. Testing Flask App Database Seeding ---")
    with app.app_context():
        # Check seeded questions
        qs = InterviewQuestion.query.all()
        print(f"Seeded Questions Count: {len(qs)}")
        for q in qs[:3]:
            print(f" - [{q.category}] {q.question_text}")
            
        assert len(qs) > 0, "Questions should be automatically seeded in SQLite"
        
        # Test mock user operations
        test_email = "testuser@example.com"
        existing = User.query.filter_by(email=test_email).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            
        new_user = User(name="Test Candidate", email=test_email)
        new_user.set_password("securepassword123")
        db.session.add(new_user)
        db.session.commit()
        
        verify_user = User.query.filter_by(email=test_email).first()
        print(f"Registered Mock User: {verify_user.name} ({verify_user.email})")
        assert verify_user.check_password("securepassword123") is True, "Password hashing should match"
        
        db.session.delete(verify_user)
        db.session.commit()
        print("Mock User clean up verified.")

    print("\n==================================================")
    print("      ALL UNIT AND DATABASE TESTS PASSED!       ")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
