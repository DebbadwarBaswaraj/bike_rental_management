from datetime import datetime, timezone, timedelta
import pytest
from models import db, Booking
from services.booking_service import (
    create_booking,
    cancel_booking,
    calculate_rental_price,
    validate_booking_dates,
    is_bike_available,
    BookingError
)

def test_price_calculation():
    start = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 1, 13, 30, tzinfo=timezone.utc) # 3.5 hours
    hourly_rate = 12.00

    duration_hours, total_amount = calculate_rental_price(hourly_rate, start, end)
    assert duration_hours == 3.5
    assert total_amount == 42.00

def test_successful_booking_creation(client, customer_user, sample_bike):
    # Log in customer
    client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    })

    future_start = datetime.now(timezone.utc) + timedelta(days=2, hours=1)
    future_end = future_start + timedelta(hours=3)

    response = client.post(f'/bookings/new/{sample_bike.id}', data={
        'start_time': future_start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': future_end.strftime('%Y-%m-%dT%H:%M')
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Reservation confirmed" in response.data

    booking = Booking.query.filter_by(user_id=customer_user.id, bike_id=sample_bike.id).first()
    assert booking is not None
    assert booking.status == Booking.STATUS_CONFIRMED
    assert booking.total_amount == 30.00 # 3 hrs * $10.00

def test_invalid_booking_end_before_start(client, customer_user, sample_bike):
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    start = datetime.now(timezone.utc) + timedelta(days=1, hours=5)
    end = start - timedelta(hours=2) # End is BEFORE start

    response = client.post(f'/bookings/new/{sample_bike.id}', data={
        'start_time': start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end.strftime('%Y-%m-%dT%H:%M')
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"End time must be after start time" in response.data or b"strictly after" in response.data

def test_invalid_booking_duration_too_short(client, customer_user, sample_bike):
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    start = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    end = start + timedelta(minutes=15) # Only 15 minutes, below 1 hour minimum

    response = client.post(f'/bookings/new/{sample_bike.id}', data={
        'start_time': start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end.strftime('%Y-%m-%dT%H:%M')
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Minimum rental duration is 1 hour" in response.data

def test_invalid_booking_start_in_past(client, customer_user, sample_bike):
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    past_start = datetime.now(timezone.utc) - timedelta(hours=5)
    past_end = datetime.now(timezone.utc) + timedelta(hours=2)

    response = client.post(f'/bookings/new/{sample_bike.id}', data={
        'start_time': past_start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': past_end.strftime('%Y-%m-%dT%H:%M')
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Start time cannot be in the past" in response.data

def test_booking_conflict_overlapping_intervals(customer_user, sample_bike):
    base_time = datetime.now(timezone.utc) + timedelta(days=3)
    existing_start = base_time + timedelta(hours=2)
    existing_end = base_time + timedelta(hours=6)

    # Create initial confirmed booking (2 PM to 6 PM)
    booking1 = create_booking(customer_user.id, sample_bike.id, existing_start, existing_end)
    assert booking1 is not None

    # Test 1: Conflict starting during existing booking (3 PM to 7 PM)
    overlap_start = base_time + timedelta(hours=3)
    overlap_end = base_time + timedelta(hours=7)
    with pytest.raises(BookingError) as exc_info:
        create_booking(customer_user.id, sample_bike.id, overlap_start, overlap_end)
    assert "already booked" in str(exc_info.value)

    # Test 2: Conflict ending during existing booking (1 PM to 4 PM)
    overlap_start2 = base_time + timedelta(hours=1)
    overlap_end2 = base_time + timedelta(hours=4)
    with pytest.raises(BookingError) as exc_info:
        create_booking(customer_user.id, sample_bike.id, overlap_start2, overlap_end2)
    assert "already booked" in str(exc_info.value)

    # Test 3: Conflict fully enclosing existing booking (1 PM to 7 PM)
    overlap_start3 = base_time + timedelta(hours=1)
    overlap_end3 = base_time + timedelta(hours=7)
    with pytest.raises(BookingError) as exc_info:
        create_booking(customer_user.id, sample_bike.id, overlap_start3, overlap_end3)
    assert "already booked" in str(exc_info.value)

    # Test 4: Conflict strictly inside existing booking (3 PM to 5 PM)
    overlap_start4 = base_time + timedelta(hours=3)
    overlap_end4 = base_time + timedelta(hours=5)
    with pytest.raises(BookingError) as exc_info:
        create_booking(customer_user.id, sample_bike.id, overlap_start4, overlap_end4)
    assert "already booked" in str(exc_info.value)

    # Test 5: NON-overlapping interval should succeed (e.g. 7 PM to 9 PM)
    non_overlap_start = base_time + timedelta(hours=7)
    non_overlap_end = base_time + timedelta(hours=9)
    booking2 = create_booking(customer_user.id, sample_bike.id, non_overlap_start, non_overlap_end)
    assert booking2 is not None
    assert booking2.id != booking1.id

def test_booking_cancellation_success(customer_user, sample_bike):
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)

    booking = create_booking(customer_user.id, sample_bike.id, start, end)
    assert booking.status == Booking.STATUS_CONFIRMED

    cancelled_booking = cancel_booking(booking.id, customer_user.id)
    assert cancelled_booking.status == Booking.STATUS_CANCELLED

    # After cancellation, the slot should be available again for another reservation!
    assert is_bike_available(sample_bike.id, start, end) is True

def test_booking_cancellation_already_cancelled_raises(customer_user, sample_bike):
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)

    booking = create_booking(customer_user.id, sample_bike.id, start, end)
    cancel_booking(booking.id, customer_user.id)

    with pytest.raises(BookingError) as exc_info:
        cancel_booking(booking.id, customer_user.id)
    assert "already cancelled" in str(exc_info.value)

def test_customer_cannot_cancel_past_booking(customer_user, sample_bike):
    # Past booking directly created in DB
    past_start = datetime.now(timezone.utc) - timedelta(days=1, hours=4)
    past_end = datetime.now(timezone.utc) - timedelta(days=1, hours=2)

    booking = Booking(
        user_id=customer_user.id,
        bike_id=sample_bike.id,
        start_time=past_start,
        end_time=past_end,
        total_amount=20.0,
        status=Booking.STATUS_CONFIRMED
    )
    db.session.add(booking)
    db.session.commit()

    with pytest.raises(BookingError) as exc_info:
        cancel_booking(booking.id, customer_user.id)
    assert "Cannot cancel a booking that has already started" in str(exc_info.value)

def test_idor_prevention_on_bookings(client, customer_user, second_customer_user, sample_bike):
    # Create booking for Customer 1
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)
    booking1 = create_booking(customer_user.id, sample_bike.id, start, end)

    # Log in as Customer 2
    client.post('/auth/login', data={'email': second_customer_user.email, 'password': 'Customer@456'})

    # Customer 2 tries to view Customer 1's confirmation receipt
    response = client.get(f'/bookings/confirmation/{booking1.id}')
    assert response.status_code == 403

    # Customer 2 tries to cancel Customer 1's reservation
    cancel_response = client.post(f'/bookings/{booking1.id}/cancel', follow_redirects=True)
    assert b"Unauthorized: You cannot modify another customer&#39;s booking" in cancel_response.data or b"Unauthorized" in cancel_response.data

    # Booking 1 remains confirmed
    db.session.refresh(booking1)
    assert booking1.status == Booking.STATUS_CONFIRMED
