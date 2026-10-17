from datetime import datetime, timezone
from flask import Blueprint, render_template, request, abort
from models import Bike, Booking
from forms import BookingForm

bikes_bp = Blueprint('bikes', __name__, url_prefix='/bikes')

@bikes_bp.route('/')
def bike_list():
    query_text = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', 'newest')

    query = Bike.query.filter_by(is_active=True)

    if query_text:
        search_pattern = f"%{query_text}%"
        query = query.filter(
            (Bike.name.ilike(search_pattern)) | 
            (Bike.model.ilike(search_pattern)) |
            (Bike.description.ilike(search_pattern))
        )

    if selected_category and selected_category.lower() != 'all':
        query = query.filter(Bike.category.ilike(selected_category))

    if max_price is not None and max_price > 0:
        query = query.filter(Bike.price_per_hour <= max_price)

    # Sorting
    if sort_by == 'price_asc':
        query = query.order_by(Bike.price_per_hour.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Bike.price_per_hour.desc())
    elif sort_by == 'name':
        query = query.order_by(Bike.name.asc())
    else: # newest
        query = query.order_by(Bike.created_at.desc())

    bikes = query.all()

    # Get distinct categories for filter buttons
    categories = ['Mountain', 'Road', 'Electric', 'City', 'Hybrid']

    return render_template(
        'bikes/list.html',
        bikes=bikes,
        categories=categories,
        selected_category=selected_category,
        query_text=query_text,
        max_price=max_price,
        sort_by=sort_by
    )

@bikes_bp.route('/<int:bike_id>')
def bike_detail(bike_id: int):
    bike = Bike.query.get_or_404(bike_id)

    # Check if currently rented at this very moment
    now = datetime.now(timezone.utc)
    current_active_booking = Booking.query.filter(
        Booking.bike_id == bike.id,
        Booking.status == Booking.STATUS_CONFIRMED,
        Booking.start_time <= now,
        Booking.end_time >= now
    ).first()

    booking_form = BookingForm()

    return render_template(
        'bikes/detail.html',
        bike=bike,
        is_rented_now=(current_active_booking is not None),
        booking_form=booking_form
    )
