from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
import math
import re


# ============================================================================
# USERNAME GENERATION UTILITY
# ============================================================================

def generate_username(school_code, role_prefix, identifier):
    """
    Generate a structured, globally-unique username.
    Format: <school_code>_<role_prefix>_<identifier>
    Example: SPHS_TCH_001  or  SPHS_STU_10A_042
    All lowercase, no spaces.
    """
    raw = f"{school_code}_{role_prefix}_{identifier}"
    # Remove special characters except underscore, lowercase
    username = re.sub(r'[^a-z0-9_]', '', raw.lower())
    return username


# ============================================================================
# SCHOOL MODEL (Tenant Root)
# ============================================================================

class School(models.Model):
    """
    School Model — Multi-Tenant Root
    
    Every piece of data in the system (users, exams, classes, attempts)
    is scoped to exactly one school. Schools are created by platform
    superadmins only — there is no public school self-registration.
    """
    
    name = models.CharField(
        max_length=200,
        verbose_name='School Name',
        help_text='Full official name of the school'
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='School Code',
        help_text='Short unique code used in username generation (e.g., SPHS, STMH). Uppercase letters only.'
    )
    
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        verbose_name='URL Slug'
    )
    
    address = models.TextField(
        blank=True,
        verbose_name='Address'
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Phone Number'
    )
    
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='School Email'
    )
    
    logo = models.ImageField(
        upload_to='school_logos/',
        blank=True,
        null=True,
        verbose_name='School Logo'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Inactive schools are locked — no logins allowed'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.name)}-{self.code.lower()}"
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)
    
    @property
    def teacher_count(self):
        return self.users.filter(role='teacher', is_active=True).count()
    
    @property
    def student_count(self):
        return self.users.filter(role='student', is_active=True).count()
    
    @property
    def class_count(self):
        return self.classes.filter(is_active=True).count()
    
    @property
    def exam_count(self):
        return self.exams.count()
    
    def get_next_teacher_number(self):
        """Returns next sequential teacher number within this school"""
        count = self.users.filter(role='teacher').count()
        return str(count + 1).zfill(3)
    
    def get_next_student_number_for_class(self, class_name_prefix):
        """Returns next sequential student number for a given class prefix"""
        prefix_clean = re.sub(r'[^a-z0-9]', '', class_name_prefix.lower())[:4]
        existing = self.users.filter(role='student', username__contains=f'_{prefix_clean}_').count()
        return str(existing + 1).zfill(3)

# Custom User Manager for Username-Based Authentication
class UserManager(BaseUserManager):
    """
    Custom user manager where username is the unique identifier
    for authentication.
    """
    
    def create_user(self, username, first_name, last_name, role, email=None, password=None, school=None, **extra_fields):
        """
        Create and save a regular user with the given username, name, and role.
        Email is optional. School is optional (can be assigned later for migration compat).
        """
        if not username:
            raise ValueError('The Username field must be set')
        if not first_name:
            raise ValueError('The First Name field must be set')
        if not last_name:
            raise ValueError('The Last Name field must be set')
        if not role:
            raise ValueError('The Role field must be set')
        
        username = username.lower().strip()
        if email:
            email = self.normalize_email(email)
        
        user = self.model(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            school=school,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, first_name, last_name, role='admin', email=None, password=None, **extra_fields):
        """
        Create and save a superuser with the given username, name, and password.
        Email is optional. Superusers are automatically assigned the 'admin' role.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # Force role to 'admin' for superusers
        role = 'admin'
        
        return self.create_user(username, first_name, last_name, role, email, password, **extra_fields)

# Custom User Model with Role-Based System
class User(AbstractUser):
    """
    Custom User model aligned with the Learning-Centric Examination Platform philosophy.
    
    Role choices are generic to support multiple business contexts:
    - TEACHER: Content creators, evaluators, performance analysts
    - STUDENT: Test takers, active learners, self-evaluators
    - ADMIN: System governance and structure management
    """
    
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('admin', 'Admin'),
    )
    
    # Core Fields
    username = models.CharField(max_length=150, unique=True, verbose_name='Username')
    email = models.EmailField(unique=True, blank=True, null=True, verbose_name='Email Address')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name='User Role')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='Phone Number')
    
    # School FK — every non-superuser must belong to exactly one school
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,       # nullable for migration: existing records + Django superusers
        blank=True,
        verbose_name='School'
    )
    
    # Username is primary identifier for authentication
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']
    
    # Use custom manager for username-based authentication
    objects = UserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def clean(self):
        """Validate that role is provided"""
        if not self.role:
            raise ValidationError({'role': 'User role is required'})
    
    @property
    def is_teacher(self):
        """Check if user is a teacher"""
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        """Check if user is a student"""
        return self.role == 'student'
    
    @property
    def is_admin_user(self):
        """Check if user is an admin (not Django superuser)"""
        return self.role == 'admin'
    
    @property
    def is_school_admin(self):
        """Check if user is a school-level admin (role='admin' and has a school)"""
        return self.role == 'admin' and self.school_id is not None
    
    def get_school(self):
        """Safe accessor for school — returns None for superusers"""
        return self.school


# ============================================================================
# CLASS/GROUP MANAGEMENT
# ============================================================================

class StudentClass(models.Model):
    """
    Student Class Model - Organize students into cohorts/batches
    
    Philosophy:
    - Group students by grade, year, section
    - Enable batch-wise exam assignment
    - Facilitate class-level analytics
    - Support exam reuse across batches
    """
    
    name = models.CharField(
        max_length=100, 
        verbose_name='Class Name',
        help_text='e.g., Grade 10 - Section A (2025)'
    )
    
    description = models.TextField(
        blank=True, 
        verbose_name='Description',
        help_text='Additional details about this class'
    )
    
    year = models.IntegerField(
        verbose_name='Academic Year',
        help_text='Year this class is active (e.g., 2025)'
    )
    
    GRADE_CHOICES = [
        ('Grade 1', 'Grade 1'),
        ('Grade 2', 'Grade 2'),
        ('Grade 3', 'Grade 3'),
        ('Grade 4', 'Grade 4'),
        ('Grade 5', 'Grade 5'),
        ('Grade 6', 'Grade 6'),
        ('Grade 7', 'Grade 7'),
        ('Grade 8', 'Grade 8'),
        ('Grade 9', 'Grade 9'),
        ('Grade 10', 'Grade 10'),
        ('Grade 11', 'Grade 11'),
        ('Grade 12', 'Grade 12'),
    ]
    
    grade = models.CharField(
        max_length=20,
        choices=GRADE_CHOICES,
        verbose_name='Grade',
        help_text='Select the grade level for this class',
        default='Grade 10'
    )
    
    # School FK — classes are strictly scoped to one school
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name='School'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_classes',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Created By'
    )
    
    students = models.ManyToManyField(
        User,
        related_name='student_classes',
        limit_choices_to={'role': 'student'},
        blank=True,
        verbose_name='Students'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status',
        help_text='Inactive classes are archived but not deleted'
    )
    
    # Enrollment settings
    enrollment_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Enrollment Code',
        help_text='Unique code students can use to self-enroll'
    )
    
    allow_self_enrollment = models.BooleanField(
        default=False,
        verbose_name='Allow Self-Enrollment',
        help_text='Students can join using the enrollment code'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Student Class'
        verbose_name_plural = 'Student Classes'
        ordering = ['-year', '-created_at']
        unique_together = ['name', 'year', 'created_by', 'school']
    
    def __str__(self):
        return f"{self.name} ({self.year})"
    
    @property
    def student_count(self):
        """Get number of students in this class"""
        return self.students.count()
    
    @property
    def assigned_exam_count(self):
        """Get number of exams assigned to this class"""
        return self.assigned_exams.count()
    
    def generate_enrollment_code(self):
        """Generate a unique 8-character enrollment code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not StudentClass.objects.filter(enrollment_code=code).exists():
                self.enrollment_code = code
                self.save(update_fields=['enrollment_code'])
                return code
    
    def enable_self_enrollment(self):
        """Enable self-enrollment and generate code if needed"""
        if not self.enrollment_code:
            self.generate_enrollment_code()
        self.allow_self_enrollment = True
        self.save(update_fields=['allow_self_enrollment'])
    
    def disable_self_enrollment(self):
        """Disable self-enrollment"""
        self.allow_self_enrollment = False
        self.save(update_fields=['allow_self_enrollment'])


# ============================================================================
# EXAMINATION SYSTEM MODELS
# ============================================================================

class Exam(models.Model):
    """
    Exam Model - Learning-Centric Assessment Event
    
    Philosophy:
    - Time-bound controlled assessment
    - Teacher-owned content creation
    - Objective MCQ-based evaluation
    - Immediately reviewable after submission
    """
    
    # Subject Choices - Fixed list to avoid typos and ensure consistency
    SUBJECT_CHOICES = (
        ('English', 'English'),
        ('Social Science', 'Social Science'),
        ('Science', 'Science'),
        ('Mathematics', 'Mathematics'),
        ('தமிழ்', 'தமிழ்'),
    )
    
    # Exam Type Choices
    EXAM_TYPE_CHOICES = (
        ('practice_test', 'Practice & Test'),
        ('test', 'Test'),
    )
    
    # Basic Information
    title = models.CharField(max_length=200, verbose_name='Exam Title')
    subject = models.CharField(
        max_length=100, 
        choices=SUBJECT_CHOICES,
        verbose_name='Subject',
        help_text='Select subject from predefined list'
    )
    description = models.TextField(blank=True, verbose_name='Description/Instructions')
    
    GRADE_CHOICES = [(str(i), f"Grade {i}") for i in range(1, 13)]
    
    grade = models.CharField(
        max_length=50, 
        choices=GRADE_CHOICES,
        verbose_name='Grade/Standard'
    )
    chapter = models.CharField(max_length=200, verbose_name='Chapter/Topic/Category')
    
    # Exam Type
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='practice_test',
        verbose_name='Exam Type',
        help_text='Practice & Test: Unlimited practice + One test attempt | Test: Single attempt only'
    )
    
    is_cloned = models.BooleanField(
        default=False,
        verbose_name='Is Cloned Copy',
        help_text='Indicates if this exam is a duplicate working copy of an original exam from the bank.'
    )
    
    # School FK — exams are strictly scoped to one school
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name='School'
    )
    
    # Teacher Ownership
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_exams',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Created By'
    )
    
    # Time Constraints
    duration_minutes = models.PositiveIntegerField(
        verbose_name='Duration (minutes)',
        help_text='Total time allowed for this exam'
    )
    
    # Class Assignment
    assigned_classes = models.ManyToManyField(
        StudentClass,
        related_name='assigned_exams',
        blank=True,
        verbose_name='Assigned Classes',
        help_text='Classes that can take this exam'
    )
    
    # Shared Question Bank Link
    questions = models.ManyToManyField(
        'Question',
        through='ExamQuestion',
        related_name='exams',
        blank=True,
        verbose_name='Questions'
    )
    
    # Metadata
    total_marks = models.PositiveIntegerField(
        default=0, 
        verbose_name='Total Marks',
        editable=False,
        help_text='Auto-calculated from question marks'
    )
    pass_percentage = models.PositiveIntegerField(
        default=40,
        verbose_name='Pass Percentage',
        help_text='Minimum percentage required to pass (e.g., 40 for 40%)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.subject}"
    
    def clean(self):
        """Validate exam constraints"""
        if self.duration_minutes and self.duration_minutes < 1:
            raise ValidationError({'duration_minutes': 'Duration must be at least 1 minute'})
    
    @property
    def question_count(self):
        """Get total number of questions"""
        return self.questions.count()
    
    def update_total_marks(self):
        """Recalculate and save total marks from all questions"""
        from django.db.models import Sum
        total = self.questions.aggregate(Sum('marks'))['marks__sum'] or 0
        self.total_marks = total
        self.save(update_fields=['total_marks'])
    
    def get_absolute_url(self):
        return reverse('exam_detail', kwargs={'pk': self.pk})


class Question(models.Model):
    """
    Question Model - Core Assessment Unit (Shared Question Bank)
    
    Philosophy:
    - Questions belong to a School and are created by a Teacher.
    - They can be reused across multiple exams.
    - Each question has conceptual layers: problem definition, choices, correct answer, explanation.
    """
    
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='School'
    )
    
    created_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='created_questions',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Created By'
    )
    
    # Categorization
    subject = models.CharField(
        max_length=100, 
        choices=Exam.SUBJECT_CHOICES,
        verbose_name='Subject'
    )
    grade = models.CharField(max_length=50, blank=True, verbose_name='Grade/Standard')
    chapter = models.CharField(max_length=200, blank=True, verbose_name='Chapter/Topic')
    
    # Question Content
    question_text = models.TextField(verbose_name='Question')
    marks = models.PositiveIntegerField(default=1, verbose_name='Marks')
    
    # Optional Explanation (Learning Enhancement)
    explanation = models.TextField(
        blank=True,
        null=True,
        verbose_name='Explanation',
        help_text='Optional: Explain why the correct answer is correct to help students learn.'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.subject} - {self.question_text[:50]}..."
    
    @property
    def correct_choice(self):
        """Get the correct choice"""
        return self.choices.filter(is_correct=True).first()


class ExamQuestion(models.Model):
    """
    Junction table for Exam and Question to maintain order.
    """
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, verbose_name='Order')

    class Meta:
        ordering = ['exam', 'order']
        unique_together = ['exam', 'question']

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"


class Choice(models.Model):
    """
    Choice Model - Answer Options
    
    Philosophy:
    - 4 choices per question (standard MCQ format)
    - Only one correct answer
    - Choices are decision paths for students
    """
    
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='choices',
        verbose_name='Question'
    )
    
    choice_text = models.CharField(max_length=500, verbose_name='Choice Text')
    is_correct = models.BooleanField(default=False, verbose_name='Correct Answer')
    order = models.PositiveIntegerField(default=0, verbose_name='Order')
    
    class Meta:
        verbose_name = 'Choice'
        verbose_name_plural = 'Choices'
        ordering = ['question', 'order']
        
    def __str__(self):
        correct = "✓" if self.is_correct else "✗"
        return f"{correct} {self.choice_text[:30]}..."
    
    def clean(self):
        """Validate choice text"""
        if not self.choice_text or len(self.choice_text.strip()) < 1:
            raise ValidationError({'choice_text': 'Choice text cannot be empty'})


# ============================================================================
# EXAM ATTEMPT MODELS (Student Exam Taking)
# ============================================================================

class ExamAttempt(models.Model):
    """
    ExamAttempt Model - Student's Exam Session
    
    Philosophy:
    - One attempt per student per exam (by default)
    - Complete audit trail: start time, end time, score
    - Enables performance analytics and learning insights
    """
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_attempts',
        limit_choices_to={'role': 'student'},
        verbose_name='Student'
    )
    
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='Exam'
    )
    
    student_class = models.ForeignKey(
        'StudentClass',
        on_delete=models.CASCADE,
        related_name='exam_attempts',
        verbose_name='Class',
        null=True,  # Temporarily nullable for migration
        help_text='The class context in which this exam was taken'
    )
    
    # Attempt Mode (for practice_test exam type)
    ATTEMPT_MODE_CHOICES = (
        ('practice', 'Practice'),
        ('test', 'Test'),
    )
    
    attempt_mode = models.CharField(
        max_length=20,
        choices=ATTEMPT_MODE_CHOICES,
        default='test',
        verbose_name='Attempt Mode',
        help_text='Practice attempts are for learning; Test attempts count for leaderboard'
    )
    
    # Attempt Metadata
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Started At')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='Submitted At')
    
    # Performance Data
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Score'
    )
    
    total_marks = models.PositiveIntegerField(default=0, verbose_name='Total Marks')
    
    # Completion Status
    is_completed = models.BooleanField(default=False, verbose_name='Completed')
    
    # Proctoring Violation Tracking
    has_violation = models.BooleanField(default=False, verbose_name='Violation Detected')
    violation_reason = models.TextField(blank=True, null=True, verbose_name='Violation Reason')
    
    # Question Order (for preserving randomization)
    question_order = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name='Question Order',
        help_text='Stores the randomized question IDs in order for this attempt'
    )
    
    class Meta:
        verbose_name = 'Exam Attempt'
        verbose_name_plural = 'Exam Attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', 'exam', 'student_class']),
            models.Index(fields=['student_class', 'exam', '-started_at']),
        ]
    
    def __str__(self):
        class_name = self.student_class.name if self.student_class else "No Class"
        return f"{self.student.get_full_name()} - {self.exam.title} - {class_name} ({self.percentage}%)"
    
    @property
    def percentage(self):
        """Calculate percentage score"""
        if self.total_marks == 0:
            return 0
        return round((self.score / self.total_marks) * 100, 2)
    
    @property
    def time_taken(self):
        """Calculate time taken for the attempt (always rounded up)"""
        if self.submitted_at:
            delta = self.submitted_at - self.started_at
            return math.ceil(delta.total_seconds() / 60)  # Return minutes (ceiling)
        return 0
    
    @property
    def duration_taken(self):
        """Calculate time taken for the attempt"""
        return self.time_taken
    
    @property
    def correct_count(self):
        """Count of correctly answered questions"""
        return self.answers.filter(is_correct=True).count()
    
    @property
    def total_questions(self):
        """Total number of questions in the exam"""
        return self.exam.questions.count()
    
    @property
    def passed(self):
        """Check if student passed based on exam's pass percentage"""
        return self.percentage >= self.exam.pass_percentage
    
    def calculate_score(self):
        """Calculate total score based on correct answers"""
        total = 0
        for answer in self.answers.all():
            if answer.is_correct:
                total += answer.question.marks
        self.score = total
        self.save()
        return total


class StudentAnswer(models.Model):
    """
    StudentAnswer Model - Individual Question Response
    
    Philosophy:
    - Captures student's choice for each question
    - Enables detailed performance analysis per question
    - Supports learning analytics and difficulty assessment
    """
    
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='Exam Attempt'
    )
    
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name='Question'
    )
    
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name='selected_by',
        verbose_name='Selected Choice'
    )
    
    is_correct = models.BooleanField(default=False, verbose_name='Is Correct')
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name='Answered At')
    
    class Meta:
        verbose_name = 'Student Answer'
        verbose_name_plural = 'Student Answers'
        unique_together = ['attempt', 'question']  # One answer per question per attempt
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.attempt.student.get_full_name()} - Q_ID:{self.question.pk}"
    
    def save(self, *args, **kwargs):
        """Auto-set is_correct based on selected choice"""
        self.is_correct = self.selected_choice.is_correct
        super().save(*args, **kwargs)

