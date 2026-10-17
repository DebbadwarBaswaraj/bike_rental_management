from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # 'customer' or 'admin'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    bookings = db.relationship('Booking', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Bike(db.Model):
    __tablename__ = 'bikes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True) # Mountain, Road, Electric, City, Hybrid
    description = db.Column(db.Text, nullable=True)
    price_per_hour = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Soft delete flag
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    bookings = db.relationship('Booking', back_populates='bike', lazy='dynamic')

    def is_available(self, start_time: datetime, end_time: datetime, exclude_booking_id: int | None = None) -> bool:
        """
        Check if the bike is available in the given time window.
        An overlap exists if:
            existing.start_time < new_end_time AND existing.end_time > new_start_time
        and existing status is in ('confirmed', 'pending').
        """
        if not self.is_active:
            return False

        query = Booking.query.filter(
            Booking.bike_id == self.id,
            Booking.status.in_(['confirmed', 'pending']),
            Booking.start_time < end_time,
            Booking.end_time > start_time
        )
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        return query.first() is None

    def __repr__(self) -> str:
        return f"<Bike id={self.id} name='{self.name}' price_per_hour={self.price_per_hour} active={self.is_active}>"


class Booking(db.Model):
    __tablename__ = 'bookings'

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    VALID_STATUSES = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_COMPLETED]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bikes.id', ondelete='RESTRICT'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default=STATUS_CONFIRMED, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='bookings')
    bike = db.relationship('Bike', back_populates='bookings')

    @property
    def duration_hours(self) -> float:
        """Calculate duration in hours with 2 decimal precision."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            hours = delta.total_seconds() / 3600.0
            return round(hours, 2)
        return 0.0

    @property
    def can_be_cancelled(self) -> bool:
        """
        A booking can be cancelled only if:
        1. Current status is 'confirmed' or 'pending'
        2. The rental start time is still in the future.
        """
        now = datetime.now(timezone.utc)
        # Note: SQLite stores naive datetimes, so ensure comparison handles naive/aware cleanly
        booking_start = self.start_time
        if booking_start.tzinfo is None:
            booking_start = booking_start.replace(tzinfo=timezone.utc)
        return self.status in [self.STATUS_CONFIRMED, self.STATUS_PENDING] and booking_start > now

    def __repr__(self) -> str:
        return f"<Booking id={self.id} user_id={self.user_id} bike_id={self.bike_id} status='{self.status}'>"
