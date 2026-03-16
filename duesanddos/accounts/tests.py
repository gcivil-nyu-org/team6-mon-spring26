import tempfile
import shutil

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.forms import PasswordChangeForm

from .models import CustomUser, Profile
from .forms import UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm

SMALL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00"
    b"\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff\x21\xf9\x04\x00\x00"
    b"\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)

TEST_PASSWORD = "TestPass123!"
NEW_PASSWORD = "NewSecure456!"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class CustomUserModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def test_str_returns_username(self):
        self.assertEqual(str(self.user), "testuser")


class ProfileModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_str_returns_formatted_string(self):
        self.assertEqual(str(self.profile), "testuser's profile")

    def test_default_bio_is_empty(self):
        self.assertEqual(self.profile.bio, "")

    def test_default_notifications_enabled_is_true(self):
        self.assertTrue(self.profile.notifications_enabled)

    def test_default_avatar_is_falsy(self):
        self.assertFalse(self.profile.avatar)


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


class UserUpdateFormTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
            first_name="Test",
            last_name="User",
        )

    def test_meta_model_is_custom_user(self):
        self.assertEqual(UserUpdateForm.Meta.model, CustomUser)

    def test_meta_fields(self):
        self.assertEqual(
            list(UserUpdateForm.Meta.fields),
            ["username", "first_name", "last_name", "email", "phone_number"],
        )

    def test_valid_data(self):
        form = UserUpdateForm(
            data={
                "username": "newname",
                "first_name": "New",
                "last_name": "Name",
                "email": "new@example.com",
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_blank_username_is_invalid(self):
        form = UserUpdateForm(
            data={
                "username": "",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
            },
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class ProfileUpdateFormTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_meta_model_is_profile(self):
        self.assertEqual(ProfileUpdateForm.Meta.model, Profile)

    def test_meta_fields(self):
        self.assertEqual(
            list(ProfileUpdateForm.Meta.fields),
            ["avatar", "bio", "notifications_enabled"],
        )

    def test_valid_data_with_bio(self):
        form = ProfileUpdateForm(
            data={"bio": "A short bio", "notifications_enabled": True},
            instance=self.profile,
        )
        self.assertTrue(form.is_valid())

    def test_empty_data_is_valid(self):
        form = ProfileUpdateForm(data={}, instance=self.profile)
        self.assertTrue(form.is_valid())


class CustomPasswordChangeFormTests(TestCase):
    def test_inherits_from_password_change_form(self):
        self.assertTrue(issubclass(CustomPasswordChangeForm, PasswordChangeForm))


# ---------------------------------------------------------------------------
# profile_view tests
# ---------------------------------------------------------------------------


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
            first_name="Test",
            last_name="User",
        )
        self.profile = Profile.objects.create(user=self.user, bio="Hello world")
        self.url = reverse("profile")

    # -- authentication -------------------------------------------------------

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_redirect_includes_next_param(self):
        response = self.client.get(self.url)
        self.assertIn("next=", response.url)
        self.assertIn("/accounts/profile/", response.url)

    # -- GET (happy path) -----------------------------------------------------

    def test_authenticated_get_returns_200(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_profile_template(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")

    def test_context_contains_profile(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertIn("profile", response.context)
        self.assertEqual(response.context["profile"], self.profile)

    # -- get_or_create --------------------------------------------------------

    def test_profile_auto_created_when_missing(self):
        self.profile.delete()
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_existing_profile_is_not_duplicated(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    # -- rendered content -----------------------------------------------------

    def test_displays_username(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, "testuser")

    def test_displays_email(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, "test@example.com")

    def test_displays_bio_when_set(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, "Hello world")

    def test_shows_default_text_when_bio_empty(self):
        self.profile.bio = ""
        self.profile.save()
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, "No bio added yet.")

    def test_edit_profile_link_present(self):
        self.client.login(username="testuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, reverse("profile"))


# ---------------------------------------------------------------------------
# edit_profile_view tests
# ---------------------------------------------------------------------------

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class EditProfileViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
            first_name="Test",
            last_name="User",
        )
        self.profile = Profile.objects.create(user=self.user)
        self.url = reverse("profile")
        self.client.login(username="testuser", password=TEST_PASSWORD)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    # -- helpers --------------------------------------------------------------

    def _profile_data(self, **overrides):
        """Return a default valid save_profile POST payload."""
        data = {
            "save_profile": "",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "bio": "",
            "notifications_enabled": True,
        }
        data.update(overrides)
        return data

    def _password_data(self, **overrides):
        """Return a default valid change_password POST payload."""
        data = {
            "change_password": "",
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
        data.update(overrides)
        return data

    # -- authentication -------------------------------------------------------

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_redirect_includes_next_param(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn("next=", response.url)
        self.assertIn("/accounts/profile/", response.url)

    # -- GET ------------------------------------------------------------------

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_uses_edit_profile_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")

    def test_get_context_contains_user_form(self):
        response = self.client.get(self.url)
        self.assertIn("user_form", response.context)
        self.assertIsInstance(response.context["user_form"], UserUpdateForm)

    def test_get_context_contains_profile_form(self):
        response = self.client.get(self.url)
        self.assertIn("profile_form", response.context)
        self.assertIsInstance(response.context["profile_form"], ProfileUpdateForm)

    def test_get_context_contains_password_form(self):
        response = self.client.get(self.url)
        self.assertIn("password_form", response.context)
        self.assertIsInstance(
            response.context["password_form"], CustomPasswordChangeForm
        )

    def test_profile_auto_created_on_get_when_missing(self):
        self.profile.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    # -- POST save_profile (valid) --------------------------------------------

    def test_save_profile_valid_redirects_to_profile(self):
        response = self.client.post(self.url, self._profile_data())
        self.assertRedirects(response, reverse("profile"))

    def test_save_profile_valid_sets_success_message(self):
        response = self.client.post(self.url, self._profile_data(), follow=True)
        msgs = list(get_messages(response.wsgi_request))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(str(msgs[0]), "Your profile was updated.")

    def test_save_profile_persists_user_changes(self):
        self.client.post(
            self.url,
            self._profile_data(
                username="updateduser",
                first_name="Updated",
                last_name="Name",
                email="updated@example.com",
            ),
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "updateduser")
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_save_profile_persists_profile_changes(self):
        self.client.post(
            self.url,
            self._profile_data(bio="Updated bio", notifications_enabled=False),
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Updated bio")
        self.assertFalse(self.profile.notifications_enabled)

    def test_save_profile_with_avatar_upload(self):
        avatar = SimpleUploadedFile("test.gif", SMALL_GIF, content_type="image/gif")
        response = self.client.post(
            self.url,
            self._profile_data(avatar=avatar),
        )
        self.assertRedirects(response, reverse("profile"))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.avatar)

    # -- POST save_profile (invalid) ------------------------------------------

    def test_save_profile_invalid_returns_200(self):
        response = self.client.post(self.url, self._profile_data(username=""))
        self.assertEqual(response.status_code, 200)

    def test_save_profile_invalid_shows_user_form_errors(self):
        response = self.client.post(self.url, self._profile_data(username=""))
        self.assertIn("username", response.context["user_form"].errors)

    def test_save_profile_invalid_still_has_all_forms_in_context(self):
        response = self.client.post(self.url, self._profile_data(username=""))
        self.assertIn("user_form", response.context)
        self.assertIn("profile_form", response.context)
        self.assertIn("password_form", response.context)

    def test_save_profile_duplicate_username_rejected(self):
        CustomUser.objects.create_user(
            username="taken",
            email="taken@example.com",
            password=TEST_PASSWORD,
        )
        response = self.client.post(self.url, self._profile_data(username="taken"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_form"].errors)

    # -- POST change_password (valid) -----------------------------------------

    def test_change_password_valid_redirects_to_profile(self):
        response = self.client.post(self.url, self._password_data())
        self.assertRedirects(response, reverse("profile"))

    def test_change_password_valid_sets_success_message(self):
        response = self.client.post(self.url, self._password_data(), follow=True)
        msgs = list(get_messages(response.wsgi_request))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(str(msgs[0]), "Your password was changed successfully.")

    def test_change_password_actually_changes_password(self):
        self.client.post(self.url, self._password_data())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_change_password_session_preserved(self):
        self.client.post(self.url, self._password_data())
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)

    # -- POST change_password (invalid) ---------------------------------------

    def test_change_password_wrong_old_password_returns_200(self):
        response = self.client.post(
            self.url,
            self._password_data(old_password="WrongPassword999!"),
        )
        self.assertEqual(response.status_code, 200)

    def test_change_password_invalid_shows_password_form_errors(self):
        response = self.client.post(
            self.url,
            self._password_data(old_password="WrongPassword999!"),
        )
        self.assertIn("password_form", response.context)
        self.assertTrue(response.context["password_form"].errors)

    def test_change_password_invalid_still_has_all_forms_in_context(self):
        response = self.client.post(
            self.url,
            self._password_data(old_password="WrongPassword999!"),
        )
        self.assertIn("user_form", response.context)
        self.assertIn("profile_form", response.context)
        self.assertIn("password_form", response.context)

    def test_change_password_mismatched_new_passwords_returns_200(self):
        response = self.client.post(
            self.url,
            self._password_data(new_password2="Mismatch789!"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["password_form"].errors)
