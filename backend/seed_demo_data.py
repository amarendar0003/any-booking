import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from services.models import (
    Country,
    State,
    District,
    City,
    Category,
    AttributeDefinition,
    RegionalCategoryConfig,
    Vendor,
    VendorStaffUser,
    Service,
    ServiceAttributeValue,
    StaffProfile,
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_or_create_user(username, email, password, **extra):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            **extra,
        },
    )

    if created:
        user.set_password(password)
        user.save()

    return user


print("\n======================================")
print(" ANYBOOKING DEMO DATA")
print("======================================\n")


# --------------------------------------------------
# USERS
# --------------------------------------------------

admin = get_or_create_user(
    "demo_admin",
    "demo.admin@anybooking.com",
    "Demo@12345",
    first_name="Demo",
    last_name="Administrator",
    is_staff=True,
    is_superuser=True,
)

vendor_user = get_or_create_user(
    "demo_vendor",
    "vendor@anybooking.com",
    "Demo@12345",
    first_name="Raj",
    last_name="Events",
)

vendor_staff_user = get_or_create_user(
    "vendor_staff",
    "staff@anybooking.com",
    "Demo@12345",
    first_name="Event",
    last_name="Staff",
)

staff_user = get_or_create_user(
    "demo_staff",
    "staff.admin@anybooking.com",
    "Demo@12345",
    first_name="AnyBooking",
    last_name="Staff",
    is_staff=True,
)


# --------------------------------------------------
# COUNTRY
# --------------------------------------------------

country, _ = Country.objects.get_or_create(
    code="IN",
    defaults={
        "name": "India",
        "currency": "INR",
        "currency_symbol": "₹",
        "phone_code": "+91",
        "is_active": True,
    },
)


# --------------------------------------------------
# STATES
# --------------------------------------------------

telangana, _ = State.objects.get_or_create(
    country=country,
    name="Telangana",
    defaults={
        "code": "TG",
        "is_active": True,
    },
)

andhra, _ = State.objects.get_or_create(
    country=country,
    name="Andhra Pradesh",
    defaults={
        "code": "AP",
        "is_active": True,
    },
)


# --------------------------------------------------
# DISTRICTS
# --------------------------------------------------

hyderabad_district, _ = District.objects.get_or_create(
    state=telangana,
    name="Hyderabad",
    defaults={"is_active": True},
)

rangareddy_district, _ = District.objects.get_or_create(
    state=telangana,
    name="Rangareddy",
    defaults={"is_active": True},
)

warangal_district, _ = District.objects.get_or_create(
    state=telangana,
    name="Hanamkonda",
    defaults={"is_active": True},
)


# --------------------------------------------------
# CITIES
# --------------------------------------------------

hyderabad, _ = City.objects.get_or_create(
    district=hyderabad_district,
    name="Hyderabad",
    defaults={
        "pin_code": "500001",
        "is_active": True,
        "is_featured": True,
    },
)

secunderabad, _ = City.objects.get_or_create(
    district=hyderabad_district,
    name="Secunderabad",
    defaults={
        "pin_code": "500003",
        "is_active": True,
        "is_featured": True,
    },
)

gachibowli, _ = City.objects.get_or_create(
    district=rangareddy_district,
    name="Gachibowli",
    defaults={
        "pin_code": "500032",
        "is_active": True,
        "is_featured": True,
    },
)

warangal, _ = City.objects.get_or_create(
    district=warangal_district,
    name="Warangal",
    defaults={
        "pin_code": "506001",
        "is_active": True,
        "is_featured": True,
    },
)


# --------------------------------------------------
# CATEGORIES
# --------------------------------------------------

categories = {}

category_data = [
    (
        Category.BANQUET_HALL,
        "Banquet halls for weddings, receptions and events.",
    ),
    (
        Category.MUSIC_BAND,
        "Professional music bands and live entertainment.",
    ),
    (
        Category.EVENT_MANAGEMENT,
        "Complete event planning and management services.",
    ),
    (
        Category.CATERING,
        "Wedding and event catering services.",
    ),
    (
        Category.DANCING,
        "Dance performers and choreography services.",
    ),
    (
        Category.PRIESTS,
        "Priests and traditional ceremony services.",
    ),
    (
        Category.HOTELS,
        "Hotels and accommodation for guests.",
    ),
]

for slug, description in category_data:
    category, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={
            "description": description,
            "is_active": True,
        },
    )

    categories[slug] = category


# --------------------------------------------------
# ATTRIBUTES
# --------------------------------------------------

hall_capacity, _ = AttributeDefinition.objects.get_or_create(
    category=categories[Category.BANQUET_HALL],
    slug="capacity",
    defaults={
        "name": "Capacity",
        "data_type": AttributeDefinition.NUMBER,
        "unit": "persons",
        "is_filterable": True,
        "order": 1,
    },
)

parking, _ = AttributeDefinition.objects.get_or_create(
    category=categories[Category.BANQUET_HALL],
    slug="parking",
    defaults={
        "name": "Parking Available",
        "data_type": AttributeDefinition.BOOLEAN,
        "is_filterable": True,
        "order": 2,
    },
)

ac_rooms, _ = AttributeDefinition.objects.get_or_create(
    category=categories[Category.HOTELS],
    slug="rooms",
    defaults={
        "name": "Rooms",
        "data_type": AttributeDefinition.NUMBER,
        "unit": "rooms",
        "is_filterable": True,
        "order": 1,
    },
)

veg_nonveg, _ = AttributeDefinition.objects.get_or_create(
    category=categories[Category.CATERING],
    slug="food-type",
    defaults={
        "name": "Food Type",
        "data_type": AttributeDefinition.CHOICE,
        "choices": "Vegetarian,Non-Vegetarian,Both",
        "is_filterable": True,
        "order": 1,
    },
)


# --------------------------------------------------
# REGIONAL CATEGORY CONFIG
# --------------------------------------------------

hall_config, _ = RegionalCategoryConfig.objects.get_or_create(
    category=categories[Category.BANQUET_HALL],
    country=country,
    state=telangana,
    defaults={
        "local_display_name": "Banquet Halls",
        "local_description": "Wedding and event banquet halls in Telangana.",
        "price_unit_label": "per event",
    },
)

hall_config.enabled_attributes.set([
    hall_capacity,
    parking,
])


hotel_config, _ = RegionalCategoryConfig.objects.get_or_create(
    category=categories[Category.HOTELS],
    country=country,
    state=telangana,
    defaults={
        "local_display_name": "Hotels",
        "local_description": "Hotels and accommodation services.",
        "price_unit_label": "per night",
    },
)

hotel_config.enabled_attributes.set([
    ac_rooms,
])


# --------------------------------------------------
# VENDORS
# --------------------------------------------------

vendor1, _ = Vendor.objects.get_or_create(
    name="Raj Events & Convention",
    defaults={
        "user": vendor_user,
        "email": "vendor@anybooking.com",
        "phone": "+91 9876543210",
        "address": "Gachibowli, Hyderabad, Telangana",
        "city": gachibowli,
        "is_active": True,
        "notify_on_booking": True,
    },
)

vendor2, _ = Vendor.objects.get_or_create(
    name="Hyderabad Celebration Group",
    defaults={
        "email": "celebration@anybooking.com",
        "phone": "+91 9876501234",
        "address": "Banjara Hills, Hyderabad, Telangana",
        "city": hyderabad,
        "is_active": True,
        "notify_on_booking": True,
    },
)


# --------------------------------------------------
# VENDOR STAFF
# --------------------------------------------------

VendorStaffUser.objects.get_or_create(
    vendor=vendor1,
    user=vendor_staff_user,
)


# --------------------------------------------------
# SERVICES
# 7 categories x 5 services = 35 services
# --------------------------------------------------

services = []

service_data = [

    # ==================================================
    # BANQUET HALLS - 5
    # ==================================================

    {
        "vendor": vendor1,
        "category": categories[Category.BANQUET_HALL],
        "city": gachibowli,
        "name": "Grand Palace Banquet Hall",
        "description": "Premium banquet hall suitable for weddings, receptions and corporate events.",
        "address": "Financial District, Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("85000"),
        "our_price": Decimal("95000"),
        "discount_percent": Decimal("10"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 245,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.BANQUET_HALL],
        "city": hyderabad,
        "name": "Royal Celebration Hall",
        "description": "Elegant event hall with modern interiors and excellent facilities.",
        "address": "Banjara Hills, Hyderabad",
        "pin_code": "500034",
        "base_price": Decimal("65000"),
        "our_price": Decimal("75000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 180,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.BANQUET_HALL],
        "city": secunderabad,
        "name": "Pearl Grand Function Hall",
        "description": "Spacious function hall for weddings, receptions and family celebrations.",
        "address": "Sainikpuri, Secunderabad",
        "pin_code": "500094",
        "base_price": Decimal("55000"),
        "our_price": Decimal("62000"),
        "discount_percent": Decimal("8"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 120,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.BANQUET_HALL],
        "city": warangal,
        "name": "Heritage Grand Hall",
        "description": "Traditional-style banquet hall for weddings and cultural events.",
        "address": "Hanamkonda, Warangal",
        "pin_code": "506001",
        "base_price": Decimal("45000"),
        "our_price": Decimal("52000"),
        "discount_percent": Decimal("7"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 90,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.BANQUET_HALL],
        "city": hyderabad,
        "name": "Skyline Convention Hall",
        "description": "Modern convention hall suitable for large weddings and corporate events.",
        "address": "Madhapur, Hyderabad",
        "pin_code": "500081",
        "base_price": Decimal("110000"),
        "our_price": Decimal("125000"),
        "discount_percent": Decimal("10"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 350,
    },


    # ==================================================
    # MUSIC BANDS - 5
    # ==================================================

    {
        "vendor": vendor2,
        "category": categories[Category.MUSIC_BAND],
        "city": secunderabad,
        "name": "Hyderabad Live Music Band",
        "description": "Professional live music and wedding entertainment band.",
        "address": "Secunderabad, Telangana",
        "pin_code": "500003",
        "base_price": Decimal("30000"),
        "our_price": Decimal("35000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 115,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.MUSIC_BAND],
        "city": hyderabad,
        "name": "Royal Beats Band",
        "description": "Energetic live band for weddings, receptions and private events.",
        "address": "Jubilee Hills, Hyderabad",
        "pin_code": "500033",
        "base_price": Decimal("25000"),
        "our_price": Decimal("30000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 160,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.MUSIC_BAND],
        "city": gachibowli,
        "name": "Melody Makers",
        "description": "Versatile music group performing Bollywood, Telugu and English songs.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("22000"),
        "our_price": Decimal("28000"),
        "discount_percent": Decimal("8"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 95,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.MUSIC_BAND],
        "city": warangal,
        "name": "Warangal Wedding Beats",
        "description": "Wedding music and entertainment band for traditional and modern celebrations.",
        "address": "Warangal, Telangana",
        "pin_code": "506002",
        "base_price": Decimal("18000"),
        "our_price": Decimal("22000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 75,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.MUSIC_BAND],
        "city": hyderabad,
        "name": "Rhythm Stars Live",
        "description": "Premium live entertainment band for large celebrations and corporate events.",
        "address": "Kondapur, Hyderabad",
        "pin_code": "500084",
        "base_price": Decimal("40000"),
        "our_price": Decimal("48000"),
        "discount_percent": Decimal("10"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 210,
    },


    # ==================================================
    # EVENT MANAGEMENT - 5
    # ==================================================

    {
        "vendor": vendor1,
        "category": categories[Category.EVENT_MANAGEMENT],
        "city": gachibowli,
        "name": "Perfect Day Event Management",
        "description": "End-to-end wedding and corporate event management.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("100000"),
        "our_price": Decimal("120000"),
        "discount_percent": Decimal("8"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 410,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.EVENT_MANAGEMENT],
        "city": hyderabad,
        "name": "Dream Wedding Planners",
        "description": "Complete wedding planning, decoration and coordination services.",
        "address": "Banjara Hills, Hyderabad",
        "pin_code": "500034",
        "base_price": Decimal("85000"),
        "our_price": Decimal("100000"),
        "discount_percent": Decimal("10"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 290,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.EVENT_MANAGEMENT],
        "city": secunderabad,
        "name": "Elite Event Solutions",
        "description": "Professional event planning for weddings, birthdays and corporate functions.",
        "address": "Begumpet, Hyderabad",
        "pin_code": "500016",
        "base_price": Decimal("70000"),
        "our_price": Decimal("82000"),
        "discount_percent": Decimal("7"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 175,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.EVENT_MANAGEMENT],
        "city": warangal,
        "name": "Celebration Planners Warangal",
        "description": "Affordable event planning and coordination for local celebrations.",
        "address": "Hanamkonda, Warangal",
        "pin_code": "506001",
        "base_price": Decimal("50000"),
        "our_price": Decimal("60000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 100,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.EVENT_MANAGEMENT],
        "city": hyderabad,
        "name": "Luxury Events Hyderabad",
        "description": "Premium luxury event planning with complete venue and guest management.",
        "address": "Jubilee Hills, Hyderabad",
        "pin_code": "500033",
        "base_price": Decimal("150000"),
        "our_price": Decimal("175000"),
        "discount_percent": Decimal("12"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 380,
    },


    # ==================================================
    # CATERING - 5
    # ==================================================

    {
        "vendor": vendor1,
        "category": categories[Category.CATERING],
        "city": hyderabad,
        "name": "Royal Feast Catering",
        "description": "Complete vegetarian and non-vegetarian catering for weddings and corporate events.",
        "address": "Madhapur, Hyderabad",
        "pin_code": "500081",
        "base_price": Decimal("650"),
        "our_price": Decimal("750"),
        "discount_percent": Decimal("5"),
        "price_unit": "per plate",
        "is_featured": True,
        "view_count": 320,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.CATERING],
        "city": gachibowli,
        "name": "Andhra Spice Catering",
        "description": "Authentic Andhra and Telangana cuisine for weddings and celebrations.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("500"),
        "our_price": Decimal("600"),
        "discount_percent": Decimal("5"),
        "price_unit": "per plate",
        "is_featured": True,
        "view_count": 240,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.CATERING],
        "city": secunderabad,
        "name": "Royal Veg Caterers",
        "description": "Pure vegetarian catering with traditional Indian dishes and desserts.",
        "address": "Tarnaka, Hyderabad",
        "pin_code": "500017",
        "base_price": Decimal("400"),
        "our_price": Decimal("500"),
        "discount_percent": Decimal("5"),
        "price_unit": "per plate",
        "is_featured": False,
        "view_count": 150,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.CATERING],
        "city": warangal,
        "name": "Heritage Food Services",
        "description": "Traditional Telangana food catering for weddings and family events.",
        "address": "Warangal, Telangana",
        "pin_code": "506002",
        "base_price": Decimal("350"),
        "our_price": Decimal("450"),
        "discount_percent": Decimal("5"),
        "price_unit": "per plate",
        "is_featured": False,
        "view_count": 105,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.CATERING],
        "city": hyderabad,
        "name": "Royal Banquet Catering",
        "description": "Premium multi-cuisine catering with customizable wedding menus.",
        "address": "Kondapur, Hyderabad",
        "pin_code": "500084",
        "base_price": Decimal("900"),
        "our_price": Decimal("1100"),
        "discount_percent": Decimal("10"),
        "price_unit": "per plate",
        "is_featured": True,
        "view_count": 280,
    },


    # ==================================================
    # DANCING - 5
    # ==================================================

    {
        "vendor": vendor1,
        "category": categories[Category.DANCING],
        "city": warangal,
        "name": "Telangana Dance Troupe",
        "description": "Traditional and modern dance performances for special occasions.",
        "address": "Hanamkonda, Warangal",
        "pin_code": "506001",
        "base_price": Decimal("18000"),
        "our_price": Decimal("20000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 95,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.DANCING],
        "city": hyderabad,
        "name": "Rhythm Dance Academy",
        "description": "Professional dance performances and choreography for weddings.",
        "address": "Madhapur, Hyderabad",
        "pin_code": "500081",
        "base_price": Decimal("15000"),
        "our_price": Decimal("18000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 130,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.DANCING],
        "city": gachibowli,
        "name": "Wedding Dance Crew",
        "description": "Specialized wedding choreography and group performances.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("12000"),
        "our_price": Decimal("15000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 85,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.DANCING],
        "city": secunderabad,
        "name": "Classical Dance Performers",
        "description": "Classical Indian dance performances for weddings and cultural events.",
        "address": "Secunderabad, Telangana",
        "pin_code": "500003",
        "base_price": Decimal("16000"),
        "our_price": Decimal("19000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per event",
        "is_featured": False,
        "view_count": 70,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.DANCING],
        "city": hyderabad,
        "name": "Fusion Dance Studio",
        "description": "Modern and traditional fusion dance performances for celebrations.",
        "address": "Jubilee Hills, Hyderabad",
        "pin_code": "500033",
        "base_price": Decimal("20000"),
        "our_price": Decimal("24000"),
        "discount_percent": Decimal("8"),
        "price_unit": "per event",
        "is_featured": True,
        "view_count": 145,
    },


    # ==================================================
    # PRIESTS - 5
    # ==================================================

    {
        "vendor": vendor2,
        "category": categories[Category.PRIESTS],
        "city": hyderabad,
        "name": "Sri Vedic Purohit Services",
        "description": "Traditional Hindu priest services for weddings and ceremonies.",
        "address": "Kukatpally, Hyderabad",
        "pin_code": "500072",
        "base_price": Decimal("8000"),
        "our_price": Decimal("10000"),
        "discount_percent": Decimal("0"),
        "price_unit": "per ceremony",
        "is_featured": False,
        "view_count": 140,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.PRIESTS],
        "city": gachibowli,
        "name": "Sri Ganesh Vedic Services",
        "description": "Experienced priests for wedding ceremonies and traditional rituals.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("7000"),
        "our_price": Decimal("8500"),
        "discount_percent": Decimal("0"),
        "price_unit": "per ceremony",
        "is_featured": True,
        "view_count": 110,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.PRIESTS],
        "city": secunderabad,
        "name": "Vedic Wedding Priests",
        "description": "Traditional wedding priest services with complete ceremony guidance.",
        "address": "Secunderabad, Telangana",
        "pin_code": "500003",
        "base_price": Decimal("6000"),
        "our_price": Decimal("7500"),
        "discount_percent": Decimal("0"),
        "price_unit": "per ceremony",
        "is_featured": False,
        "view_count": 85,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.PRIESTS],
        "city": warangal,
        "name": "Telangana Purohit Services",
        "description": "Traditional priest services for weddings, housewarming and ceremonies.",
        "address": "Warangal, Telangana",
        "pin_code": "506001",
        "base_price": Decimal("5000"),
        "our_price": Decimal("6500"),
        "discount_percent": Decimal("0"),
        "price_unit": "per ceremony",
        "is_featured": False,
        "view_count": 65,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.PRIESTS],
        "city": hyderabad,
        "name": "Sri Lakshmi Vedic Priests",
        "description": "Experienced Vedic priests for traditional Hindu wedding ceremonies.",
        "address": "Banjara Hills, Hyderabad",
        "pin_code": "500034",
        "base_price": Decimal("9000"),
        "our_price": Decimal("11000"),
        "discount_percent": Decimal("0"),
        "price_unit": "per ceremony",
        "is_featured": True,
        "view_count": 125,
    },


    # ==================================================
    # HOTELS - 5
    # ==================================================

    {
        "vendor": vendor2,
        "category": categories[Category.HOTELS],
        "city": hyderabad,
        "name": "Grand Hyderabad Hotel",
        "description": "Comfortable hotel accommodation for wedding and business guests.",
        "address": "Somajiguda, Hyderabad",
        "pin_code": "500082",
        "base_price": Decimal("4500"),
        "our_price": Decimal("5000"),
        "discount_percent": Decimal("10"),
        "price_unit": "per night",
        "is_featured": True,
        "view_count": 275,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.HOTELS],
        "city": gachibowli,
        "name": "Gachibowli Grand Hotel",
        "description": "Modern hotel rooms close to major business and event destinations.",
        "address": "Gachibowli, Hyderabad",
        "pin_code": "500032",
        "base_price": Decimal("4000"),
        "our_price": Decimal("4800"),
        "discount_percent": Decimal("8"),
        "price_unit": "per night",
        "is_featured": True,
        "view_count": 220,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.HOTELS],
        "city": secunderabad,
        "name": "Secunderabad Comfort Inn",
        "description": "Comfortable accommodation for families and event guests.",
        "address": "Secunderabad, Telangana",
        "pin_code": "500003",
        "base_price": Decimal("3000"),
        "our_price": Decimal("3500"),
        "discount_percent": Decimal("5"),
        "price_unit": "per night",
        "is_featured": False,
        "view_count": 150,
    },
    {
        "vendor": vendor1,
        "category": categories[Category.HOTELS],
        "city": warangal,
        "name": "Warangal Heritage Hotel",
        "description": "Convenient hotel accommodation for weddings and cultural events.",
        "address": "Hanamkonda, Warangal",
        "pin_code": "506001",
        "base_price": Decimal("2500"),
        "our_price": Decimal("3000"),
        "discount_percent": Decimal("5"),
        "price_unit": "per night",
        "is_featured": False,
        "view_count": 95,
    },
    {
        "vendor": vendor2,
        "category": categories[Category.HOTELS],
        "city": hyderabad,
        "name": "Luxury Hyderabad Suites",
        "description": "Premium rooms and suites for wedding and corporate guests.",
        "address": "Jubilee Hills, Hyderabad",
        "pin_code": "500033",
        "base_price": Decimal("7000"),
        "our_price": Decimal("8500"),
        "discount_percent": Decimal("10"),
        "price_unit": "per night",
        "is_featured": True,
        "view_count": 310,
    },
]


# --------------------------------------------------
# CREATE SERVICES
# --------------------------------------------------

for data in service_data:
    service, created = Service.objects.get_or_create(
        name=data["name"],
        defaults=data,
    )

    services.append(service)


# --------------------------------------------------
# SERVICE ATTRIBUTES
# --------------------------------------------------

capacity_map = {
    "Grand Palace Banquet Hall": 500,
    "Royal Celebration Hall": 300,
    "Pearl Grand Function Hall": 250,
    "Heritage Grand Hall": 200,
    "Skyline Convention Hall": 800,
}

for service in services:

    # Banquet Hall attributes
    if service.category.slug == Category.BANQUET_HALL:

        ServiceAttributeValue.objects.update_or_create(
            service=service,
            attribute=hall_capacity,
            defaults={
                "value_number": Decimal(
                    str(capacity_map.get(service.name, 300))
                )
            },
        )

        ServiceAttributeValue.objects.update_or_create(
            service=service,
            attribute=parking,
            defaults={
                "value_boolean": True,
            },
        )

    # Hotel attributes
    elif service.category.slug == Category.HOTELS:

        hotel_rooms = {
            "Grand Hyderabad Hotel": 80,
            "Gachibowli Grand Hotel": 65,
            "Secunderabad Comfort Inn": 50,
            "Warangal Heritage Hotel": 40,
            "Luxury Hyderabad Suites": 100,
        }

        ServiceAttributeValue.objects.update_or_create(
            service=service,
            attribute=ac_rooms,
            defaults={
                "value_number": Decimal(
                    str(hotel_rooms.get(service.name, 50))
                )
            },
        )

    # Catering attributes
    elif service.category.slug == Category.CATERING:

        ServiceAttributeValue.objects.update_or_create(
            service=service,
            attribute=veg_nonveg,
            defaults={
                "value_text": "Both",
            },
        )


# --------------------------------------------------
# STAFF PROFILE
# --------------------------------------------------

StaffProfile.objects.update_or_create(
    user=staff_user,
    defaults={
        "country": country,
        "state": telangana,
        "city": hyderabad,
        "notes": "Demo AnyBooking staff account",
    },
)


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("\n======================================")
print(" DEMO DATA CREATED SUCCESSFULLY")
print("======================================")

print(f"Countries : {Country.objects.count()}")
print(f"States    : {State.objects.count()}")
print(f"Districts : {District.objects.count()}")
print(f"Cities    : {City.objects.count()}")
print(f"Categories: {Category.objects.count()}")
print(f"Attributes: {AttributeDefinition.objects.count()}")
print(f"Vendors   : {Vendor.objects.count()}")
print(f"Services  : {Service.objects.count()}")
print(f"Users     : {User.objects.count()}")

print("\nServices by category:")
for slug, category in categories.items():
    print(
        f"  {slug}: "
        f"{Service.objects.filter(category=category).count()}"
    )

print("\nDemo login accounts:")
print("--------------------")

print("Admin:")
print("  Username: demo_admin")
print("  Password: Demo@12345")

print("\nVendor:")
print("  Username: demo_vendor")
print("  Password: Demo@12345")

print("\nVendor Staff:")
print("  Username: vendor_staff")
print("  Password: Demo@12345")

print("\nStaff:")
print("  Username: demo_staff")
print("  Password: Demo@12345")

print("\nDone.")
