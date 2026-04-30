"""
Migration 0021: Make school FK non-nullable on StudentClass and Exam.

User.school remains nullable to accommodate Django superusers who
have no school affiliation. All records were populated by migration 0020.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0020_migrate_existing_data_to_default_school'),
    ]

    operations = [
        # Make StudentClass.school required (all rows already populated)
        migrations.AlterField(
            model_name='studentclass',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='classes',
                to='myapp.school',
                verbose_name='School',
            ),
        ),
        # Make Exam.school required (all rows already populated)
        migrations.AlterField(
            model_name='exam',
            name='school',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='exams',
                to='myapp.school',
                verbose_name='School',
            ),
        ),
    ]
