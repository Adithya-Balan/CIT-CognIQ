from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Exam, Question, Choice, ExamAttempt, StudentAnswer


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin aligned with Learning-Centric philosophy"""
    
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()


# ============================================================================
# EXAM SYSTEM ADMIN
# ============================================================================

class ChoiceInline(admin.TabularInline):
    """Inline choices for questions"""
    model = Choice
    extra = 4
    max_num = 4
    fields = ('choice_text', 'is_correct', 'order')


class QuestionInline(admin.StackedInline):
    """Inline questions for exams"""
    model = Question
    extra = 1
    fields = ('question_text', 'marks', 'explanation', 'order')
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """Exam Admin - Learning-Centric Assessment Management"""
    
    list_display = ('title', 'subject', 'created_by', 'duration_minutes', 'total_marks', 'created_at')
    list_filter = ('subject', 'created_at')
    search_fields = ('title', 'subject', 'description', 'created_by__email')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'description')
        }),
        ('Ownership', {
            'fields': ('created_by',)
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
    inlines = [QuestionInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('created_by')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Question Admin - Core Assessment Units"""
    
    list_display = ('exam', 'question_text_short', 'marks', 'order', 'has_explanation')
    list_filter = ('exam__subject', 'marks', 'exam__created_by')
    search_fields = ('question_text', 'explanation', 'exam__title')
    ordering = ('exam', 'order')
    
    fieldsets = (
        ('Question', {
            'fields': ('exam', 'question_text', 'marks', 'order')
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
    """Choice Admin - Answer Options"""
    
    list_display = ('question', 'choice_text_short', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__exam__subject')
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
    """ExamAttempt Admin - Student Performance Tracking"""
    
    list_display = ('student', 'exam', 'score', 'total_marks', 'percentage_display', 'is_completed', 'started_at', 'submitted_at')
    list_filter = ('is_completed', 'exam__subject', 'started_at')
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
        return qs.select_related('student', 'exam')


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    """StudentAnswer Admin - Individual Response Tracking"""
    
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


