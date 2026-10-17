from models import db, Bike

def test_bike_listing_public(client, sample_bike):
    response = client.get('/bikes/')
    assert response.status_code == 200
    assert sample_bike.name.encode() in response.data
    assert b"Trek FX 3 Disc" in response.data

def test_bike_filter_by_category(client, sample_bike):
    # Add a Mountain bike
    mountain_bike = Bike(
        name="Trek Marlin 8",
        model="Marlin 8",
        category="Mountain",
        price_per_hour=8.50,
        is_active=True
    )
    db.session.add(mountain_bike)
    db.session.commit()

    # Filter for Mountain
    response = client.get('/bikes/?category=Mountain')
    assert response.status_code == 200
    assert b"Trek Marlin 8" in response.data
    assert b"Trek FX 3 Disc" not in response.data

    # Filter for Hybrid
    response = client.get('/bikes/?category=Hybrid')
    assert response.status_code == 200
    assert b"Trek FX 3 Disc" in response.data
    assert b"Trek Marlin 8" not in response.data

def test_bike_filter_by_price(client, sample_bike):
    # sample_bike has price 10.00
    expensive_bike = Bike(
        name="Specialized Turbo",
        model="Turbo Vado",
        category="Electric",
        price_per_hour=25.00,
        is_active=True
    )
    db.session.add(expensive_bike)
    db.session.commit()

    # Filter with max_price = 15.00
    response = client.get('/bikes/?max_price=15.00')
    assert response.status_code == 200
    assert b"Trek FX 3 Disc" in response.data
    assert b"Specialized Turbo" not in response.data

def test_bike_search_query(client, sample_bike):
    response = client.get('/bikes/?q=hydraulic')
    assert response.status_code == 200
    assert b"Trek FX 3 Disc" in response.data

    response = client.get('/bikes/?q=nonexistentkeyword123')
    assert response.status_code == 200
    assert b"No bikes matched your search" in response.data

def test_bike_detail_page(client, sample_bike):
    response = client.get(f'/bikes/{sample_bike.id}')
    assert response.status_code == 200
    assert sample_bike.name.encode() in response.data
    assert b"Included with Every Rental" in response.data

def test_inactive_bike_hidden_from_public_listing(client, sample_bike):
    sample_bike.is_active = False
    db.session.commit()

    response = client.get('/bikes/')
    assert response.status_code == 200
    assert sample_bike.name.encode() not in response.data
