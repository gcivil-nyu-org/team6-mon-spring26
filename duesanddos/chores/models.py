from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Chore(models.Model):
    REPEAT_TYPE_CHOICES = (
        ("ONE_TIME", "One-time"),
        ("DAILY", "Recurring - Daily"),
        ("WEEKLY", "Recurring - Weekly"),
    )

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="chores",
    )
    description = models.CharField(max_length=255)

    repeat_type = models.CharField(
        max_length=10,
        choices=REPEAT_TYPE_CHOICES,
        default="ONE_TIME",
    )

    has_due_date = models.BooleanField(default=False)

    # One-time chores use due_date (+ optional due_time)
    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)

    # Recurring chores use start_date / end_date
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)

    repeat_monday = models.BooleanField(default=False)
    repeat_tuesday = models.BooleanField(default=False)
    repeat_wednesday = models.BooleanField(default=False)
    repeat_thursday = models.BooleanField(default=False)
    repeat_friday = models.BooleanField(default=False)
    repeat_saturday = models.BooleanField(default=False)
    repeat_sunday = models.BooleanField(default=False)

    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_chores",
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_chores",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["description"]

    def __str__(self):
        return self.description

    def clean(self):
        if self.repeat_type == "ONE_TIME":
            if self.has_due_date and not self.due_date:
                raise ValidationError("One-time chores with due dates must include a due date.")

        if self.repeat_type in ["DAILY", "WEEKLY"] and not self.start_date:
            raise ValidationError("Recurring chores must include a start date.")

        if self.repeat_type == "WEEKLY":
            if not any(
                [
                    self.repeat_monday,
                    self.repeat_tuesday,
                    self.repeat_wednesday,
                    self.repeat_thursday,
                    self.repeat_friday,
                    self.repeat_saturday,
                    self.repeat_sunday,
                ]
            ):
                raise ValidationError("Weekly chores must repeat on at least one weekday.")

        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

    @property
    def weekly_days(self):
        return {
            0: self.repeat_monday,
            1: self.repeat_tuesday,
            2: self.repeat_wednesday,
            3: self.repeat_thursday,
            4: self.repeat_friday,
            5: self.repeat_saturday,
            6: self.repeat_sunday,
        }

    def occurs_on(self, target_date):
        if not self.is_active:
            return False

        if self.repeat_type == "ONE_TIME":
            if not self.has_due_date or not self.due_date:
                return False
            return self.due_date == target_date

        if target_date < self.start_date:
            return False

        if self.end_date and target_date > self.end_date:
            return False

        if self.repeat_type == "DAILY":
            return True

        if self.repeat_type == "WEEKLY":
            return self.weekly_days.get(target_date.weekday(), False)

        return False