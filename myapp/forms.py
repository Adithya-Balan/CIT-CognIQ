from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from .models import User, Exam, Question, Choice, School, generate_username
import re


# ============================================================================
# SCHOOL ADMIN — USER CREATION FORMS
# Note: Public teacher/student self-registration is DISABLED.
# Only school admins (role='admin') can create teacher and student accounts.
# ============================================================================

class TeacherCreationForm(forms.ModelForm):
    """
    Used by school admins to create teacher accounts within their school.
    Username is auto-generated as: <school_code>_tch_<seq_number>
    Password is set explicitly.
    """
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Set a password for this teacher',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        help_text='Minimum 8 characters.'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Email Address (optional)',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Phone Number (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = 'teacher'

    def save(self, school, commit=True):
        """Create teacher user with system-generated username scoped to school."""
        user = super().save(commit=False)
        user.role = 'teacher'
        user.school = school
        # Auto-generate username: e.g., default_tch_004
        seq = school.get_next_teacher_number()
        candidate = generate_username(school.code, 'tch', seq)
        # Ensure global uniqueness (edge case: increment if taken)
        base = candidate
        counter = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}_{counter}"
            counter += 1
        user.username = candidate
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class StudentCreationForm(forms.ModelForm):
    """
    Used by school admins and teachers to create student accounts.
    Username is auto-generated as: <school_code>_stu_<class_prefix>_<seq>
    A custom username suffix can be provided (roll number, etc.).
    """
    identifier = forms.CharField(
        label='Roll / Identifier',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'e.g., 10A-042 or roll number',
        }),
        help_text='Used to build the system username. Only letters, digits and hyphens.'
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Set a password for this student',
            'autocomplete': 'new-password',
        }),
        min_length=6,
        help_text='Minimum 6 characters.'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Email Address (optional)',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Phone Number (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = 'student'

    def clean_identifier(self):
        val = self.cleaned_data['identifier'].strip()
        if not re.match(r'^[a-zA-Z0-9\-]+$', val):
            raise forms.ValidationError('Only letters, digits and hyphens allowed.')
        return val

    def save(self, school, commit=True):
        """Create student user with system-generated username scoped to school."""
        user = super().save(commit=False)
        user.role = 'student'
        user.school = school
        identifier = self.cleaned_data['identifier']
        candidate = generate_username(school.code, 'stu', identifier)
        base = candidate
        counter = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}_{counter}"
            counter += 1
        user.username = candidate
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class SchoolRegistrationForm(forms.Form):
    """
    Public form used to register a new school on the platform.
    Creates both the School record and the initial School Admin user.
    """
    school_name = forms.CharField(
        label='School / Institution Name',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Enter official school name',
        })
    )
    admin_first_name = forms.CharField(
        label='Admin First Name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'First Name',
        })
    )
    admin_last_name = forms.CharField(
        label='Admin Last Name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Last Name',
        })
    )
    admin_email = forms.EmailField(
        label='Admin Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'admin@school.edu',
        })
    )
    admin_phone = forms.CharField(
        label='Admin Phone Number',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': '+1 (555) 000-0000',
        })
    )
    password = forms.CharField(
        label='Admin Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        help_text='Minimum 8 characters.'
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        email = cleaned_data.get('admin_email')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
            
        if email and User.objects.filter(email=email).exists():
            self.add_error('admin_email', "A user with this email already exists.")
            
        return cleaned_data


class BulkStudentUploadForm(forms.Form):
    """
    Used by school admins to bulk-upload students via CSV/Excel.
    """
    file = forms.FileField(
        label='Student Data File',
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'accept': '.csv,.xlsx,.xls',
        }),
        help_text='CSV or Excel file. Columns: first_name, last_name, identifier, password (optional), email (optional)'
    )


class BulkTeacherUploadForm(forms.Form):
    """
    Used by school admins to bulk-upload teachers via CSV/Excel.
    """
    file = forms.FileField(
        label='Teacher Data File',
        widget=forms.ClearableFileInput(attrs={
            'class': 'hidden',
            'accept': '.csv,.xlsx,.xls',
        }),
        help_text='CSV or Excel file. Columns: first_name, last_name, email (optional), phone_number (optional), password (optional)'
    )

# ============================================================================
# EXAM CREATION FORMS
# ============================================================================

class ExamForm(forms.ModelForm):
    """
    Exam Creation Form - Teacher Content Creation
    
    Philosophy: Teachers design time-bound, structured assessments
    """

    class Meta:
        model = Exam
        fields = [
            'title', 'subject', 'grade', 'chapter', 'description',
            'exam_type',
            'duration_minutes',
            'pass_percentage'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., Mathematics Mid-Term Exam'
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'grade': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'chapter': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., Algebra or Mid-Term'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Instructions for students (optional)',
                'rows': 4
            }),
            'exam_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., 60',
                'min': '1'
            }),
            'pass_percentage': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., 40',
                'min': '0',
                'max': '100'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['subject'].required = True
        self.fields['grade'].required = True
        self.fields['chapter'].required = True
        self.fields['pass_percentage'].help_text = 'Minimum percentage required to pass (default: 40%)'


class QuestionForm(forms.ModelForm):
    """
    Question Form - Core Assessment Unit
    
    Philosophy: Each question can optionally teach through explanation
    """

    class Meta:
        model = Question
        fields = ['question_text', 'marks', 'explanation', 'subject', 'grade', 'chapter']
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter your question here...',
                'rows': 3
            }),
            'marks': forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '1',
                'value': '1'
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Optional: Explain why the correct answer is correct to help students learn.',
                'rows': 3
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            }),
            'grade': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., Grade 10'
            }),
            'chapter': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g., Algebra'
            }),
        }


class ChoiceForm(forms.ModelForm):
    """
    Choice Form - Answer Options
    
    Philosophy: 4 choices per question, one correct answer
    """

    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct', 'order']
        widgets = {
            'choice_text': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter choice text'
            }),
            'is_correct': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'
            }),
            'order': forms.HiddenInput()
        }


# QuestionFormSet removed as Question is no longer directly linked to Exam.


class BaseChoiceFormSet(forms.BaseInlineFormSet):
    """Custom formset to ensure choices are ordered correctly"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            choices = list(self.instance.choices.all().order_by('order'))
            needs_fix = False
            for i, choice in enumerate(choices):
                if choice.order != i:
                    needs_fix = True
                    choice.order = i
                    choice.save(update_fields=['order'])
            self.queryset = self.queryset.order_by('order')

    def save(self, commit=True):
        instances = super().save(commit=False)
        if commit:
            for i, instance in enumerate(instances):
                if not hasattr(instance, 'order') or instance.order is None:
                    instance.order = i
                instance.save()
            for obj in self.deleted_objects:
                obj.delete()
        return instances


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    formset=BaseChoiceFormSet,
    extra=0,
    max_num=4,
    can_delete=False,
    min_num=4,
    validate_min=True
)


class ProfileUpdateForm(forms.ModelForm):
    """
    Minimal profile update form for students and teachers.
    Allows editing of basic profile information only.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition',
                'placeholder': 'Enter your email address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition',
                'placeholder': 'Enter your phone number (optional)'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
        }

    def clean_email(self):
        """Ensure email uniqueness while allowing current user's email"""
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

class SchoolSettingsForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'address', 'phone', 'email', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500', 'placeholder': 'School Name'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500', 'rows': 3, 'placeholder': 'School Address'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500', 'placeholder': 'Contact Email'}),
            'logo': forms.FileInput(attrs={'class': 'w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500'}),
        }
