import pytest
from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, User, Bike, Booking

@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for testing."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for making HTTP requests."""
    return app.test_client()

@pytest.fixture
def customer_user(app):
    """Create and return a sample customer user."""
    user = User(
        name="John Doe",
        email="john@example.com",
        role="customer"
    )
    user.set_password("Customer@123")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def second_customer_user(app):
    """Create and return a second customer user for IDOR testing."""
    user = User(
        name="Jane Smith",
        email="jane@example.com",
        role="customer"
    )
    user.set_password("Customer@456")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def admin_user(app):
    """Create and return a sample administrator user."""
    admin = User(
        name="Admin Chief",
        email="admin@example.com",
        role="admin"
    )
    admin.set_password("AdminSecure@123")
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def sample_bike(app):
    """Create and return an active sample bike."""
    bike = Bike(
        name="Trek FX 3 Disc",
        model="FX 3 Fitness 2024",
        category="Hybrid",
        description="High quality fitness hybrid bicycle with hydraulic disc brakes.",
        price_per_hour=10.00,
        image_url="https://example.com/bike.jpg",
        is_active=True
    )
    db.session.add(bike)
    db.session.commit()
    return bike
