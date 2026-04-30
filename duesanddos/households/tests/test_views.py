from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember

TEST_PASSWORD = "TestPass123!"


class HouseholdSettingsViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="hhuser",
            email="hh@example.com",
            password=TEST_PASSWORD,
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.household = Household.objects.create(name="Test House")
        self.member = HouseholdMember.objects.create(
            user=self.user, household=self.household, role="Admin"
        )
        self.profile.active_household = self.household
        self.profile.save()
        self.client.login(username="hhuser", password=TEST_PASSWORD)
        self.url = reverse("household_settings")

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
        Profile.objects.update_or_create(
            user=member_user, defaults={"active_household": self.household}
        )
        HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="memberonly", password=TEST_PASSWORD)
        self.client.post(self.url, {"action": "generate_invite"})
        self.household.refresh_from_db()
        self.assertIsNone(self.household.invite_code)

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
        Profile.objects.update_or_create(
            user=member_user, defaults={"active_household": self.household}
        )
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
        Profile.objects.get_or_create(user=new_user)
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

        Household.objects.create(
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
        Profile.objects.update_or_create(
            user=leaver, defaults={"active_household": self.household}
        )
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
        Profile.objects.update_or_create(
            user=member_user, defaults={"active_household": self.household}
        )
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

    def test_update_role_non_admin_fails(self):
        member_user = CustomUser.objects.create_user(
            username="nonadmin",
            email="nonadmin@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.update_or_create(
            user=member_user, defaults={"active_household": self.household}
        )
        HouseholdMember.objects.create(
            user=member_user, household=self.household, role="Member"
        )
        self.client.logout()
        self.client.login(username="nonadmin", password=TEST_PASSWORD)
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
        self.assertTrue(
            any("only admins can manage roles" in str(m).lower() for m in msgs)
        )

    def test_last_admin_leave_successor_not_found(self):
        response = self.client.post(
            self.url,
            {
                "action": "remove_member",
                "user_id": str(self.user.id),
                "new_admin_id": "9999",  # Non-existent successor
            },
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("successor not found" in str(m).lower() for m in msgs))

    def test_remove_member_non_admin_fails(self):
        victim = CustomUser.objects.create_user(
            username="victim2",
            email="victim2@example.com",
            password=TEST_PASSWORD,
        )
        HouseholdMember.objects.create(
            user=victim, household=self.household, role="Member"
        )

        leaver = CustomUser.objects.create_user(
            username="leaver2",
            email="leaver2@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.update_or_create(
            user=leaver, defaults={"active_household": self.household}
        )
        HouseholdMember.objects.create(
            user=leaver, household=self.household, role="Member"
        )

        self.client.logout()
        self.client.login(username="leaver2", password=TEST_PASSWORD)
        # Try to remove someone else
        response = self.client.post(
            self.url,
            {"action": "remove_member", "user_id": str(victim.id)},
            follow=True,
        )
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("only admins can remove" in str(m).lower() for m in msgs))
