from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, RequestFactory
from django.urls import reverse

from accounts.adapters import CustomAccountAdapter, CustomSocialAccountAdapter
from accounts.models import Expense, ExpenseSplit, Household, HouseholdMember, Profile
from duesanddos.urls import home_redirect


User = get_user_model()
TEST_PASSWORD = "TestPass123!"


class AdapterAndRootUrlTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="rootuser", email="root@example.com", password=TEST_PASSWORD
        )

    def test_home_redirect_sends_authenticated_user_to_dashboard(self):
        request = self.factory.get("/")
        request.user = self.user

        response = home_redirect(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_custom_account_adapter_redirects_to_dashboard(self):
        request = self.factory.get("/")

        response = CustomAccountAdapter().get_login_redirect_url(request)

        self.assertEqual(response, reverse("dashboard"))

    def test_custom_social_adapter_redirects_to_dashboard(self):
        request = self.factory.get("/")

        response = CustomSocialAccountAdapter().get_connect_redirect_url(
            request, socialaccount=None
        )

        self.assertEqual(response, reverse("dashboard"))

    def test_custom_social_adapter_disables_auto_signup(self):
        request = self.factory.get("/")

        response = CustomSocialAccountAdapter().is_auto_signup_allowed(
            request, sociallogin=None
        )

        self.assertFalse(response)


class AdditionalProfileBranchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=self.user)
        self.client.login(username="profileuser", password=TEST_PASSWORD)
        self.url = reverse("profile")

    def test_unrecognized_profile_post_renders_unbound_forms(self):
        response = self.client.post(self.url, {"unexpected_action": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user_form"].is_bound)
        self.assertFalse(response.context["profile_form"].is_bound)
        self.assertFalse(response.context["password_form"].is_bound)


class AdditionalHouseholdBranchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="adminuser", email="admin@example.com", password=TEST_PASSWORD
        )
        self.other = User.objects.create_user(
            username="otheruser", email="other@example.com", password=TEST_PASSWORD
        )
        self.third = User.objects.create_user(
            username="thirduser", email="third@example.com", password=TEST_PASSWORD
        )
        self.household = Household.objects.create(name="Main House")
        self.other_household = Household.objects.create(name="Backup House")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        Profile.objects.create(user=self.other, active_household=self.household)
        Profile.objects.create(user=self.third, active_household=self.household)
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.other, household=self.household, role="Member"
        )
        HouseholdMember.objects.create(
            user=self.third, household=self.other_household, role="Admin"
        )
        self.client.login(username="adminuser", password=TEST_PASSWORD)
        self.url = reverse("household_settings")

    def test_non_admin_cannot_manage_roles(self):
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)

        response = self.client.post(
            self.url,
            {"action": "update_role", "user_id": str(self.user.id), "role": "Member"},
            follow=True,
        )

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Only Admins can manage roles.", messages)

    def test_non_admin_cannot_remove_other_member(self):
        intruder = User.objects.create_user(
            username="intruder", email="intruder@example.com", password=TEST_PASSWORD
        )
        Profile.objects.create(user=intruder, active_household=self.household)
        HouseholdMember.objects.create(
            user=intruder, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)

        response = self.client.post(
            self.url,
            {"action": "remove_member", "user_id": str(intruder.id)},
            follow=True,
        )

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Only Admins can remove other members.", messages)
        self.assertTrue(
            HouseholdMember.objects.filter(
                user=intruder, household=self.household
            ).exists()
        )

    def test_last_admin_leave_with_missing_successor_shows_error(self):
        response = self.client.post(
            self.url,
            {
                "action": "remove_member",
                "user_id": str(self.user.id),
                "new_admin_id": str(self.third.id),
            },
            follow=True,
        )

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Selected successor not found.", messages)
        self.assertTrue(
            HouseholdMember.objects.filter(
                user=self.user, household=self.household
            ).exists()
        )

    def test_join_household_invalid_code_shows_error(self):
        response = self.client.post(self.url, {"action": "join_household", "invite_code": "INVALID"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Invalid invite code.", messages)

    def test_join_household_expired_code_shows_error(self):
        from django.utils import timezone
        from datetime import timedelta
        self.household.invite_code = "EXPIRED"
        self.household.invite_code_expires = timezone.now() - timedelta(days=1)
        self.household.save()
        response = self.client.post(self.url, {"action": "join_household", "invite_code": "EXPIRED"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("This invite code has expired.", messages)

    def test_non_admin_cannot_update_general_settings(self):
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)
        response = self.client.post(self.url, {"action": "update_general", "name": "New Name"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Only Admins can change household settings.", messages)

    def test_non_admin_cannot_generate_invite_code(self):
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)
        response = self.client.post(self.url, {"action": "generate_invite"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Only Admins can generate invite codes.", messages)

    def test_non_admin_cannot_delete_household(self):
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)
        response = self.client.post(self.url, {"action": "delete_household"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Only Admins can delete the household.", messages)

    def test_last_admin_cannot_demote_themselves(self):
        response = self.client.post(self.url, {"action": "update_role", "user_id": str(self.user.id), "role": "Member"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("You cannot demote yourself as the only admin.", messages)
        self.assertEqual(HouseholdMember.objects.get(user=self.user, household=self.household).role, "Admin")

    def test_member_can_leave_household(self):
        self.client.logout()
        self.client.login(username="otheruser", password=TEST_PASSWORD)
        response = self.client.post(self.url, {"action": "remove_member", "user_id": str(self.other.id)}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("You left the household.", messages)
        self.assertFalse(HouseholdMember.objects.filter(user=self.other, household=self.household).exists())
        # Check if fallback worked
        # (other user from setUp has active_household=self.household, after leaving they belong to no more households in setUp, but the code says "fall back to another household if available")
        # In setUp, otheruser only belongs to self.household.
        # Profile.objects.create(user=self.other, active_household=self.household)
        other_profile = Profile.objects.get(user=self.other)
        self.assertIsNone(other_profile.active_household)


class DeleteAccountNoPasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="socialuser", email="social@example.com", password=TEST_PASSWORD
        )
        self.user.set_unusable_password()
        self.user.save()
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)
        self.url = reverse("delete_account")

    def test_non_password_account_requires_exact_delete_confirmation(self):
        response = self.client.post(self.url, {"confirmation": "delete"}, follow=True)

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("please type as it is - case sensitive", messages)
        self.assertTrue(User.objects.filter(username="socialuser").exists())

    def test_incorrect_password_deletion_fails(self):
        # Refetch user to ensure status is clean
        user = User.objects.get(username="socialuser")
        user.set_password(TEST_PASSWORD)
        user.save()
        # Re-login to update session with new password context if necessary
        self.client.login(username="socialuser", password=TEST_PASSWORD)
        
        response = self.client.post(self.url, {"confirmation": "WrongPass"}, follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Incorrect password" in m for m in messages))
        self.assertTrue(User.objects.filter(username="socialuser").exists())

    def test_non_password_account_can_delete_with_exact_delete_confirmation(self):
        response = self.client.post(self.url, {"confirmation": "DELETE"})

        self.assertRedirects(response, reverse("login"))
        self.assertFalse(User.objects.filter(username="socialuser").exists())


class ExpensesAndDashboardBranchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payer", email="payer@example.com", password=TEST_PASSWORD
        )
        self.friend = User.objects.create_user(
            username="friend", email="friend@example.com", password=TEST_PASSWORD
        )
        self.household = Household.objects.create(name="Budget House")
        self.profile = Profile.objects.create(
            user=self.user, active_household=self.household
        )
        Profile.objects.create(user=self.friend, active_household=self.household)
        HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(
            user=self.friend, household=self.household, role="Member"
        )
        self.client.login(username="payer", password=TEST_PASSWORD)

    def test_expenses_list_redirects_when_no_active_household(self):
        self.profile.active_household = None
        self.profile.save()

        response = self.client.get(reverse("expenses_list"))

        self.assertRedirects(response, reverse("household_settings"))

    def test_dashboard_context_for_user_who_is_owed(self):
        dinner = Expense.objects.create(
            title="Dinner",
            amount=Decimal("60.00"),
            payer=self.user,
            household=self.household,
        )
        ExpenseSplit.objects.create(
            expense=dinner, user=self.user, amount_owed=Decimal("30.00")
        )
        ExpenseSplit.objects.create(
            expense=dinner, user=self.friend, amount_owed=Decimal("30.00")
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.context["total_spent"], Decimal("60.00"))
        self.assertEqual(response.context["you_are_owed"], 30.0)
        self.assertEqual(response.context["you_owe"], 0)
        self.assertEqual(
            response.context["owed_breakdown"], [{"name": "friend", "amount": 30.0}]
        )
        self.assertEqual(response.context["owe_to_breakdown"], [])

    def test_dashboard_context_for_user_who_owes(self):
        utilities = Expense.objects.create(
            title="Utilities",
            amount=Decimal("80.00"),
            payer=self.friend,
            household=self.household,
        )
        ExpenseSplit.objects.create(
            expense=utilities, user=self.user, amount_owed=Decimal("50.00")
        )
        ExpenseSplit.objects.create(
            expense=utilities, user=self.friend, amount_owed=Decimal("30.00")
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.context["you_are_owed"], 0)
        self.assertEqual(response.context["you_owe"], 50.0)
        self.assertEqual(
            response.context["owe_to_breakdown"], [{"name": "friend", "amount": 50.0}]
        )
        self.assertEqual(response.context["owed_breakdown"], [])

    def test_dashboard_without_household_sets_flag(self):
        self.profile.active_household = None
        self.profile.save()

        response = self.client.get(reverse("dashboard"))

        self.assertTrue(response.context["no_household"])

    def test_simple_add_expense_creates_expense_and_sets_message(self):
        response = self.client.post(
            reverse("add_expense"),
            {"title": "Snacks", "amount": "12.50"},
            follow=True,
        )

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            Expense.objects.filter(
                title="Snacks",
                amount=Decimal("12.50"),
                payer=self.user,
                household=self.household,
            ).exists()
        )
        self.assertIn("Added $12.50 for Snacks!", messages)

    @patch("accounts.views.Expense")
    def test_simple_add_expense_ignores_missing_title_or_amount(self, expense_cls):
        self.client.post(reverse("add_expense"), {"title": "", "amount": "12.50"})
        self.client.post(reverse("add_expense"), {"title": "Snacks", "amount": ""})

        expense_cls.objects.create.assert_not_called()
