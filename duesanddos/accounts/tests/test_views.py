import tempfile
import shutil

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import CustomUser, Profile, Household, HouseholdMember
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


# ---------------------------------------------------------------------------
# register_view tests
# ---------------------------------------------------------------------------


class RegisterViewTests(TestCase):
    def setUp(self):
        self.url = reverse("register")
        self.valid_data = {
            "username": "newuser",
            "firstName": "New",
            "lastName": "User",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "confirmPassword": "StrongPass123!",
        }

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_uses_register_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_get_context_contains_form(self):
        response = self.client.get(self.url)
        self.assertIn("form", response.context)

    def test_valid_registration_creates_user(self):
        self.client.post(self.url, self.valid_data)
        self.assertTrue(CustomUser.objects.filter(username="newuser").exists())

    def test_valid_registration_creates_profile(self):
        self.client.post(self.url, self.valid_data)
        user = CustomUser.objects.get(username="newuser")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_valid_registration_redirects_to_profile(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertRedirects(response, reverse("profile"))

    def test_valid_registration_logs_user_in(self):
        self.client.post(self.url, self.valid_data)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)

    def test_valid_registration_sets_success_message(self):
        response = self.client.post(self.url, self.valid_data, follow=True)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Account created" in str(m) for m in msgs))

    def test_duplicate_username_renders_form_with_error(self):
        CustomUser.objects.create_user(
            username="newuser",
            email="other@example.com",
            password="x",
        )
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            CustomUser.objects.filter(email="newuser@example.com").exists()
        )

    def test_duplicate_email_renders_form_with_error(self):
        CustomUser.objects.create_user(
            username="other",
            email="newuser@example.com",
            password="x",
        )
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 200)

    def test_mismatched_passwords_returns_200(self):
        data = dict(self.valid_data, confirmPassword="DifferentPass1!")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_blank_username_returns_200(self):
        data = dict(self.valid_data, username="")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_sets_first_and_last_name(self):
        self.client.post(self.url, self.valid_data)
        user = CustomUser.objects.get(username="newuser")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")


# ---------------------------------------------------------------------------
# dashboard_view tests
# ---------------------------------------------------------------------------


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="dashuser",
            email="dash@example.com",
            password=TEST_PASSWORD,
        )
        self.url = reverse("dashboard")

    def test_unauthenticated_redirects(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_returns_200(self):
        self.client.login(username="dashuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_dashboard_template(self):
        self.client.login(username="dashuser", password=TEST_PASSWORD)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/dashboard.html")


# ---------------------------------------------------------------------------
# Static page view tests (faq, terms, privacy)
# ---------------------------------------------------------------------------


class StaticPageViewTests(TestCase):
    def test_faq_returns_200(self):
        response = self.client.get(reverse("faq"))
        self.assertEqual(response.status_code, 200)

    def test_faq_uses_correct_template(self):
        response = self.client.get(reverse("faq"))
        self.assertTemplateUsed(response, "accounts/faq.html")

    def test_terms_returns_200(self):
        response = self.client.get(reverse("terms"))
        self.assertEqual(response.status_code, 200)

    def test_terms_uses_correct_template(self):
        response = self.client.get(reverse("terms"))
        self.assertTemplateUsed(response, "accounts/terms.html")

    def test_privacy_returns_200(self):
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)

    def test_privacy_uses_correct_template(self):
        response = self.client.get(reverse("privacy"))
        self.assertTemplateUsed(response, "accounts/privacy.html")


# ---------------------------------------------------------------------------
# ProtectedLogoutView tests
# ---------------------------------------------------------------------------


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="logoutuser",
            email="logout@example.com",
            password=TEST_PASSWORD,
        )
        self.client.login(username="logoutuser", password=TEST_PASSWORD)
        self.url = reverse("logout")

    def test_get_returns_200_when_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_uses_logout_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/logout.html")

    def test_unauthenticated_get_redirects(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_unauthenticated_post_redirects(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_post_logs_out_user(self):
        self.client.post(self.url)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)

    def test_get_does_not_log_out_user(self):
        self.client.get(self.url)
        # Verify the user is still logged in by fetching the profile page
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)

    def test_post_redirects_to_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("login"))


# ---------------------------------------------------------------------------
# household_settings_view tests
# ---------------------------------------------------------------------------


class HouseholdSettingsViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="hhuser",
            email="hh@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)
        self.household = Household.objects.create(name="Test House")
        self.member = HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        self.profile.active_household = self.household
        self.profile.save()
        self.client.login(username="hhuser", password=TEST_PASSWORD)
        self.url = reverse("household_settings")

    # -- GET ------------------------------------------------------------------

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "accounts/household_settings.html")

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_context_contains_active_household(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["active_household"], self.household)

    def test_context_contains_members(self):
        response = self.client.get(self.url)
        self.assertIn("members", response.context)

    def test_context_is_admin_true_for_admin(self):
        response = self.client.get(self.url)
        self.assertTrue(response.context["is_admin"])

    def test_get_auto_sets_active_household_if_none(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.active_household)

    # -- POST: create_household -----------------------------------------------

    def test_create_household_creates_and_redirects(self):
        response = self.client.post(
            self.url,
            {"action": "create_household", "household_name": "New House"},
        )
        self.assertRedirects(response, self.url)
        self.assertTrue(Household.objects.filter(name="New House").exists())

    def test_create_household_sets_user_as_admin(self):
        self.client.post(
            self.url,
            {"action": "create_household", "household_name": "My Place"},
        )
        new_hh = Household.objects.get(name="My Place")
        self.assertTrue(
            HouseholdMember.objects.filter(
                user=self.user, household=new_hh, role="Admin"
            ).exists()
        )

    def test_create_household_blank_name_ignored(self):
        count_before = Household.objects.count()
        self.client.post(
            self.url,
            {"action": "create_household", "household_name": ""},
        )
        self.assertEqual(Household.objects.count(), count_before)

    # -- POST: switch_household -----------------------------------------------

    def test_switch_household_updates_active(self):
        hh2 = Household.objects.create(name="Second House")
        HouseholdMember.objects.create(user=self.user, household=hh2, role="Member")
        self.client.post(
            self.url,
            {"action": "switch_household", "household_id": str(hh2.id)},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.active_household, hh2)

    def test_switch_household_invalid_id_ignored(self):
        import uuid

        self.client.post(
            self.url,
            {"action": "switch_household", "household_id": str(uuid.uuid4())},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.active_household, self.household)

    # -- POST: generate_invite ------------------------------------------------

    def test_generate_invite_creates_code(self):
        self.client.post(self.url, {"action": "generate_invite"})
        self.household.refresh_from_db()
        self.assertIsNotNone(self.household.invite_code)
        self.assertIsNotNone(self.household.invite_code_expires)

    def test_non_admin_cannot_generate_invite(self):
        member_user = CustomUser.objects.create_user(
            username="memberonly",
            email="member@example.com",
            password=TEST_PASSWORD,
        )
        member_profile = Profile.objects.create(
            user=member_user, active_household=self.household
        )
        HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="memberonly", password=TEST_PASSWORD)
        self.client.post(self.url, {"action": "generate_invite"})
        self.household.refresh_from_db()
        self.assertIsNone(self.household.invite_code)
        del member_profile  # silence unused var warning

    # -- POST: update_name ----------------------------------------------------

    def test_update_general_as_admin_succeeds(self):
        self.client.post(
            self.url,
            {
                "action": "update_general",
                "name": "Renamed House",
                "description": "New desc",
                "default_rules": "No rules",
            },
        )
        self.household.refresh_from_db()
        self.assertEqual(self.household.name, "Renamed House")
        self.assertEqual(self.household.description, "New desc")
        self.assertEqual(self.household.default_rules, "No rules")

    def test_update_general_as_non_admin_fails(self):
        member_user = CustomUser.objects.create_user(
            username="member2",
            email="member2@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=member_user, active_household=self.household)
        HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="member2", password=TEST_PASSWORD)
        self.client.post(
            self.url,
            {
                "action": "update_general",
                "name": "Hacked Name",
                "description": "Hacked desc",
            },
        )
        self.household.refresh_from_db()
        self.assertNotEqual(self.household.name, "Hacked Name")
        self.assertNotEqual(self.household.description, "Hacked desc")

    # -- POST: join_household (invite code) -----------------------------------

    def test_join_household_with_valid_invite(self):
        from django.utils import timezone
        from datetime import timedelta

        hh2 = Household.objects.create(
            name="Joinable House",
            invite_code="JOINME1234",
            invite_code_expires=timezone.now() + timedelta(days=1),
        )
        new_user = CustomUser.objects.create_user(
            username="joiner",
            email="joiner@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=new_user)
        self.client.logout()
        self.client.login(username="joiner", password=TEST_PASSWORD)
        self.client.post(
            self.url,
            {"action": "join_household", "invite_code": "JOINME1234"},
        )
        self.assertTrue(
            HouseholdMember.objects.filter(user=new_user, household=hh2).exists()
        )

    def test_join_household_with_expired_invite(self):
        from django.utils import timezone
        from datetime import timedelta

        hh2 = Household.objects.create(
            name="Expired House",
            invite_code="EXPIRED123",
            invite_code_expires=timezone.now() - timedelta(days=1),
        )
        response = self.client.post(
            self.url,
            {"action": "join_household", "invite_code": "EXPIRED123"},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("expired" in str(m).lower() for m in msgs))
        del hh2

    def test_join_household_with_invalid_code(self):
        response = self.client.post(
            self.url,
            {"action": "join_household", "invite_code": "BADCODE999"},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("invalid" in str(m).lower() for m in msgs))

    def test_join_household_already_member(self):
        from django.utils import timezone
        from datetime import timedelta

        self.household.invite_code = "MYCODE1234"
        self.household.invite_code_expires = timezone.now() + timedelta(days=1)
        self.household.save()
        response = self.client.post(
            self.url,
            {"action": "join_household", "invite_code": "MYCODE1234"},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already" in str(m).lower() for m in msgs))

    # -- POST: update_role ----------------------------------------------------

    def test_update_role_as_admin(self):
        member_user = CustomUser.objects.create_user(
            username="roletest",
            email="roletest@example.com",
            password=TEST_PASSWORD,
        )
        member_link = HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.post(
            self.url,
            {
                "action": "update_role",
                "user_id": str(member_user.id),
                "role": "Admin",
            },
        )
        member_link.refresh_from_db()
        self.assertEqual(member_link.role, "Admin")

    def test_last_admin_cannot_demote_self(self):
        response = self.client.post(
            self.url,
            {
                "action": "update_role",
                "user_id": str(self.user.id),
                "role": "Member",
            },
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("cannot demote" in str(m).lower() for m in msgs))
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, "Admin")

    # -- POST: remove_member --------------------------------------------------

    def test_admin_can_remove_member(self):
        victim = CustomUser.objects.create_user(
            username="victim",
            email="victim@example.com",
            password=TEST_PASSWORD,
        )
        HouseholdMember.objects.create(
            user=victim, household=self.household, role="Member"
        )
        self.client.post(
            self.url,
            {"action": "remove_member", "user_id": str(victim.id)},
        )
        self.assertFalse(
            HouseholdMember.objects.filter(
                user=victim, household=self.household
            ).exists()
        )

    def test_member_can_leave_household(self):
        leaver = CustomUser.objects.create_user(
            username="leaver",
            email="leaver@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=leaver, active_household=self.household)
        HouseholdMember.objects.create(
            user=leaver, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="leaver", password=TEST_PASSWORD)
        self.client.post(
            self.url,
            {"action": "remove_member", "user_id": str(leaver.id)},
        )
        self.assertFalse(
            HouseholdMember.objects.filter(
                user=leaver, household=self.household
            ).exists()
        )

    def test_last_admin_cannot_leave_without_successor(self):
        response = self.client.post(
            self.url,
            {"action": "remove_member", "user_id": str(self.user.id)},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("admin" in str(m).lower() for m in msgs))
        self.assertTrue(
            HouseholdMember.objects.filter(
                user=self.user, household=self.household
            ).exists()
        )

    def test_last_admin_can_leave_with_new_admin(self):
        successor = CustomUser.objects.create_user(
            username="successor",
            email="successor@example.com",
            password=TEST_PASSWORD,
        )
        succ_link = HouseholdMember.objects.create(
            user=successor, household=self.household, role="Member"
        )
        self.client.post(
            self.url,
            {
                "action": "remove_member",
                "user_id": str(self.user.id),
                "new_admin_id": str(successor.id),
            },
        )
        succ_link.refresh_from_db()
        self.assertEqual(succ_link.role, "Admin")
        self.assertFalse(
            HouseholdMember.objects.filter(
                user=self.user, household=self.household
            ).exists()
        )

    # -- POST: delete_household -----------------------------------------------

    def test_admin_can_delete_household(self):
        hh_id = self.household.id
        self.client.post(self.url, {"action": "delete_household"})
        self.assertFalse(Household.objects.filter(id=hh_id).exists())

    def test_non_admin_cannot_delete_household(self):
        member_user = CustomUser.objects.create_user(
            username="nodelete",
            email="nodelete@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=member_user, active_household=self.household)
        HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="nodelete", password=TEST_PASSWORD)
        self.client.post(self.url, {"action": "delete_household"})
        self.assertTrue(Household.objects.filter(id=self.household.id).exists())

    def test_no_active_household_shows_error_for_admin_actions(self):
        self.profile.active_household = None
        self.profile.save()
        response = self.client.post(
            self.url, {"action": "update_general", "name": "Nope"}, follow=True
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("no active household" in str(m).lower() for m in msgs))

    def test_unrecognized_action_redirects(self):
        response = self.client.post(self.url, {"action": "bogus_action"})
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# delete_account_view tests
# ---------------------------------------------------------------------------


class DeleteAccountViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="deluser",
            email="del@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=self.user)
        self.client.login(username="deluser", password=TEST_PASSWORD)
        self.url = reverse("delete_account")

    def test_get_redirects(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.post(self.url, {"confirmation": TEST_PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_correct_password_deletes_account(self):
        self.client.post(self.url, {"confirmation": TEST_PASSWORD})
        self.assertFalse(CustomUser.objects.filter(username="deluser").exists())

    def test_correct_password_redirects_to_login(self):
        response = self.client.post(self.url, {"confirmation": TEST_PASSWORD})
        self.assertRedirects(response, reverse("login"))

    def test_wrong_password_aborts_deletion(self):
        self.client.post(self.url, {"confirmation": "WrongPassword!"})
        self.assertTrue(CustomUser.objects.filter(username="deluser").exists())

    def test_wrong_password_redirects_to_profile(self):
        response = self.client.post(self.url, {"confirmation": "WrongPassword!"})
        self.assertRedirects(response, reverse("profile"))

    def test_wrong_password_sets_error_message(self):
        response = self.client.post(
            self.url,
            {"confirmation": "WrongPassword!"},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("incorrect" in str(m).lower() for m in msgs))

    def test_deletion_removes_connected_households(self):
        hh = Household.objects.create(name="ToDelete")
        HouseholdMember.objects.create(user=self.user, household=hh, role="Admin")
        self.profile_hh = hh
        self.client.post(self.url, {"confirmation": TEST_PASSWORD})
        self.assertFalse(Household.objects.filter(id=hh.id).exists())

    def test_add_expense_pro_splitting(self):
        from django.urls import reverse
        from accounts.models import Household, HouseholdMember, Profile

        hh = Household.objects.create(name="Test House")
        HouseholdMember.objects.create(user=self.user, household=hh, role="Admin")

        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.active_household = hh
        profile.save()

        self.client.login(username="testuser", password="password")
        url = reverse("add_expense_pro")

        post_data = {
            "title": "Test Split",
            "amount": "100.00",
            "payer": self.user.id,
            "split_type": "EQUAL",
            "participants": [self.user.id],
        }
        response = self.client.post(url, post_data)

        self.assertEqual(response.status_code, 302)
