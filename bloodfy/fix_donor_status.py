import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodfy_project.settings')

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from users.models import User
from donors.models import Donor
from django.utils import timezone

print("=" * 60)
print("  🛠  Bloodfy — Donor Status Fixer")
print("=" * 60)

# Get all donors
donors = Donor.objects.all()
total = donors.count()
fixed = 0

print(f"Found {total} donor profiles. Checking statuses...")

for donor in donors:
    user = donor.user
    if user.donor_status != 'DONOR_APPROVED':
        user.donor_status = 'DONOR_APPROVED'
        user.donor_status_updated_at = timezone.now()
        user.save(update_fields=['donor_status', 'donor_status_updated_at'])
        print(f"  ✅ Fixed status for: {user.email}")
        fixed += 1
    else:
        print(f"  ⏭  Already approved: {user.email}")

print("-" * 60)
print(f"✅ DONE! Fixed {fixed} users.")
print("=" * 60)
