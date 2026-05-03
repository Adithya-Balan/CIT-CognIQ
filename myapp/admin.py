from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Exam, Question, Choice, ExamAttempt, StudentAnswer, School


# ============================================================================
# SCHOOL ADMIN — Platform superadmin creates schools here
# ============================================================================

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """
    School management — platform superadmin only.
    Schools are created here; each school gets its own admin user.
    """
    list_display = ('name', 'code', 'is_active', 'teacher_count', 'student_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'email')
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('School Identity', {
            'fields': ('name', 'code', 'slug', 'logo')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def teacher_count(self, obj):
        return obj.teacher_count
    teacher_count.short_description = 'Teachers'

    def student_count(self, obj):
        return obj.student_count
    student_count.short_description = 'Students'


# ============================================================================
# USER ADMIN
# ============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin — school-scoped display"""

    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'school', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'school', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role & School', {'fields': ('role', 'school', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'school', 'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('school')


# ============================================================================
# EXAM SYSTEM ADMIN
# ============================================================================

class ChoiceInline(admin.TabularInline):
    """Inline choices for questions"""
    model = Choice
    extra = 4
    max_num = 4
    fields = ('choice_text', 'is_correct', 'order')


class ExamQuestionInline(admin.TabularInline):
    """Inline questions for exams"""
    model = Exam.questions.through
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """Exam Admin — school-scoped"""

    list_display = ('title', 'subject', 'school', 'created_by', 'duration_minutes', 'total_marks', 'created_at')
    list_filter = ('subject', 'school', 'created_at')
    search_fields = ('title', 'subject', 'description', 'created_by__email')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'description')
        }),
        ('Ownership & Tenant', {
            'fields': ('created_by', 'school')
        }),
        ('Time Constraints', {
            'fields': ('duration_minutes',)
        }),
        ('Settings', {
            'fields': ('total_marks',),
            'description': 'Total marks is auto-calculated from question marks'
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'total_marks')
    inlines = [ExamQuestionInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('created_by', 'school')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Question Admin"""

    list_display = ('school', 'subject', 'grade', 'chapter', 'question_text_short', 'marks', 'created_by', 'has_explanation')
    list_filter = ('school', 'subject', 'grade', 'created_by')
    search_fields = ('question_text', 'explanation', 'chapter')
    ordering = ('-created_at',)

    fieldsets = (
        ('Categorization', {
            'fields': ('school', 'created_by', 'subject', 'grade', 'chapter')
        }),
        ('Question Content', {
            'fields': ('question_text', 'marks')
        }),
        ('Explanation (Mandatory)', {
            'fields': ('explanation',),
            'description': 'Assessment must teach! Provide a clear explanation.'
        }),
    )

    inlines = [ChoiceInline]

    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'

    def has_explanation(self, obj):
        return bool(obj.explanation)
    has_explanation.boolean = True
    has_explanation.short_description = 'Has Explanation'


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    """Choice Admin"""

    list_display = ('question', 'choice_text_short', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__subject')
    search_fields = ('choice_text', 'question__question_text')
    ordering = ('question', 'order')

    def choice_text_short(self, obj):
        return obj.choice_text[:40] + '...' if len(obj.choice_text) > 40 else obj.choice_text
    choice_text_short.short_description = 'Choice'


# ============================================================================
# EXAM ATTEMPT ADMIN
# ============================================================================

class StudentAnswerInline(admin.TabularInline):
    """Inline student answers for attempts"""
    model = StudentAnswer
    extra = 0
    fields = ('question', 'selected_choice', 'is_correct')
    readonly_fields = ('is_correct',)
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    """ExamAttempt Admin — school-scoped"""

    list_display = ('student', 'exam', 'score', 'total_marks', 'percentage_display', 'is_completed', 'started_at', 'submitted_at')
    list_filter = ('is_completed', 'exam__subject', 'exam__school', 'started_at')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'exam__title')
    ordering = ('-started_at',)
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Attempt Info', {
            'fields': ('student', 'exam', 'is_completed')
        }),
        ('Performance', {
            'fields': ('score', 'total_marks', 'started_at', 'submitted_at')
        }),
    )

    readonly_fields = ('started_at', 'submitted_at', 'score', 'total_marks')
    inlines = [StudentAnswerInline]

    def percentage_display(self, obj):
        return f"{obj.percentage}%"
    percentage_display.short_description = 'Score %'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'exam', 'exam__school')


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    """StudentAnswer Admin"""

    list_display = ('attempt', 'question_short', 'selected_choice_short', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at')
    search_fields = ('attempt__student__email', 'question__question_text')
    ordering = ('-answered_at',)

    def question_short(self, obj):
        return obj.question.question_text[:40] + '...' if len(obj.question.question_text) > 40 else obj.question.question_text
    question_short.short_description = 'Question'

    def selected_choice_short(self, obj):
        return obj.selected_choice.choice_text[:30] + '...' if len(obj.selected_choice.choice_text) > 30 else obj.selected_choice.choice_text
    selected_choice_short.short_description = 'Selected Answer'
