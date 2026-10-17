from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, User, Bike, Booking
from forms import BikeForm
from services.booking_service import update_booking_status, BookingError

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator ensuring that only authenticated users with admin role can access the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please sign in with administrator credentials.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_bikes = Bike.query.count()
    active_bikes = Bike.query.filter_by(is_active=True).count()
    total_bookings = Booking.query.count()
    confirmed_bookings = Booking.query.filter_by(status=Booking.STATUS_CONFIRMED).count()
    completed_bookings = Booking.query.filter_by(status=Booking.STATUS_COMPLETED).count()
    cancelled_bookings = Booking.query.filter_by(status=Booking.STATUS_CANCELLED).count()

    # Revenue calculation: only confirmed and completed bookings generate revenue
    revenue_query = db.session.query(db.func.sum(Booking.total_amount))\
        .filter(Booking.status.in_([Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED]))\
        .scalar()
    total_revenue = round(revenue_query or 0.0, 2)

    total_customers = User.query.filter_by(role='customer').count()

    # Recent 5 bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_bikes=total_bikes,
        active_bikes=active_bikes,
        total_bookings=total_bookings,
        confirmed_bookings=confirmed_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        total_revenue=total_revenue,
        total_customers=total_customers,
        recent_bookings=recent_bookings
    )

@admin_bp.route('/bikes')
@login_required
@admin_required
def bikes_list():
    category_filter = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Bike.query

    if category_filter:
        query = query.filter(Bike.category == category_filter)

    if status_filter == 'active':
        query = query.filter(Bike.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(Bike.is_active == False)

    bikes = query.order_by(Bike.created_at.desc()).all()
    categories = ['Mountain', 'Road', 'Electric', 'City', 'Hybrid']

    return render_template(
        'admin/bikes_list.html',
        bikes=bikes,
        categories=categories,
        category_filter=category_filter,
        status_filter=status_filter
    )

@admin_bp.route('/bikes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def bike_add():
    form = BikeForm()
    if form.validate_on_submit():
        bike = Bike(
            name=form.name.data.strip(),
            model=form.model.data.strip(),
            category=form.category.data,
            price_per_hour=round(float(form.price_per_hour.data), 2),
            image_url=form.image_url.data.strip() if form.image_url.data else None,
            description=form.description.data.strip() if form.description.data else None,
            is_active=form.is_active.data
        )
        db.session.add(bike)
        db.session.commit()
        flash(f"Bike '{bike.name}' was successfully added to inventory.", "success")
        return redirect(url_for('admin.bikes_list'))

    return render_template('admin/bike_form.html', form=form, title="Add New Bike", action="Add")

@admin_bp.route('/bikes/<int:bike_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def bike_edit(bike_id: int):
    bike = Bike.query.get_or_404(bike_id)
    form = BikeForm(obj=bike)

    if form.validate_on_submit():
        bike.name = form.name.data.strip()
        bike.model = form.model.data.strip()
        bike.category = form.category.data
        bike.price_per_hour = round(float(form.price_per_hour.data), 2)
        bike.image_url = form.image_url.data.strip() if form.image_url.data else None
        bike.description = form.description.data.strip() if form.description.data else None
        bike.is_active = form.is_active.data

        db.session.commit()
        flash(f"Bike '{bike.name}' details updated successfully.", "success")
        return redirect(url_for('admin.bikes_list'))

    return render_template('admin/bike_form.html', form=form, title=f"Edit Bike: {bike.name}", action="Update", bike=bike)

@admin_bp.route('/bikes/<int:bike_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def bike_toggle_status(bike_id: int):
    bike = Bike.query.get_or_404(bike_id)
    bike.is_active = not bike.is_active
    db.session.commit()
    status_str = "activated" if bike.is_active else "deactivated"
    flash(f"Bike '{bike.name}' has been {status_str}.", "info")
    return redirect(url_for('admin.bikes_list'))

@admin_bp.route('/bikes/<int:bike_id>/delete', methods=['POST'])
@login_required
@admin_required
def bike_delete(bike_id: int):
    """
    Safely delete a bike:
    If historical bookings exist, enforce soft-delete by deactivating to preserve booking integrity.
    If no bookings exist, hard delete is safely allowed.
    """
    bike = Bike.query.get_or_404(bike_id)
    booking_count = Booking.query.filter_by(bike_id=bike.id).count()

    if booking_count > 0:
        bike.is_active = False
        db.session.commit()
        flash(
            f"Bike '{bike.name}' has {booking_count} historical booking(s). "
            f"To preserve financial and audit integrity, it has been deactivated rather than permanently erased.",
            "warning"
        )
    else:
        db.session.delete(bike)
        db.session.commit()
        flash(f"Bike '{bike.name}' has been permanently deleted from inventory.", "success")

    return redirect(url_for('admin.bikes_list'))

@admin_bp.route('/bookings')
@login_required
@admin_required
def bookings_list():
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()

    query = Booking.query.join(User).join(Bike)

    if status_filter and status_filter.lower() != 'all':
        query = query.filter(Booking.status == status_filter)

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            (User.name.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (Bike.name.ilike(search_pattern)) |
            (Bike.model.ilike(search_pattern))
        )

    bookings = query.order_by(Booking.created_at.desc()).all()

    return render_template(
        'admin/bookings_list.html',
        bookings=bookings,
        status_filter=status_filter,
        search_query=search_query,
        valid_statuses=Booking.VALID_STATUSES
    )

@admin_bp.route('/bookings/<int:booking_id>/update-status', methods=['POST'])
@login_required
@admin_required
def booking_status_update(booking_id: int):
    new_status = request.form.get('status', '').strip()
    try:
        booking = update_booking_status(booking_id, new_status)
        flash(f"Booking #{booking.id} status updated to '{new_status.title()}'.", "success")
    except BookingError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Failed to update booking status.", "danger")

    return redirect(url_for('admin.bookings_list'))
