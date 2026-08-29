import os
import sys

# Ensure backend folder is in Python import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Serving AI Smart Interview Analyzer Production App on http://0.0.0.0:{port}")
    serve(app, host="0.0.0.0", port=port)
