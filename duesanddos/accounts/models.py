import uuid
import os
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone


class UploadToPath:
    """
    Upload-to callable that Django migrations can serialize via deconstruct().

    S3 path pattern:  {category}/uid_{user_pk}/{uuid32}.{ext}

    Examples:
        UploadToPath('profile_pics')  →  profile_pics/uid_42/a1b2c3...jpg
        UploadToPath('expenses')      →  expenses/uid_42/d4e5f6...jpg
        UploadToPath('chores')        →  chores/uid_42/g7h8i9...jpg

    1M+ user design notes:
    - user_pk   : immutable DB PK (never changes, unlike username or email)
    - uuid4.hex : 32-char random — collision probability effectively zero
    - category  : separate S3 key prefix per media type; enables per-prefix
                  IAM scoping, lifecycle rules, and CDN cache policies
    - S3 automatically shards on key hash, so uid_ sub-prefixes give good
      distribution even without explicit randomized prefixes
    """

    def __init__(self, category: str):
        self.category = category

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower() or ".jpg"
        user_pk = getattr(instance, "user_id", None)
        if user_pk is None:
            user = getattr(instance, "user", None)
            user_pk = getattr(user, "pk", "unknown") if user else "unknown"
        return f"{self.category}/uid_{user_pk}/{uuid.uuid4().hex}{ext}"

    def deconstruct(self):
        """Required by Django to serialize this callable in migration files."""
        return ("accounts.models.UploadToPath", [self.category], {})


def make_upload_path(category: str) -> UploadToPath:
    """Convenience alias: make_upload_path('expenses') == UploadToPath('expenses')."""
    return UploadToPath(category)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # required + unique
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    # Keep defaults:
    # USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS includes 'email' by default in createsuperuser prompts:
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


class Household(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_rules = models.TextField(blank=True)
    invite_code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    invite_code_expires = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(
        upload_to=make_upload_path("profile_pics"), blank=True, null=True
    )
    bio = models.TextField(blank=True)
    notifications_enabled = models.BooleanField(default=True)
    active_household = models.ForeignKey(
        Household,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_profiles",
    )

    def save(self, *args, **kwargs):
        """Delete the old avatar from S3 whenever a new one is uploaded."""
        try:
            old = Profile.objects.get(pk=self.pk)
        except Profile.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        if old and old.avatar and old.avatar != self.avatar:
            old.avatar.storage.delete(old.avatar.name)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Expense(models.Model):
    SPLIT_CHOICES = (
        ('EQUAL', 'Split Equally'),
        ('PERCENT', 'Split by Percentage'),
    )
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses_paid')
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='expenses')
    split_type = models.CharField(max_length=10, choices=SPLIT_CHOICES, default='EQUAL')
    date_spent = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (${self.amount})"

class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2) # The calculated share

    def __str__(self):
        return f"{self.user.username} owes ${self.amount_owed} for {self.expense.title}"