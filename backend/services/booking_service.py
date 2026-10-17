from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from models import db, Bike, Booking, User

MINIMUM_HOURS = 1.0
MAXIMUM_DAYS = 7.0

class BookingError(Exception):
    """Custom exception for booking validation and domain errors."""
    pass

def validate_booking_dates(start_time: datetime, end_time: datetime) -> None:
    """
    Validate reservation timestamps.
    Raises BookingError if rules are violated.
    """
    now = datetime.now(timezone.utc)

    # Ensure UTC-aware or naive normalized to UTC
    if start_time.tzinfo is None:
        start_time_utc = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time_utc = start_time.astimezone(timezone.utc)

    if end_time.tzinfo is None:
        end_time_utc = end_time.replace(tzinfo=timezone.utc)
    else:
        end_time_utc = end_time.astimezone(timezone.utc)

    # Allow 2 minutes grace period for network submission lag
    if start_time_utc < (now - timedelta(minutes=2)):
        raise BookingError("Start time cannot be in the past.")

    if end_time_utc <= start_time_utc:
        raise BookingError("End time must be strictly after the start time.")

    duration_hours = (end_time_utc - start_time_utc).total_seconds() / 3600.0

    if duration_hours < MINIMUM_HOURS:
        raise BookingError(f"Minimum rental duration is {int(MINIMUM_HOURS)} hour(s).")

    if duration_hours > (MAXIMUM_DAYS * 24):
        raise BookingError(f"Maximum rental duration is {int(MAXIMUM_DAYS)} days.")

def calculate_rental_price(price_per_hour: float, start_time: datetime, end_time: datetime) -> Tuple[float, float]:
    """
    Calculate duration in hours and total rental price.
    Returns: (duration_hours, total_amount)
    """
    delta_seconds = (end_time - start_time).total_seconds()
    duration_hours = round(delta_seconds / 3600.0, 2)
    total_amount = round(duration_hours * price_per_hour, 2)
    return duration_hours, total_amount

def is_bike_available(bike_id: int, start_time: datetime, end_time: datetime, exclude_booking_id: Optional[int] = None) -> bool:
    """
    Determine if a bike is free of conflicting confirmed or pending reservations.
    Overlapping interval logic:
    Existing booking conflicts if:
        existing.start_time < requested.end_time AND existing.end_time > requested.start_time
    """
    query = Booking.query.filter(
        Booking.bike_id == bike_id,
        Booking.status.in_([Booking.STATUS_CONFIRMED, Booking.STATUS_PENDING]),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    )

    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    conflict = query.first()
    return conflict is None

def create_booking(user_id: int, bike_id: int, start_time: datetime, end_time: datetime) -> Booking:
    """
    Atomically validate and reserve a bike for a customer.
    """
    # 1. Validate dates
    validate_booking_dates(start_time, end_time)

    # 2. Verify bike existence and active status
    bike = db.session.get(Bike, bike_id)
    if not bike:
        raise BookingError("Bike does not exist.")
    if not bike.is_active:
        raise BookingError("This bike is currently inactive or under maintenance.")

    # 3. Check availability to prevent double-booking
    if not is_bike_available(bike_id, start_time, end_time):
        raise BookingError("Sorry, this bike is already booked during the selected time period. Please select different dates.")

    # 4. Calculate total amount
    _, total_amount = calculate_rental_price(bike.price_per_hour, start_time, end_time)

    # 5. Persist booking
    booking = Booking(
        user_id=user_id,
        bike_id=bike_id,
        start_time=start_time,
        end_time=end_time,
        total_amount=total_amount,
        status=Booking.STATUS_CONFIRMED
    )

    db.session.add(booking)
    db.session.commit()
    return booking

def cancel_booking(booking_id: int, current_user_id: int, is_admin: bool = False) -> Booking:
    """
    Cancel an existing reservation with authorization and cancellation window checks.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise BookingError("Booking not found.")

    # Prevent IDOR: Only the owner or an admin can cancel
    if not is_admin and booking.user_id != current_user_id:
        raise BookingError("Unauthorized: You cannot modify another customer's booking.")

    if not booking.can_be_cancelled:
        if booking.status in [Booking.STATUS_CANCELLED, Booking.STATUS_COMPLETED]:
            raise BookingError(f"Cannot cancel a booking that is already {booking.status}.")
        else:
            raise BookingError("Cannot cancel a booking that has already started or completed.")

    booking.status = Booking.STATUS_CANCELLED
    db.session.commit()
    return booking

def update_booking_status(booking_id: int, new_status: str) -> Booking:
    """
    Admin-only status transition updater.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise BookingError("Booking not found.")

    if new_status not in Booking.VALID_STATUSES:
        raise BookingError(f"Invalid status: {new_status}")

    # Check valid transitions
    current = booking.status
    if current == new_status:
        return booking

    if current == Booking.STATUS_CANCELLED:
        raise BookingError("Cannot change status of an already cancelled booking.")

    booking.status = new_status
    db.session.commit()
    return booking
