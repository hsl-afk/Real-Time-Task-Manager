from real_time_task_management.celery import app
from django.core.mail import send_mail
from django.conf import settings
from Users.models import Task, User
from Users.enum import Status

@app.task
def send_assignment_email(task_id, user_id):
    try:
        task = Task.objects.get(id=task_id)
        user = User.objects.get(id=user_id)

        subject = f"New Task Assigned: {task.title}"
        message = f"Hello {user.username},\n\nYou have been assigned a new task: {task.title}.\nPriority: {task.priority}\nDue Date: {task.due_date}\n\nDescription:\n{task.description}\n\nPlease check the task manager for more details."

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
    except (Task.DoesNotExist, User.DoesNotExist):
        pass

@app.task
def send_daily_reminders():
    # Find users with pending/in-progress tasks
    users = User.objects.filter(assigned_tasks__status__in=[Status.PENDING, Status.IN_PROGRESS]).distinct()

    for user in users:
        tasks = user.assigned_tasks.filter(status__in=[Status.PENDING, Status.IN_PROGRESS])

        if tasks.exists():
            subject = "Daily Task Reminder"
            message = f"Hello {user.username},\n\nHere is a reminder of your pending tasks:\n\n"

            for task in tasks:
                message += f"- {task.title} (Due: {task.due_date})\n"

            message += "\nPlease try to complete them on time."

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
                recipient_list=[user.email],
                fail_silently=False,
            )

