from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    ACTION_CHOICES = (
        ("EXPENSE_ADDED", "Expense Added"),
        ("PAYMENT_SETTLED", "Payment Settled"),
        ("HOUSEHOLD_JOINED", "Joined Household"),
        ("MEMBER_REMOVED", "Member Removed"),
        ("EXPENSE_DELETED", "Expense Deleted"),
        ("EXPENSE_EDITED", "Expense Edited"),
        ("CHORE_CREATED", "Chore Created"),
        ("CHORE_UPDATED", "Chore Updated"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities"
    )
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="activities"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"