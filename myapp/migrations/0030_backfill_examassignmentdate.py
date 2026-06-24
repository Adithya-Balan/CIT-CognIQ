"""
Data migration: Backfill ExamAssignmentDate records for all existing
exam-to-class assignments. Uses the exam's created_at as a fallback
since the actual assignment timestamp wasn't previously tracked.
"""

from django.db import migrations


def backfill_assignment_dates(apps, schema_editor):
    Exam = apps.get_model('myapp', 'Exam')
    ExamAssignmentDate = apps.get_model('myapp', 'ExamAssignmentDate')

    # Iterate over all exams that have assigned classes
    for exam in Exam.objects.prefetch_related('assigned_classes').all():
        for student_class in exam.assigned_classes.all():
            ExamAssignmentDate.objects.get_or_create(
                exam=exam,
                student_class=student_class,
                defaults={'assigned_at': exam.created_at}
            )


def reverse_backfill(apps, schema_editor):
    ExamAssignmentDate = apps.get_model('myapp', 'ExamAssignmentDate')
    ExamAssignmentDate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0029_examassignmentdate'),
    ]

    operations = [
        migrations.RunPython(backfill_assignment_dates, reverse_backfill),
    ]
