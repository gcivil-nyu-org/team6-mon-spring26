from django.db import models
from django.conf import settings
from django.utils import timezone


class Expense(models.Model):
    SPLIT_CHOICES = (
        ("EQUAL", "Split Equally"),
        ("PERCENT", "Split by Percentage"),
        ("AMOUNT", "Split by Amount ($)"),
    )

    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses_paid"
    )
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="expenses"
    )
    split_type = models.CharField(max_length=10, choices=SPLIT_CHOICES, default="EQUAL")
    date_spent = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (${self.amount})"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name="splits"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlements_made",
    )

    def __str__(self):
        status = " (Settled)" if self.is_settled else ""
        return (
            f"{self.user.username} owes ${self.amount_owed} "
            f"for {self.expense.title}{status}"
        )
