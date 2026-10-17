from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, FloatField, SelectField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required"),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please provide a valid email address")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords do not match")
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError("This email is already registered. Please sign in or use a different email.")

class AdminRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required"),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please provide a valid email address")
    ])
    password = PasswordField('Admin Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Admin password must be at least 8 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords do not match")
    ])
    admin_secret_key = StringField('Admin Setup Secret Key', validators=[
        DataRequired(message="Security authorization key is required to register an administrator")
    ])
    submit = SubmitField('Create Administrator Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError("This email is already registered. Please sign in or use a different email.")

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required")
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class BikeForm(FlaskForm):
    name = StringField('Bike Name', validators=[
        DataRequired(message="Bike name is required"),
        Length(max=100)
    ])
    model = StringField('Model / Brand', validators=[
        DataRequired(message="Model is required"),
        Length(max=100)
    ])
    category = SelectField('Category', choices=[
        ('Mountain', 'Mountain Bike'),
        ('Road', 'Road Bike'),
        ('Electric', 'Electric Bike (E-Bike)'),
        ('City', 'City / Cruiser'),
        ('Hybrid', 'Hybrid Bike')
    ], validators=[DataRequired()])
    price_per_hour = FloatField('Price per Hour ($)', validators=[
        DataRequired(message="Hourly price is required"),
        NumberRange(min=0.5, max=500.0, message="Price must be between $0.50 and $500.00")
    ])
    image_url = StringField('Image URL', validators=[
        Optional(),
        Length(max=500)
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000)
    ])
    is_active = BooleanField('Active & Available for Rental', default=True)
    submit = SubmitField('Save Bike')

class BookingForm(FlaskForm):
    start_time = DateTimeLocalField('Start Date & Time', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="Start time is required")
    ])
    end_time = DateTimeLocalField('End Date & Time', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="End time is required")
    ])
    submit = SubmitField('Confirm Reservation')

    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError("End time must be after start time.")
