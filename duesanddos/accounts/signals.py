import logging
import requests
from django.core.files.base import ContentFile
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Profile
from allauth.socialaccount.models import SocialAccount

logger = logging.getLogger(__name__)


@receiver(user_signed_up)
def fetch_gmail_photo(request, user, **kwargs):
    """
    When a new user signs up via Google OAuth, fetch their Gmail profile picture
    and save it to S3 as their avatar.
    """
    try:
        # Check if the user signed up via Google
        social_account = SocialAccount.objects.filter(
            user=user, provider="google"
        ).first()
        if not social_account:
            return

        # Google profile photo URL is typically stored in extra_data['picture']
        picture_url = social_account.extra_data.get("picture")
        if not picture_url:
            return

        profile, _ = Profile.objects.get_or_create(user=user)

        # Don't overwrite if they somehow already have an avatar
        if profile.avatar:
            return

        # Fetch the image
        response = requests.get(picture_url)
        if response.status_code == 200:
            # Save it via our make_upload_path factory (which generates S3 unique path)
            file_name = f"gmail_photo_{user.pk}.jpg"
            profile.avatar.save(file_name, ContentFile(response.content), save=True)

    except Exception as e:
        # We don't want to crash the signup process if photo download fails
        logger.debug("Error fetching Gmail photo: %s", e)
