from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # required + unique
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    # Keep defaults:
    # USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS includes 'email' by default in createsuperuser prompts if you set it:
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username