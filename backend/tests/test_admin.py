from datetime import datetime, timezone, timedelta
from models import db, Bike, Booking, User
from services.booking_service import create_booking

def test_unauthorized_user_redirected_from_admin(client):
    response = client.get('/admin/dashboard')
    # Should redirect to login
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']

def test_customer_forbidden_from_admin_dashboard(client, customer_user):
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})
    response = client.get('/admin/dashboard')
    assert response.status_code == 403

def test_admin_dashboard_metrics(client, admin_user, customer_user, sample_bike):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    # Create a booking
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=3)
    create_booking(customer_user.id, sample_bike.id, start, end)

    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b"Operations Dashboard" in response.data
    assert b"$30.00" in response.data # 3 hrs * $10.00

def test_admin_add_bike(client, admin_user):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    response = client.post('/admin/bikes/add', data={
        'name': 'Cannondale SuperSix EVO',
        'model': 'EVO Carbon 2',
        'category': 'Road',
        'price_per_hour': 18.50,
        'image_url': 'https://example.com/cannondale.jpg',
        'description': 'Pro racing road bike with aerodynamic carbon frame.',
        'is_active': True
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"was successfully added to inventory" in response.data

    bike = Bike.query.filter_by(name='Cannondale SuperSix EVO').first()
    assert bike is not None
    assert bike.price_per_hour == 18.50
    assert bike.category == 'Road'

def test_admin_edit_bike(client, admin_user, sample_bike):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    response = client.post(f'/admin/bikes/{sample_bike.id}/edit', data={
        'name': 'Trek FX 3 Disc (Upgraded)',
        'model': sample_bike.model,
        'category': sample_bike.category,
        'price_per_hour': 12.50, # Price change
        'image_url': sample_bike.image_url,
        'description': 'Updated description',
        'is_active': True
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"details updated successfully" in response.data

    db.session.refresh(sample_bike)
    assert sample_bike.name == 'Trek FX 3 Disc (Upgraded)'
    assert sample_bike.price_per_hour == 12.50

def test_admin_toggle_bike_active(client, admin_user, sample_bike):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    assert sample_bike.is_active is True

    # Toggle to False
    client.post(f'/admin/bikes/{sample_bike.id}/toggle-status', follow_redirects=True)
    db.session.refresh(sample_bike)
    assert sample_bike.is_active is False

    # Toggle back to True
    client.post(f'/admin/bikes/{sample_bike.id}/toggle-status', follow_redirects=True)
    db.session.refresh(sample_bike)
    assert sample_bike.is_active is True

def test_admin_safe_delete_bike_with_bookings(client, admin_user, customer_user, sample_bike):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    # Create a booking so bike has historical records
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)
    booking = create_booking(customer_user.id, sample_bike.id, start, end)

    # Attempt delete
    response = client.post(f'/admin/bikes/{sample_bike.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b"deactivated rather than permanently erased" in response.data

    # Verify bike still exists in DB, but is_active is now False
    db.session.refresh(sample_bike)
    assert sample_bike is not None
    assert sample_bike.is_active is False
    # Verify booking record is intact
    db.session.refresh(booking)
    assert booking.bike_id == sample_bike.id

def test_admin_safe_delete_bike_without_bookings(client, admin_user):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    unused_bike = Bike(
        name="Temporary Bike",
        model="Test Model",
        category="City",
        price_per_hour=5.0,
        is_active=True
    )
    db.session.add(unused_bike)
    db.session.commit()
    bike_id = unused_bike.id

    response = client.post(f'/admin/bikes/{bike_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b"permanently deleted" in response.data

    assert db.session.get(Bike, bike_id) is None

def test_admin_update_booking_status(client, admin_user, customer_user, sample_bike):
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'AdminSecure@123'})

    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=2)
    booking = create_booking(customer_user.id, sample_bike.id, start, end)
    assert booking.status == Booking.STATUS_CONFIRMED

    # Admin marks booking completed
    response = client.post(f'/admin/bookings/{booking.id}/update-status', data={
        'status': Booking.STATUS_COMPLETED
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"status updated to &#39;Completed&#39;" in response.data or b"Completed" in response.data

    db.session.refresh(booking)
    assert booking.status == Booking.STATUS_COMPLETED
