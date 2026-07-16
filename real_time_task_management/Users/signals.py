import logging
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Task
from .tasks import send_assignment_email

logger = logging.getLogger(__name__)

@receiver(m2m_changed, sender=Task.assigned_to.through)
def task_assignment_changed(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            try:
                send_assignment_email.delay(instance.id, user_id)
            except Exception as e:
                logger.exception(f"Could not queue assignment email for user {user_id}")
