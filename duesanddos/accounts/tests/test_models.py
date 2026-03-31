from django.test import TestCase

from accounts.models import (
    CustomUser,
    Profile,
    Household,
    HouseholdMember,
    Expense,
    ExpenseSplit,
    ActivityLog,
)
from django.contrib.auth import get_user_model

from unittest.mock import Mock, patch

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

    def test_save_deletes_old_avatar_when_avatar_changes(self):
        old_file = Mock()
        old_file.name = "profile_pics/old.gif"
        old_file.storage.delete = Mock()

        new_file = Mock()

        with patch("accounts.models.Profile.objects.get") as mock_get, patch(
            "django.db.models.Model.save", return_value=None
        ):
            mock_get.return_value = Mock(avatar=old_file)
            self.profile.avatar = new_file
            self.profile.save()

        old_file.storage.delete.assert_called_once_with("profile_pics/old.gif")


# ---------------------------------------------------------------------------
# Model: UploadToPath and Household tests
# ---------------------------------------------------------------------------


class HouseholdModelTests(TestCase):
    def test_str_returns_name(self):
        hh = Household.objects.create(name="Test House")
        self.assertEqual(str(hh), "Test House")

    def test_default_fields_are_empty(self):
        hh = Household.objects.create(name="Empty House")
        self.assertEqual(hh.description, "")
        self.assertEqual(hh.default_rules, "")

    def test_fields_can_be_saved(self):
        hh = Household.objects.create(
            name="Filled House",
            description="A nice house",
            default_rules="No shoes inside",
        )
        hh.refresh_from_db()
        self.assertEqual(hh.description, "A nice house")
        self.assertEqual(hh.default_rules, "No shoes inside")


class HouseholdMemberModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="memtest",
            email="memtest@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Member House")
        self.member = HouseholdMember.objects.create(
            user=self.user, household=self.hh, role="Admin"
        )

    def test_str_returns_formatted_string(self):
        expected = "memtest - Member House (Admin)"
        self.assertEqual(str(self.member), expected)


class UploadToPathTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="uploadtest",
            email="upload@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_upload_path_has_correct_category(self):
        from accounts.models import UploadToPath

        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.jpg")
        self.assertTrue(path.startswith("test_cat/"))

    def test_upload_path_includes_user_pk(self):
        from accounts.models import UploadToPath

        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.jpg")
        self.assertIn(f"uid_{self.user.pk}", path)

    def test_upload_path_ends_with_jpg(self):
        from accounts.models import UploadToPath

        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.png")
        self.assertTrue(path.endswith(".png"))

    def test_upload_path_no_extension_defaults_to_jpg(self):
        from accounts.models import UploadToPath

        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "noext")
        self.assertTrue(path.endswith(".jpg"))

    def test_deconstruct_returns_correct_path(self):
        from accounts.models import UploadToPath

        uploader = UploadToPath("mycat")
        name, args, kwargs = uploader.deconstruct()
        self.assertEqual(name, "accounts.models.UploadToPath")
        self.assertEqual(args, ["mycat"])
        self.assertEqual(kwargs, {})

    def test_upload_path_falls_back_to_unknown_without_user_or_user_id(self):
        from accounts.models import UploadToPath

        class DummyInstance:
            pass

        uploader = UploadToPath("test_cat")
        path = uploader(DummyInstance(), "photo.jpg")
        self.assertIn("uid_unknown", path)


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="payer",
            email="payer@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Expense House")
        HouseholdMember.objects.create(user=self.user, household=self.hh, role="Admin")

    def test_expense_str_returns_title_and_amount(self):
        expense = Expense.objects.create(
            title="Groceries",
            amount="42.50",
            payer=self.user,
            household=self.hh,
            split_type="EQUAL",
        )
        self.assertEqual(str(expense), "Groceries ($42.50)")

    def test_expense_default_split_type_is_equal(self):
        expense = Expense.objects.create(
            title="Utilities",
            amount="90.00",
            payer=self.user,
            household=self.hh,
        )
        self.assertEqual(expense.split_type, "EQUAL")

    def test_expense_accepts_amount_split_type(self):
        expense = Expense.objects.create(
            title="Dinner",
            amount="75.00",
            payer=self.user,
            household=self.hh,
            split_type="AMOUNT",
        )
        self.assertEqual(expense.split_type, "AMOUNT")


class ExpenseSplitModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="splituser",
            email="split@example.com",
            password=TEST_PASSWORD,
        )
        self.user2 = CustomUser.objects.create_user(
            username="splituser2",
            email="split2@example.com",
            password=TEST_PASSWORD,
        )
        self.hh = Household.objects.create(name="Split House")
        HouseholdMember.objects.create(user=self.user, household=self.hh, role="Admin")
        HouseholdMember.objects.create(
            user=self.user2, household=self.hh, role="Member"
        )
        self.expense = Expense.objects.create(
            title="Internet",
            amount="60.00",
            payer=self.user,
            household=self.hh,
            split_type="EQUAL",
        )

    def test_expense_split_str_returns_expected_text(self):
        split = ExpenseSplit.objects.create(
            expense=self.expense,
            user=self.user,
            amount_owed="60.00",
        )
        self.assertEqual(
            str(split),
            "splituser owes $60.00 for Internet",
        )

    def test_expense_split_count_for_created_expense(self):
        expense = Expense.objects.create(
            title="Test Expense",
            amount="30.00",
            payer=self.user,
            household=self.hh,
            split_type="AMOUNT",
        )
        ExpenseSplit.objects.create(
            expense=expense, user=self.user, amount_owed="10.00"
        )
        ExpenseSplit.objects.create(
            expense=expense, user=self.user2, amount_owed="20.00"
        )

        self.assertEqual(expense.splits.count(), 2)


class ActivityLogModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="activityp", email="act@example.com", password="Pass123!"
        )
        self.household = Household.objects.create(name="Act House")
        self.log = ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_ADDED",
            details="Added test expense",
        )

    def test_activity_log_creation(self):
        self.assertEqual(self.log.action, "EXPENSE_ADDED")
        self.assertIn("Added test expense", self.log.details)
        self.assertTrue(self.log.id)

    def test_activity_log_ordering(self):
        log2 = ActivityLog.objects.create(
            user=self.user,
            household=self.household,
            action="EXPENSE_DELETED",
            details="Deleted test expense",
        )
        logs = ActivityLog.objects.all()
        # Ordering is -timestamp, so log2 should be first
        self.assertEqual(logs[0], log2)

    def test_activity_log_str(self):
        expected_str = (
            f"{self.user.username} - {self.log.action} at {self.log.timestamp}"
        )
        self.assertEqual(str(self.log), expected_str)
