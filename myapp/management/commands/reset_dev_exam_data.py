from django.core.management.base import BaseCommand
from django.db import transaction
from myapp.models import ExamAttempt, StudentAnswer, User


class Command(BaseCommand):
    help = 'Safely reset all development exam attempts and student answers for local testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset attempts for all students instead of only dev students (student1, student2, student3)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('--- Resetting Development Exam Attempts ---'))

        reset_all = options.get('all', False)

        with transaction.atomic():
            if reset_all:
                target_users = User.objects.filter(role='student')
            else:
                target_users = User.objects.filter(username__in=['student1', 'student2', 'student3', 'student'])

            attempts = ExamAttempt.objects.filter(student__in=target_users)
            attempt_count = attempts.count()
            answers = StudentAnswer.objects.filter(attempt__in=attempts)
            answer_count = answers.count()

            answers.delete()
            attempts.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {attempt_count} exam attempts and {answer_count} student answers.\n'
                f'Dev students ({", ".join(target_users.values_list("username", flat=True))}) '
                f'can now take all practice and test attempts afresh.'
            )
        )
