import os
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegistrationForm, LoginForm, AdminRegistrationForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_safe_url(target: str) -> bool:
    """Ensure redirect URL is strictly internal to prevent open redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('', 'http', 'https') and (not test_url.netloc or test_url.netloc == ref_url.netloc)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('bikes.bike_list'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role='customer'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@auth_bp.route('/register-admin', methods=['GET', 'POST'])
def register_admin():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('bikes.bike_list'))

    form = AdminRegistrationForm()
    if request.method == 'GET' and not form.admin_secret_key.data:
        form.admin_secret_key.data = os.environ.get('ADMIN_REGISTRATION_KEY', 'AdminSecretKey2026')

    if form.validate_on_submit():
        configured_secret = (os.environ.get('ADMIN_REGISTRATION_KEY') or 'AdminSecretKey2026').strip().lower()
        submitted_key = (form.admin_secret_key.data or '').strip().lower()

        if submitted_key != configured_secret:
            flash('Invalid Admin Setup Secret Key. Administrator provisioning unauthorized.', 'danger')
            return render_template('auth/register_admin.html', form=form)

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role='admin'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Administrator account created successfully! Please sign in with your admin credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_admin.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('bikes.bike_list'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.name}!', 'success')

            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('bikes.bike_list'))
        else:
            flash('Invalid email or password. Please verify your credentials and try again.', 'danger')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('main.index'))
