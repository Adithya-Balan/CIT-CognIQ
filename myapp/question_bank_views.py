from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Question, Exam, ExamQuestion
from .forms import QuestionForm, ChoiceFormSet
from django.db import transaction
from django.core.paginator import Paginator

@login_required
def question_bank(request):
    """View and filter the school's shared question bank."""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied. Teachers only.')
        return redirect('dashboard')
        
    questions = Question.objects.filter(school=request.user.school).select_related('created_by').prefetch_related('choices')
    
    # Filtering
    subject = request.GET.get('subject')
    grade = request.GET.get('grade')
    chapter = request.GET.get('chapter')
    search = request.GET.get('search')
    
    if subject:
        questions = questions.filter(subject=subject)
    if grade:
        questions = questions.filter(grade__icontains=grade)
    if chapter:
        questions = questions.filter(chapter__icontains=chapter)
    if search:
        questions = questions.filter(question_text__icontains=search)
        
    paginator = Paginator(questions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filters
    subjects = Question.objects.filter(school=request.user.school).values_list('subject', flat=True).distinct()
    grades = Question.objects.filter(school=request.user.school).exclude(grade='').values_list('grade', flat=True).distinct()
    chapters = Question.objects.filter(school=request.user.school).exclude(chapter='').values_list('chapter', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'subjects': subjects,
        'grades': grades,
        'chapters': chapters,
        'current_subject': subject,
        'current_grade': grade,
        'current_chapter': chapter,
        'search_query': search,
        'page_title': 'Shared Question Bank'
    }
    return render(request, 'exams/question_bank.html', context)

@login_required
def question_create(request):
    if not request.user.is_teacher:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
        
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        choice_formset = ChoiceFormSet(request.POST)
        
        if question_form.is_valid() and choice_formset.is_valid():
            try:
                with transaction.atomic():
                    question = question_form.save(commit=False)
                    question.school = request.user.school
                    question.created_by = request.user
                    question.save()
                    
                    choice_formset.instance = question
                    choices = choice_formset.save(commit=False)
                    
                    correct_count = 0
                    for idx, choice in enumerate(choices):
                        choice.order = idx
                        if choice.is_correct:
                            correct_count += 1
                        choice.save()
                        
                    if correct_count != 1:
                        raise ValueError('Must have exactly one correct choice.')
                        
                    messages.success(request, 'Question added to bank successfully!')
                    return redirect('question_bank')
            except Exception as e:
                messages.error(request, f'Error: {e}')
    else:
        question_form = QuestionForm()
        choice_formset = ChoiceFormSet()
        
    context = {
        'question_form': question_form,
        'choice_formset': choice_formset,
        'page_title': 'Create Question'
    }
    return render(request, 'exams/question_bank_form.html', context)

@login_required
def exam_add_from_bank(request, exam_pk):
    """View to select questions from the bank and add them to an exam."""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
        
    exam = get_object_or_404(Exam, pk=exam_pk, created_by=request.user)
    
    if request.method == 'POST':
        question_ids = request.POST.getlist('questions')
        if not question_ids:
            messages.warning(request, 'No questions selected.')
            return redirect('exam_add_from_bank', exam_pk=exam.pk)
            
        base_order = exam.questions.count()
        added = 0
        for q_id in question_ids:
            # Check if not already in exam
            if not ExamQuestion.objects.filter(exam=exam, question_id=q_id).exists():
                ExamQuestion.objects.create(exam=exam, question_id=q_id, order=base_order + added)
                added += 1
                
        if added > 0:
            exam.update_total_marks()
            messages.success(request, f'{added} questions added to exam.')
        else:
            messages.info(request, 'All selected questions are already in this exam.')
            
        return redirect('exam_detail', pk=exam.pk)
        
    # GET request - show question bank
    existing_q_ids = exam.questions.values_list('id', flat=True)
    questions = Question.objects.filter(school=request.user.school).exclude(id__in=existing_q_ids)
    
    # Basic filtering similar to question bank
    subject = request.GET.get('subject', exam.subject)
    if subject:
        questions = questions.filter(subject=subject)
        
    search = request.GET.get('search')
    if search:
        questions = questions.filter(question_text__icontains=search)
        
    paginator = Paginator(questions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'exam': exam,
        'page_obj': page_obj,
        'current_subject': subject,
        'search_query': search,
        'page_title': f'Add from Bank: {exam.title}'
    }
    return render(request, 'exams/exam_add_from_bank.html', context)
