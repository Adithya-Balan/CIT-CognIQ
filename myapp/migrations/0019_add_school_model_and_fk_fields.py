from django.db import migrations, models
import django.db.models.deletion
import django.utils.text


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0018_examattempt_attempt_mode_alter_exam_exam_type'),
    ]

    operations = [
        # 1. Create School model
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Full official name of the school', max_length=200, verbose_name='School Name')),
                ('code', models.CharField(help_text='Short unique code used in username generation (e.g., SPHS, STMH). Uppercase letters only.', max_length=20, unique=True, verbose_name='School Code')),
                ('slug', models.SlugField(blank=True, max_length=220, unique=True, verbose_name='URL Slug')),
                ('address', models.TextField(blank=True, verbose_name='Address')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='Phone Number')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='School Email')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='school_logos/', verbose_name='School Logo')),
                ('is_active', models.BooleanField(default=True, help_text='Inactive schools are locked — no logins allowed', verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'School',
                'verbose_name_plural': 'Schools',
                'ordering': ['name'],
            },
        ),

        # 2. Add nullable school FK to User
        migrations.AddField(
            model_name='user',
            name='school',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users',
                to='myapp.school',
                verbose_name='School',
            ),
        ),

        # 3. Add nullable school FK to StudentClass
        migrations.AddField(
            model_name='studentclass',
            name='school',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='classes',
                to='myapp.school',
                verbose_name='School',
            ),
        ),

        # 4. Add nullable school FK to Exam
        migrations.AddField(
            model_name='exam',
            name='school',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='exams',
                to='myapp.school',
                verbose_name='School',
            ),
        ),

        # 5. Update StudentClass unique_together to be school-scoped
        migrations.AlterUniqueTogether(
            name='studentclass',
            unique_together={('name', 'year', 'created_by', 'school')},
        ),
    ]
