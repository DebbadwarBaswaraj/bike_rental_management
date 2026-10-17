from flask import Blueprint, render_template
from models import Bike, Booking, db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Featured bikes (up to 6 active bikes)
    featured_bikes = Bike.query.filter_by(is_active=True).limit(6).all()

    # High-level stats for landing page social proof
    total_bikes_count = Bike.query.filter_by(is_active=True).count()
    completed_rentals = Booking.query.filter_by(status=Booking.STATUS_COMPLETED).count()

    categories = [
        {'name': 'Mountain', 'icon': 'bi-tree', 'desc': 'Conquer rugged trails and off-road tracks with suspension.'},
        {'name': 'Road', 'icon': 'bi-speedometer2', 'desc': 'Lightweight aerodynamic frames engineered for pure speed.'},
        {'name': 'Electric', 'icon': 'bi-lightning-charge', 'desc': 'Effortless pedal assist for hills and long distance commutes.'},
        {'name': 'City', 'icon': 'bi-buildings', 'desc': 'Upright ergonomic posture for comfortable urban exploration.'},
        {'name': 'Hybrid', 'icon': 'bi-shuffle', 'desc': 'The versatile all-rounder for city streets and park trails.'}
    ]

    return render_template(
        'index.html',
        featured_bikes=featured_bikes,
        total_bikes=total_bikes_count,
        completed_rentals=completed_rentals,
        categories=categories
    )

@main_bp.route('/about')
def about():
    return render_template('about.html')
