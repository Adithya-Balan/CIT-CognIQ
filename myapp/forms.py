from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from allauth.account.forms import SignupForm
from .models import User, Exam, Question, Choice


class CustomSignupForm(SignupForm):
    """
    Custom signup form that extends allauth's SignupForm to include role selection.
    Aligned with the Learning-Centric Examination Platform philosophy.
    """
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Username',
            'autocomplete': 'username'
        }),
        help_text='Required. Letters, digits and @/./+/-/_ only.'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Last Name'
        })
    )
    
    # Only allow teacher and student roles - admin is created via Django admin panel
    SIGNUP_ROLE_CHOICES = (
        ('teacher', 'Teacher - I want to create and manage exams'),
        ('student', 'Student - I want to take exams and learn'),
    )
    
    role = forms.ChoiceField(
        choices=SIGNUP_ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
        }),
        help_text='Choose your role on the platform'
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Phone Number (Optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove email field - not used for authentication
        if 'email' in self.fields:
            del self.fields['email']
        
        # Add Tailwind classes to allauth default fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Choose a unique username',
            'autocomplete': 'username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    
    def clean_username(self):
        """
        Validate username with case-insensitive uniqueness check.
        
        The UserManager converts usernames to lowercase before saving,
        so we need to check for case-insensitive uniqueness to prevent
        the "user already exists" error when someone tries to register
        with a different case variant (e.g., "Admin" when "admin" exists).
        """
        from .models import User
        
        username = self.cleaned_data.get('username', '').strip()
        
        if not username:
            raise forms.ValidationError('Username is required.')
        
        # Check for case-insensitive duplicates since UserManager lowercases usernames
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'A user with username "{username}" already exists. '
                'Usernames are case-insensitive.'
            )
        
        return username
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = self.cleaned_data['role']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.save()
        return user


class TeacherSignupForm(UserCreationForm):
    """Dedicated form for teacher registration"""
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        if commit:
            user.save()
        return user


class StudentSignupForm(UserCreationForm):
    """Dedicated form for student registration"""
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
        return user


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
            'title', 'subject', 'description', 
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
        self.fields['pass_percentage'].help_text = 'Minimum percentage required to pass (default: 40%)'


class QuestionForm(forms.ModelForm):
    """
    Question Form - Core Assessment Unit
    
    Philosophy: Each question can optionally teach through explanation
    """
    
    class Meta:
        model = Question
        fields = ['question_text', 'marks', 'explanation', 'order']
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
            'order': forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': '0'
            })
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


# Formsets for managing multiple questions and choices
QuestionFormSet = inlineformset_factory(
    Exam, 
    Question, 
    form=QuestionForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class BaseChoiceFormSet(forms.BaseInlineFormSet):
    """Custom formset to ensure choices are ordered correctly"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure queryset is always ordered by the order field
        if self.instance.pk:
            # Fetch choices and verify order integrity
            choices = list(self.instance.choices.all().order_by('order'))
            
            # Fix any missing or invalid order values
            needs_fix = False
            for i, choice in enumerate(choices):
                if choice.order != i:
                    needs_fix = True
                    choice.order = i
                    choice.save(update_fields=['order'])
            
            # Now set the properly ordered queryset
            self.queryset = self.queryset.order_by('order')
    
    def save(self, commit=True):
        """Override save to ensure order field is maintained"""
        instances = super().save(commit=False)
        
        if commit:
            # Save each instance while preserving/setting proper order
            for i, instance in enumerate(instances):
                # Ensure order is set correctly
                if not hasattr(instance, 'order') or instance.order is None:
                    instance.order = i
                instance.save()
            
            # Handle deletions
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
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email
