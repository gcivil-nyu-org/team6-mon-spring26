from django.db.models.signals import post_save
from django.dispatch import receiver
from chores.models import ChoreCompletion
from .models import ActivityLog

@receiver(post_save, sender=ChoreCompletion)
def log_chore_completion(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.completed_by,
            household=instance.chore.household,
            activity_type='CHORE_COMPLETED',
            description=f"completed the chore: {instance.chore.description}"
        )