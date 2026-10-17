import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from models import db, User, Bike, Booking

SAMPLE_BIKES = [
    {
        "name": "Trek Marlin 8 Gen 3",
        "model": "Marlin 8 2024 Edition",
        "category": "Mountain",
        "price_per_hour": 8.50,
        "image_url": "https://images.unsplash.com/photo-1576435728678-68d0fbf94e91?auto=format&fit=crop&w=800&q=80",
        "description": "Trail-ready mountain bike with RockShox air suspension fork, 1x12 wide-range drivetrain, and tubeless-ready rims for supreme off-road performance.",
        "is_active": True
    },
    {
        "name": "Cannondale Synapse Carbon",
        "model": "Synapse Carbon 3 L",
        "category": "Road",
        "price_per_hour": 12.00,
        "image_url": "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=800&q=80",
        "description": "Ultra-light endurance road bike featuring Shimano 105 groupset and SmartSense integrated lighting for fast, safe long-distance tarmac riding.",
        "is_active": True
    },
    {
        "name": "Specialized Turbo Vado 4.0",
        "model": "Turbo Vado 4.0 E-Bike",
        "category": "Electric",
        "price_per_hour": 15.00,
        "image_url": "https://images.unsplash.com/photo-1571068316344-75bc76f77890?auto=format&fit=crop&w=800&q=80",
        "description": "Smooth and powerful pedal-assist e-bike with a 710Wh battery, MasterMind display, and up to 90 miles of assisted range for effortless cruising.",
        "is_active": True
    },
    {
        "name": "Electra Townie 7D Classic",
        "model": "Townie 7D Step-Through",
        "category": "City",
        "price_per_hour": 5.00,
        "image_url": "https://images.unsplash.com/photo-1507035895480-2b3156c31fc8?auto=format&fit=crop&w=800&q=80",
        "description": "The best-selling recreational city bike with Flat Foot Technology for an upright, relaxed posture, plush saddle, and convenient rear rack.",
        "is_active": True
    },
    {
        "name": "Trek FX 3 Disc",
        "model": "FX 3 Disc Fitness",
        "category": "Hybrid",
        "price_per_hour": 6.50,
        "image_url": "https://images.unsplash.com/photo-1532298229144-0ec0c57515c7?auto=format&fit=crop&w=800&q=80",
        "description": "Versatile fitness hybrid bike with carbon fork, all-weather hydraulic disc brakes, and comfortable IsoZone handlebars. Perfect for commutes and trails.",
        "is_active": True
    },
    {
        "name": "Specialized Rockhopper Comp",
        "model": "Rockhopper Comp 29",
        "category": "Mountain",
        "price_per_hour": 7.50,
        "image_url": "https://images.unsplash.com/photo-1511994298241-608e28f14fde?auto=format&fit=crop&w=800&q=80",
        "description": "Durable A1 premium aluminum mountain bike with SR SunTour fork, hydraulic disc brakes, and microSHIFT 1x9 drivetrain.",
        "is_active": True
    },
    {
        "name": "Rad Power RadCity 5 Plus",
        "model": "RadCity 5 Plus Commuter",
        "category": "Electric",
        "price_per_hour": 14.00,
        "image_url": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=800&q=80",
        "description": "Premium commuter e-bike engineered for city streets with 750W geared hub motor, hydraulic brakes, and puncture-resistant tires.",
        "is_active": True
    },
    {
        "name": "Giant Defy Advanced 2",
        "model": "Defy Advanced 2 2024",
        "category": "Road",
        "price_per_hour": 11.00,
        "image_url": "https://images.unsplash.com/photo-1508974239320-0a029497e820?auto=format&fit=crop&w=800&q=80",
        "description": "Engineered for speed and endurance on rough roads, featuring Advanced-grade composite frame and D-Fuse seatpost to absorb vibrations.",
        "is_active": True
    }
]

def seed_database():
    """Populate database with sample bikes, demo accounts, and initial bookings."""
    db.create_all()

    # 1. Seed or update Admin
    admin = User.query.filter_by(email="admin@bikerental.com").first()
    if not admin:
        admin = User(
            name="System Administrator",
            email="admin@bikerental.com",
            role="admin"
        )
        admin.set_password("Admin@12345")
        db.session.add(admin)

    # 2. Seed or update Demo Customer
    customer = User.query.filter_by(email="customer@bikerental.com").first()
    if not customer:
        customer = User(
            name="Alex Morgan",
            email="customer@bikerental.com",
            role="customer"
        )
        customer.set_password("Customer@12345")
        db.session.add(customer)

    db.session.commit()

    # 3. Seed Sample Bikes
    seeded_bikes = []
    for bike_data in SAMPLE_BIKES:
        existing = Bike.query.filter_by(name=bike_data["name"]).first()
        if not existing:
            bike = Bike(**bike_data)
            db.session.add(bike)
            seeded_bikes.append(bike)
        else:
            seeded_bikes.append(existing)

    db.session.commit()

    # 4. Seed sample bookings if none exist
    if Booking.query.count() == 0 and customer and seeded_bikes:
        now = datetime.now(timezone.utc)

        # Booking 1: Past completed booking
        past_start = now - timedelta(days=3, hours=5)
        past_end = now - timedelta(days=3, hours=1)
        bike1 = seeded_bikes[0]
        hours1 = round((past_end - past_start).total_seconds() / 3600.0, 2)
        booking1 = Booking(
            user_id=customer.id,
            bike_id=bike1.id,
            start_time=past_start,
            end_time=past_end,
            total_amount=round(hours1 * bike1.price_per_hour, 2),
            status=Booking.STATUS_COMPLETED
        )
        db.session.add(booking1)

        # Booking 2: Upcoming confirmed booking
        future_start = now + timedelta(days=2, hours=2)
        future_end = now + timedelta(days=2, hours=6)
        bike2 = seeded_bikes[2] # Electric bike
        hours2 = round((future_end - future_start).total_seconds() / 3600.0, 2)
        booking2 = Booking(
            user_id=customer.id,
            bike_id=bike2.id,
            start_time=future_start,
            end_time=future_end,
            total_amount=round(hours2 * bike2.price_per_hour, 2),
            status=Booking.STATUS_CONFIRMED
        )
        db.session.add(booking2)

        db.session.commit()
        print("[OK] Sample bookings seeded.")

    print(f"[OK] Seed complete: {len(SAMPLE_BIKES)} bikes ready. Admin & Demo Customer accounts active.")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_database()
