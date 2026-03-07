from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # required + unique
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    # Keep defaults:
    # USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS includes 'email' by default in createsuperuser prompts if you set it:
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username
    
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    bio = models.TextField(blank=True)
    notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s profile"