from models import User

def test_user_registration_success(client):
    response = client.post('/auth/register', data={
        'name': 'New Rider',
        'email': 'rider@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    user = User.query.filter_by(email='rider@example.com').first()
    assert user is not None
    assert user.name == 'New Rider'
    assert user.role == 'customer'
    assert user.check_password('Password123') is True
    # Verify password is not stored plaintext
    assert user.password_hash != 'Password123'

def test_user_registration_duplicate_email(client, customer_user):
    response = client.post('/auth/register', data={
        'name': 'Imposter John',
        'email': customer_user.email, # Duplicate
        'password': 'DifferentPass123',
        'confirm_password': 'DifferentPass123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"This email is already registered" in response.data

def test_user_registration_password_mismatch(client):
    response = client.post('/auth/register', data={
        'name': 'Mismatch User',
        'email': 'mismatch@example.com',
        'password': 'Password123',
        'confirm_password': 'Password456'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Passwords do not match" in response.data
    assert User.query.filter_by(email='mismatch@example.com').first() is None

def test_user_login_success(client, customer_user):
    response = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, John Doe!" in response.data
    assert b"Log Out" in response.data

def test_user_login_invalid_password(client, customer_user):
    response = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'WrongPassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_user_login_nonexistent_email(client):
    response = client.post('/auth/login', data={
        'email': 'nobody@example.com',
        'password': 'SomePassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_user_logout(client, customer_user):
    # Login
    client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    }, follow_redirects=True)

    # Logout
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been safely logged out" in response.data
    assert b"Sign In" in response.data

def test_admin_registration_success(client):
    response = client.post('/auth/register-admin', data={
        'name': 'New Operations Admin',
        'email': 'ops_admin@example.com',
        'password': 'SecureAdminPass@123',
        'confirm_password': 'SecureAdminPass@123',
        'admin_secret_key': 'AdminSecretKey2026'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Administrator account created successfully" in response.data

    user = User.query.filter_by(email='ops_admin@example.com').first()
    assert user is not None
    assert user.role == 'admin'
    assert user.is_admin is True

def test_admin_registration_invalid_key(client):
    response = client.post('/auth/register-admin', data={
        'name': 'Hacker Admin',
        'email': 'hacker@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123',
        'admin_secret_key': 'WrongKey123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid Admin Setup Secret Key" in response.data
    assert User.query.filter_by(email='hacker@example.com').first() is None

