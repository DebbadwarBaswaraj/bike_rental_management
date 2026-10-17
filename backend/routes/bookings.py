from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import Bike, Booking, db
from forms import BookingForm
from services.booking_service import (
    create_booking,
    cancel_booking,
    calculate_rental_price,
    validate_booking_dates,
    is_bike_available,
    BookingError
)

bookings_bp = Blueprint('bookings', __name__, url_prefix='/bookings')

@bookings_bp.route('/new/<int:bike_id>', methods=['POST'])
@login_required
def create(bike_id: int):
    bike = Bike.query.get_or_404(bike_id)
    form = BookingForm()

    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data

        try:
            booking = create_booking(
                user_id=current_user.id,
                bike_id=bike.id,
                start_time=start_time,
                end_time=end_time
            )
            flash(f"Reservation confirmed! Bike '{bike.name}' reserved successfully.", "success")
            return redirect(url_for('bookings.confirmation', booking_id=booking.id))
        except BookingError as e:
            flash(str(e), "danger")
            return redirect(url_for('bikes.bike_detail', bike_id=bike.id))
        except Exception as e:
            flash("An unexpected error occurred while processing your booking. Please try again.", "danger")
            return redirect(url_for('bikes.bike_detail', bike_id=bike.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field.replace('_', ' ').capitalize()}: {error}", "warning")
        return redirect(url_for('bikes.bike_detail', bike_id=bike.id))

@bookings_bp.route('/confirmation/<int:booking_id>')
@login_required
def confirmation(booking_id: int):
    booking = Booking.query.get_or_404(booking_id)

    # Prevent IDOR: Only booking owner or admin can view
    if booking.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template('bookings/confirmation.html', booking=booking)

@bookings_bp.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id)\
                            .order_by(Booking.created_at.desc())\
                            .all()
    return render_template('bookings/my_bookings.html', bookings=bookings)

@bookings_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel(booking_id: int):
    try:
        booking = cancel_booking(
            booking_id=booking_id,
            current_user_id=current_user.id,
            is_admin=current_user.is_admin
        )
        flash(f"Booking #{booking.id} has been successfully cancelled.", "info")
    except BookingError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Could not cancel booking due to an unexpected error.", "danger")

    return redirect(url_for('bookings.my_bookings'))

@bookings_bp.route('/api/quote', methods=['POST'])
def quote():
    """Live quote calculation endpoint for frontend interactive booking preview."""
    data = request.get_json() or {}
    bike_id = data.get('bike_id')
    start_str = data.get('start_time')
    end_str = data.get('end_time')

    if not bike_id or not start_str or not end_str:
        return jsonify({'valid': False, 'error': 'Missing parameters'}), 400

    bike = db.session.get(Bike, bike_id)
    if not bike or not bike.is_active:
        return jsonify({'valid': False, 'error': 'Bike not available'}), 404

    try:
        start_time = datetime.fromisoformat(start_str)
        end_time = datetime.fromisoformat(end_str)

        validate_booking_dates(start_time, end_time)

        available = is_bike_available(bike.id, start_time, end_time)
        if not available:
            return jsonify({
                'valid': False,
                'conflict': True,
                'error': 'This bike is already booked during these dates/times.'
            })

        duration_hours, total_amount = calculate_rental_price(bike.price_per_hour, start_time, end_time)

        return jsonify({
            'valid': True,
            'conflict': False,
            'duration_hours': duration_hours,
            'price_per_hour': bike.price_per_hour,
            'total_amount': total_amount
        })
    except BookingError as e:
        return jsonify({'valid': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'valid': False, 'error': 'Invalid date format'}), 400
