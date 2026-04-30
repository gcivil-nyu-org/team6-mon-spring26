from django.test import TestCase
from django.contrib.auth.forms import PasswordChangeForm

from accounts.models import CustomUser, Profile
from accounts.forms import UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm

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
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

    def test_meta_model_is_profile(self):
        self.assertEqual(ProfileUpdateForm.Meta.model, Profile)

    def test_meta_fields(self):
        form = ProfileUpdateForm()
        self.assertEqual(
            list(form.fields.keys()),
            ["avatar", "bio", "theme", "default_calendar_view"],
        )

    def test_valid_data_with_bio(self):
        form = ProfileUpdateForm(
            data={
                "bio": "A short bio",
                "theme": "light",
                "default_calendar_view": "dayGridMonth",
                "notifications_enabled": True,
            },
            instance=self.profile,
        )
        self.assertTrue(form.is_valid())

    def test_empty_data_is_valid(self):
        form = ProfileUpdateForm(
            data={"theme": "light", "default_calendar_view": "dayGridMonth"},
            instance=self.profile,
        )
        self.assertTrue(form.is_valid())


class CustomPasswordChangeFormTests(TestCase):
    def test_inherits_from_password_change_form(self):
        self.assertTrue(issubclass(CustomPasswordChangeForm, PasswordChangeForm))


# ---------------------------------------------------------------------------
# RegisterForm tests
# ---------------------------------------------------------------------------


class RegisterFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            "username": "formuser",
            "firstName": "Form",
            "lastName": "User",
            "email": "formuser@example.com",
            "password": "StrongPass123!",
            "confirmPassword": "StrongPass123!",
        }

    def _get_form(self, **overrides):
        from accounts.forms import RegisterForm

        data = dict(self.valid_data, **overrides)
        return RegisterForm(data=data)

    def test_valid_form_is_valid(self):
        form = self._get_form()
        self.assertTrue(form.is_valid())

    def test_duplicate_username_invalid(self):
        CustomUser.objects.create_user(
            username="formuser",
            email="other@example.com",
            password="x",
        )
        form = self._get_form()
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_duplicate_email_invalid(self):
        CustomUser.objects.create_user(
            username="other",
            email="formuser@example.com",
            password="x",
        )
        form = self._get_form()
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_mismatched_passwords_invalid(self):
        form = self._get_form(confirmPassword="DifferentPass!")
        self.assertFalse(form.is_valid())
        self.assertIn("confirmPassword", form.errors)

    def test_weak_password_invalid(self):
        form = self._get_form(password="123", confirmPassword="123")
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_blank_username_invalid(self):
        form = self._get_form(username="")
        self.assertFalse(form.is_valid())

    def test_invalid_email_invalid(self):
        form = self._get_form(email="notanemail")
        self.assertFalse(form.is_valid())
