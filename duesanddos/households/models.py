import uuid
from django.db import models
from django.conf import settings


class Household(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_rules = models.TextField(blank=True)
    invite_code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    invite_code_expires = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fridge_note = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        pass


class HouseholdMember(models.Model):
    ROLE_CHOICES = (
        ("Admin", "Admin"),
        ("Member", "Member"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="Member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "household")

    def __str__(self):
        return f"{self.user.username} - {self.household.name} ({self.role})"
