import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from accounts.models import User

tests = [('kofi','kofi123'),('Felix','felix123'),('admin','admin123')]
for uname, pwd in tests:
    user = User.authenticate(uname, pwd)
    u = User.get_by_username(uname)
    status = "OK" if user else "FAIL"
    active = u.is_active if u else "NOT FOUND"
    hash_preview = u.password_hash[:20] if u and u.password_hash else "EMPTY"
    print(uname + ": " + status + " | is_active=" + str(active) + " | hash=" + hash_preview)
