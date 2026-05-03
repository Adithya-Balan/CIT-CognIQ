from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Exam, StudentClass
from django.db import transaction
from django.core.paginator import Paginator

@login_required
def exam_bank(request):
    """View and filter the school's shared exam bank."""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied. Teachers only.')
        return redirect('dashboard')
        
    exams = Exam.objects.filter(school=request.user.school).select_related('created_by').prefetch_related('questions')
    
    # Filtering
    subject = request.GET.get('subject')
    grade = request.GET.get('grade')
    chapter = request.GET.get('chapter')
    search = request.GET.get('search')
    
    if subject:
        exams = exams.filter(subject=subject)
    if grade:
        exams = exams.filter(grade__icontains=grade)
    if chapter:
        exams = exams.filter(chapter__icontains=chapter)
    if search:
        exams = exams.filter(title__icontains=search)
        
    # Group by subject and page them
    paginator = Paginator(exams.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filters
    subjects = Exam.objects.filter(school=request.user.school).values_list('subject', flat=True).distinct()
    grades = Exam.objects.filter(school=request.user.school).exclude(grade='').values_list('grade', flat=True).distinct()
    chapters = Exam.objects.filter(school=request.user.school).exclude(chapter='').values_list('chapter', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'subjects': subjects,
        'grades': grades,
        'chapters': chapters,
        'current_subject': subject,
        'current_grade': grade,
        'current_chapter': chapter,
        'search_query': search,
        'page_title': 'Shared Exam Bank'
    }
    return render(request, 'exams/exam_bank.html', context)

@login_required
def assign_exam_from_bank(request, exam_pk):
    """Assign an exam from the bank to one or more of the teacher's classes"""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
        
    exam = get_object_or_404(Exam, pk=exam_pk, school=request.user.school)
    
    if request.method == 'POST':
        class_ids = request.POST.getlist('classes')
        if not class_ids:
            messages.warning(request, 'No classes selected.')
            return redirect('assign_exam_from_bank', exam_pk=exam.pk)
            
        classes = StudentClass.objects.filter(id__in=class_ids, created_by=request.user)
        assigned_count = 0
        for student_class in classes:
            if not exam.assigned_classes.filter(id=student_class.id).exists():
                exam.assigned_classes.add(student_class)
                assigned_count += 1
                
        if assigned_count > 0:
            messages.success(request, f'Exam "{exam.title}" assigned to {assigned_count} class(es).')
        else:
            messages.info(request, 'Exam is already assigned to the selected classes.')
            
        return redirect('exam_bank')
        
    # GET request - show form to pick classes
    teacher_classes = StudentClass.objects.filter(created_by=request.user).order_by('name')
    already_assigned = exam.assigned_classes.filter(created_by=request.user).values_list('id', flat=True)
    
    context = {
        'exam': exam,
        'teacher_classes': teacher_classes,
        'already_assigned': list(already_assigned),
        'page_title': f'Assign Exam: {exam.title}'
    }
    return render(request, 'exams/assign_exam_from_bank.html', context)

@login_required
def clone_exam(request, exam_pk):
    """Duplicate an exam so the teacher becomes the creator and can edit it"""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
        
    original_exam = get_object_or_404(Exam, pk=exam_pk, school=request.user.school)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Clone exam
                new_exam = Exam.objects.create(
                    title=f"Copy of {original_exam.title}",
                    subject=original_exam.subject,
                    description=original_exam.description,
                    grade=original_exam.grade,
                    chapter=original_exam.chapter,
                    exam_type=original_exam.exam_type,
                    school=request.user.school,
                    created_by=request.user,
                    duration_minutes=original_exam.duration_minutes,
                    pass_percentage=original_exam.pass_percentage,
                    total_marks=original_exam.total_marks
                )
                
                # Clone exam-question relationships
                from .models import ExamQuestion
                original_eqs = ExamQuestion.objects.filter(exam=original_exam)
                for eq in original_eqs:
                    ExamQuestion.objects.create(
                        exam=new_exam,
                        question=eq.question,
                        order=eq.order
                    )
                    
            messages.success(request, f'Exam duplicated successfully. You can now edit your copy.')
            return redirect('exam_detail', pk=new_exam.pk)
        except Exception as e:
            messages.error(request, f'Error duplicating exam: {e}')
            return redirect('exam_bank')
            
    return redirect('exam_bank')
