import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_time_task_management.settings')

# Pass broker and backend directly in the constructor so it is always Redis,
# regardless of when Django settings are lazily loaded.
app = Celery(
    'real_time_task_management',
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
