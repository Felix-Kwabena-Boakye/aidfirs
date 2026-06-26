import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from accounts.models import User

# Reset kofi password
kofi = User.get_by_username('kofi')
if kofi:
    kofi.password_hash = User.hash_password('kofi123')
    kofi.save()
    test = User.authenticate('kofi', 'kofi123')
    print("kofi reset: " + ("OK" if test else "FAIL"))

# Reset Felix password
felix = User.get_by_username('Felix')
if felix:
    felix.password_hash = User.hash_password('felix123')
    felix.save()
    test = User.authenticate('Felix', 'felix123')
    print("Felix reset: " + ("OK" if test else "FAIL"))

# Print current users.json content for kofi
import json
with open('users.json') as f:
    users = json.load(f)
for u in users:
    print(u['username'] + " hash=" + str(u.get('password_hash',''))[:30])
