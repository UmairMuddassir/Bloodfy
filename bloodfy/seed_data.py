# Bloodfy Seed Data Script
# ========================
# Creates sample donors (all 8 blood groups), blood stock entries,
# and blood stock data for demo/testing purposes.
#
# Usage:
#     python seed_data.py

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodfy_project.settings')

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from datetime import date, timedelta
from users.models import User
from donors.models import Donor
from blood_stock.models import BloodStock
from django.utils import timezone

print("=" * 60)
print("  🩸 Bloodfy — Seed Data Generator")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# 1. CREATE DONOR USERS (one per blood group + extras)
# ─────────────────────────────────────────────────────────────

DONORS_DATA = [
    # (first_name, last_name, email, phone, blood_group, city, lat, lon, weight, dob, cnic)
    ("Ahmed", "Khan", "ahmed.khan@bloodfy.com", "+923001234567", "A+", "Lahore", 31.5204, 74.3587, 72, "1995-03-15", "3520112345671"),
    ("Fatima", "Ali", "fatima.ali@bloodfy.com", "+923012345678", "A-", "Lahore", 31.5497, 74.3436, 58, "1998-07-22", "3520212345672"),
    ("Hassan", "Raza", "hassan.raza@bloodfy.com", "+923023456789", "B+", "Lahore", 31.4697, 74.2728, 80, "1992-11-08", "3520312345673"),
    ("Ayesha", "Malik", "ayesha.malik@bloodfy.com", "+923034567890", "B-", "Lahore", 31.5127, 74.3545, 55, "1997-01-30", "3520412345674"),
    ("Usman", "Butt", "usman.butt@bloodfy.com", "+923045678901", "O+", "Lahore", 31.4826, 74.3292, 85, "1990-05-12", "3520512345675"),
    ("Zainab", "Shah", "zainab.shah@bloodfy.com", "+923056789012", "O-", "Lahore", 31.5580, 74.3096, 62, "1996-09-18", "3520612345676"),
    ("Bilal", "Ahmed", "bilal.ahmed@bloodfy.com", "+923067890123", "AB+", "Lahore", 31.4504, 74.3920, 75, "1993-04-25", "3520712345677"),
    ("Sara", "Hussain", "sara.hussain@bloodfy.com", "+923078901234", "AB-", "Lahore", 31.5310, 74.3150, 60, "1999-12-05", "3520812345678"),
    # Extra donors in different cities
    ("Ali", "Nawaz", "ali.nawaz@bloodfy.com", "+923089012345", "O+", "Islamabad", 33.6844, 73.0479, 78, "1991-08-14", "3710112345679"),
    ("Mariam", "Tariq", "mariam.tariq@bloodfy.com", "+923090123456", "A+", "Karachi", 24.8607, 67.0011, 56, "1994-02-28", "4210112345680"),
    ("Hamza", "Iqbal", "hamza.iqbal@bloodfy.com", "+923101234567", "B+", "Faisalabad", 31.4504, 73.1350, 82, "1988-06-10", "3310112345681"),
    ("Noor", "Fatima", "noor.fatima@bloodfy.com", "+923112345678", "O-", "Rawalpindi", 33.5651, 73.0169, 54, "2000-10-20", "3710212345682"),
    ("Imran", "Siddiqui", "imran.siddiqui@bloodfy.com", "+923123456789", "A-", "Multan", 30.1575, 71.5249, 70, "1989-03-05", "3610112345683"),
    ("Hira", "Qureshi", "hira.qureshi@bloodfy.com", "+923134567890", "AB+", "Peshawar", 34.0151, 71.5249, 59, "1997-07-15", "1710112345684"),
    ("Tariq", "Mehmood", "tariq.mehmood@bloodfy.com", "+923145678901", "B-", "Quetta", 30.1798, 66.9750, 88, "1985-11-25", "5410112345685"),
    ("Sana", "Aslam", "sana.aslam@bloodfy.com", "+923156789012", "AB-", "Lahore", 31.5001, 74.3500, 52, "2001-04-08", "3520912345686"),
]

created_donors = 0
skipped_donors = 0

for first, last, email, phone, bg, city, lat, lon, weight, dob, cnic in DONORS_DATA:
    # Check if user already exists
    if User.objects.filter(email=email).exists():
        print(f"  ⏭  {first} {last} ({bg}) — already exists, skipping")
        skipped_donors += 1
        continue
    
    # Create user
    user = User.objects.create_user(
        email=email,
        password="Bloodfy@123",
        first_name=first,
        last_name=last,
        phone_number=phone,
        user_type="user",
        is_verified=True,
        is_active=True,
        city=city,
        donor_status="DONOR_APPROVED",
        donor_status_updated_at=timezone.now(),
    )
    
    # Create donor profile
    Donor.objects.create(
        user=user,
        blood_group=bg,
        city=city,
        address=f"{city}, Pakistan",
        latitude=lat,
        longitude=lon,
        weight_kg=weight,
        date_of_birth=date.fromisoformat(dob),
        cnic=cnic,
        is_active=True,
        is_eligible=True,
        availability_status=True,
        response_rate=round(80 + (hash(email) % 20), 2),
        donation_count=hash(email) % 8,
    )
    
    created_donors += 1
    print(f"  ✅ {first} {last} ({bg}, {city}) — created")

print(f"\n  Donors: {created_donors} created, {skipped_donors} skipped")

# ─────────────────────────────────────────────────────────────
# 2. CREATE BLOOD STOCK ENTRIES
# ─────────────────────────────────────────────────────────────

print("\n" + "─" * 60)
print("  Creating Blood Stock entries...")
print("─" * 60)

BLOOD_STOCK_DATA = [
    # (blood_group, hospital, city, units, threshold)
    ("A+", "Jinnah Hospital", "Lahore", 45, 10),
    ("A-", "Jinnah Hospital", "Lahore", 12, 5),
    ("B+", "Jinnah Hospital", "Lahore", 38, 10),
    ("B-", "Jinnah Hospital", "Lahore", 8, 5),
    ("O+", "Jinnah Hospital", "Lahore", 52, 15),
    ("O-", "Jinnah Hospital", "Lahore", 15, 10),
    ("AB+", "Jinnah Hospital", "Lahore", 20, 5),
    ("AB-", "Jinnah Hospital", "Lahore", 6, 5),
    ("A+", "Mayo Hospital", "Lahore", 30, 10),
    ("B+", "Mayo Hospital", "Lahore", 25, 10),
    ("O+", "Mayo Hospital", "Lahore", 40, 15),
    ("O-", "Mayo Hospital", "Lahore", 10, 10),
    ("A+", "PIMS Hospital", "Islamabad", 35, 10),
    ("O+", "PIMS Hospital", "Islamabad", 28, 10),
    ("B+", "Aga Khan Hospital", "Karachi", 42, 10),
    ("O+", "Aga Khan Hospital", "Karachi", 55, 15),
]

created_stock = 0
updated_stock = 0

for bg, hospital, city, units, threshold in BLOOD_STOCK_DATA:
    stock, created = BloodStock.objects.update_or_create(
        blood_group=bg,
        hospital_name=hospital,
        defaults={
            'hospital_city': city,
            'units_available': units,
            'critical_threshold': threshold,
        }
    )
    if created:
        created_stock += 1
        print(f"  ✅ {bg} at {hospital} — {units} units")
    else:
        updated_stock += 1
        print(f"  🔄 {bg} at {hospital} — updated to {units} units")

print(f"\n  Blood Stock: {created_stock} created, {updated_stock} updated")

# ─────────────────────────────────────────────────────────────
# 3. SUMMARY
# ─────────────────────────────────────────────────────────────

total_donors = Donor.objects.count()
total_users = User.objects.count()
total_stock = BloodStock.objects.count()

print("\n" + "=" * 60)
print("  ✅ SEED DATA COMPLETE")
print("=" * 60)
print(f"  Total Users:   {total_users}")
print(f"  Total Donors:  {total_donors}")
print(f"  Blood Stock:   {total_stock} entries")
print(f"\n  All donor passwords: Bloodfy@123")
print("=" * 60)
