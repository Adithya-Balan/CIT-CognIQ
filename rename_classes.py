import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CognIQ.settings')
django.setup()

from myapp.models import StudentClass

classes = StudentClass.objects.all()
for c in classes:
    # Remove "- Year X" from name
    new_name = re.sub(r'\s*-\s*Year\s*\d+', ' - Section A', c.name)
    if new_name != c.name:
        c.name = new_name
        c.save()

print("Classes renamed successfully.")
