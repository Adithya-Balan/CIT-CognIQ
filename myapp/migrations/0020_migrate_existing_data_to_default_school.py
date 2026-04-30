"""
Data Migration: Assign all existing data to a "Default School"
- Creates one School named "Default School" with code "DEFAULT"
- Assigns all existing Users, StudentClasses, and Exams to it
"""
from django.db import migrations
from django.utils.text import slugify


def migrate_to_default_school(apps, schema_editor):
    School = apps.get_model('myapp', 'School')
    User = apps.get_model('myapp', 'User')
    StudentClass = apps.get_model('myapp', 'StudentClass')
    Exam = apps.get_model('myapp', 'Exam')

    # Create the Default School
    default_school, created = School.objects.get_or_create(
        code='DEFAULT',
        defaults={
            'name': 'Default School',
            'slug': 'default-school',
            'address': '',
            'phone': '',
            'is_active': True,
        }
    )

    # Assign all non-superuser users to the default school
    User.objects.filter(school__isnull=True, is_superuser=False).update(school=default_school)

    # Assign all StudentClasses to the default school
    StudentClass.objects.filter(school__isnull=True).update(school=default_school)

    # Assign all Exams to the default school
    Exam.objects.filter(school__isnull=True).update(school=default_school)


def reverse_migration(apps, schema_editor):
    """Reverse: Remove the Default School assignment (set back to null)"""
    School = apps.get_model('myapp', 'School')
    User = apps.get_model('myapp', 'User')
    StudentClass = apps.get_model('myapp', 'StudentClass')
    Exam = apps.get_model('myapp', 'Exam')

    try:
        default_school = School.objects.get(code='DEFAULT')
        User.objects.filter(school=default_school).update(school=None)
        StudentClass.objects.filter(school=default_school).update(school=None)
        Exam.objects.filter(school=default_school).update(school=None)
        default_school.delete()
    except School.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0019_add_school_model_and_fk_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_to_default_school, reverse_migration),
    ]
