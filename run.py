import sys
from pathlib import Path

# Add backend directory to Python sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting PedalPulse Bike Rental server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
