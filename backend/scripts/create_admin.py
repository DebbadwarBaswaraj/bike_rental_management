import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from models import db, User

def create_admin_user(name: str, email: str, password: str) -> User:
    email = email.lower().strip()
    user = User.query.filter_by(email=email).first()

    if user:
        user.name = name
        user.role = 'admin'
        user.set_password(password)
        print(f"Existing user '{email}' successfully updated to Administrator role.")
    else:
        user = User(
            name=name,
            email=email,
            role='admin'
        )
        user.set_password(password)
        db.session.add(user)
        print(f"New Administrator '{email}' successfully created.")

    db.session.commit()
    return user

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Read from environment variables or prompt
        admin_name = os.environ.get('ADMIN_NAME') or input("Enter Admin Name: ")
        admin_email = os.environ.get('ADMIN_EMAIL') or input("Enter Admin Email: ")
        admin_password = os.environ.get('ADMIN_PASSWORD') or input("Enter Admin Password: ")

        if not admin_email or not admin_password:
            print("Error: Email and password are required.")
            sys.exit(1)

        create_admin_user(admin_name, admin_email, admin_password)
