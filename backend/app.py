import os
from datetime import datetime, timezone
import click
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / 'frontend'

# Ensure backend directory is in python search path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import config_by_name
from models import db, User, Bike, Booking

# Instantiate extensions
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name=None):
    """Application factory for the Bike Rental Management System."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / 'templates'),
        static_folder=str(FRONTEND_DIR / 'static')
    )
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.bikes import bikes_bp
    from routes.bookings import bookings_bp
    from routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bikes_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(admin_bp)

    # Global context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.now(timezone.utc),
            'app_name': 'PedalPulse Bike Rentals'
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    # Custom CLI Commands
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        with app.app_context():
            db.create_all()
            click.echo("[OK] Database tables created successfully.")

    @app.cli.command("seed-data")
    def seed_data_command():
        """Seed sample bikes and accounts into the database."""
        from scripts.seed_data import seed_database
        with app.app_context():
            seed_database()
            click.echo("[OK] Database seeded successfully with sample bikes and test accounts.")

    @app.cli.command("create-admin")
    @click.option('--name', prompt=True, default='Admin User', help="Admin display name")
    @click.option('--email', prompt=True, help="Admin email address")
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
    def create_admin_command(name, email, password):
        """Create a new administrator user."""
        from scripts.create_admin import create_admin_user
        with app.app_context():
            create_admin_user(name, email, password)

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting PedalPulse Bike Rental server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
