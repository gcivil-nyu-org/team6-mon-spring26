from unittest.mock import Mock, PropertyMock, patch

from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser, Profile
from chores.models import Chore
from expenses.models import Expense
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message, MessageReference
from chat.services import (
    MESSAGE_PREVIEW_PLACEHOLDER,
    _resolve_reference_specs,
    compute_message_preview_text,
    ensure_chat_context,
    get_active_household_for_user,
    get_conversation_or_404,
    get_participant_or_404,
    normalize_message_body,
    serialize_message,
    serialize_reference,
    summarize_chore_assignees,
    summarize_chore_schedule,
)

TEST_PASSWORD = "TestPass123!"


class ChatServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="alpha",
            email="alpha@example.com",
            password=TEST_PASSWORD,
        )
        self.other = CustomUser.objects.create_user(
            username="beta",
            email="beta@example.com",
            password=TEST_PASSWORD,
        )
        self.third = CustomUser.objects.create_user(
            username="gamma",
            email="gamma@example.com",
            password=TEST_PASSWORD,
        )
        self.outsider = CustomUser.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password=TEST_PASSWORD,
        )

        self.household = Household.objects.create(name="Service House")
        self.other_household = Household.objects.create(name="Other House")

        self.profile = Profile.objects.create(
            user=self.user,
            active_household=self.household,
        )
        Profile.objects.create(user=self.other, active_household=self.household)
        Profile.objects.create(user=self.third, active_household=self.household)
        Profile.objects.create(
            user=self.outsider, active_household=self.other_household
        )

        HouseholdMember.objects.create(user=self.user, household=self.household)
        HouseholdMember.objects.create(user=self.other, household=self.household)
        HouseholdMember.objects.create(user=self.third, household=self.household)
        HouseholdMember.objects.create(
            user=self.outsider, household=self.other_household
        )

        self.conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.other,
        )

    def test_get_active_household_clears_stale_membership(self):
        HouseholdMember.objects.filter(
            user=self.user,
            household=self.household,
        ).delete()

        household = get_active_household_for_user(self.user)

        self.assertIsNone(household)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.active_household)

    def test_ensure_chat_context_returns_none_when_no_active_household(self):
        self.profile.active_household = None
        self.profile.save(update_fields=["active_household"])

        household, conversation = ensure_chat_context(self.user)

        self.assertIsNone(household)
        self.assertIsNone(conversation)

    def test_get_conversation_rejects_group_without_participant(self):
        fake_conversation = Mock()
        fake_conversation.conversation_type = Conversation.ConversationType.GROUP
        fake_conversation.participants.filter.return_value.exists.return_value = False

        queryset = Mock()
        queryset.select_related.return_value = queryset
        queryset.prefetch_related.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.first.return_value = fake_conversation

        with patch(
            "chat.services.Conversation.objects.accessible_to", return_value=queryset
        ):
            with self.assertRaises(Http404):
                get_conversation_or_404(self.user, self.household, 999)

    def test_get_participant_or_404_raises_for_missing_participant(self):
        with self.assertRaises(Http404):
            get_participant_or_404(self.conversation, self.third)

    def test_normalize_and_preview_helpers_cover_boundary_paths(self):
        with self.assertRaisesMessage(
            ValidationError,
            f"Message body cannot exceed {Message.MAX_BODY_LENGTH} chars.",
        ):
            normalize_message_body("x" * (Message.MAX_BODY_LENGTH + 1))

        self.assertEqual(
            compute_message_preview_text("", True), MESSAGE_PREVIEW_PLACEHOLDER
        )
        self.assertEqual(compute_message_preview_text("", False), "")

    def test_serialize_message_blank_avatar_when_url_unavailable(self):
        profile = self.user.profile
        profile.avatar = "avatars/test.png"
        profile.save(update_fields=["avatar"])

        message = Message.objects.create(
            conversation=self.conversation,
            author=self.user,
            body="Avatar test",
        )

        with patch.object(
            type(profile.avatar), "url", new_callable=PropertyMock
        ) as avatar_url:
            avatar_url.side_effect = ValueError("no file")
            payload = serialize_message(message, self.other)

        self.assertEqual(payload["author_avatar_url"], "")
        self.assertFalse(payload["is_own_message"])

    def test_serialize_reference_covers_live_chore_and_unavailable_expense(self):
        chore = Chore.objects.create(
            household=self.household,
            description="Vacuum living room",
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=False,
        )
        chore.assignees.add(self.user, self.other, self.third)

        message = Message.objects.create(
            conversation=self.conversation,
            author=self.user,
            body="refs",
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="18.20",
            payer=self.user,
            household=self.household,
        )

        chore_reference = MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.CHORE,
            chore=chore,
            position=0,
        )
        unavailable_expense_reference = MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=expense,
            position=1,
        )
        expense.delete()
        unavailable_expense_reference.refresh_from_db()

        chore_payload = serialize_reference(chore_reference)
        expense_payload = serialize_reference(unavailable_expense_reference)

        self.assertEqual(chore_payload["title"], "Vacuum living room")
        self.assertEqual(
            chore_payload["href"],
            f"{reverse('chores_list')}?highlight_chore={chore.id}",
        )
        self.assertTrue(chore_payload["is_available"])
        self.assertEqual(expense_payload["title"], "Expense unavailable")
        self.assertIsNone(expense_payload["href"])
        self.assertFalse(expense_payload["is_available"])

    def test_chore_summary_helpers_cover_due_time_and_assignee_variants(self):
        due_date = timezone.now().date()
        due_time = (
            timezone.now().replace(hour=17, minute=30, second=0, microsecond=0).time()
        )

        timed_chore = Chore.objects.create(
            household=self.household,
            description="Timed chore",
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=True,
            due_date=due_date,
            due_time=due_time,
        )
        untimed_chore = Chore.objects.create(
            household=self.household,
            description="One off",
            created_by=self.user,
            repeat_type="ONE_TIME",
            has_due_date=False,
        )
        daily_chore = Chore.objects.create(
            household=self.household,
            description="Daily",
            created_by=self.user,
            repeat_type="DAILY",
        )
        specific_weekly_chore = Chore.objects.create(
            household=self.household,
            description="Specific days",
            created_by=self.user,
            repeat_type="WEEKLY",
            repeat_monday=True,
            repeat_wednesday=True,
        )
        unspecific_weekly_chore = Chore.objects.create(
            household=self.household,
            description="Weekly fallback",
            created_by=self.user,
            repeat_type="WEEKLY",
        )
        duo_chore = Chore.objects.create(
            household=self.household,
            description="Duo",
            created_by=self.user,
            repeat_type="WEEKLY",
        )
        trio_chore = Chore.objects.create(
            household=self.household,
            description="Trio",
            created_by=self.user,
            repeat_type="WEEKLY",
        )
        duo_chore.assignees.add(self.user, self.other)
        trio_chore.assignees.add(self.user, self.other, self.third)

        self.assertIn("Due", summarize_chore_schedule(timed_chore))
        self.assertIn("5:30 PM", summarize_chore_schedule(timed_chore))
        self.assertEqual(summarize_chore_schedule(untimed_chore), "One-time")
        self.assertEqual(summarize_chore_schedule(daily_chore), "Repeats daily")
        self.assertEqual(
            summarize_chore_schedule(specific_weekly_chore),
            "Repeats Mon / Wed",
        )
        self.assertEqual(
            summarize_chore_schedule(unspecific_weekly_chore),
            "Repeats weekly",
        )
        self.assertEqual(
            summarize_chore_assignees(duo_chore),
            "Assigned to alpha and beta",
        )
        self.assertEqual(
            summarize_chore_assignees(trio_chore),
            "Assigned to alpha +2 more",
        )

    def test_resolve_reference_specs_rejects_invalid_payload_shapes(self):
        expense = Expense.objects.create(
            title="Dinner",
            amount="12.00",
            payer=self.user,
            household=self.household,
        )
        inactive_chore = Chore.objects.create(
            household=self.household,
            description="Inactive chore",
            created_by=self.user,
            is_active=False,
            has_due_date=True,
            due_date=timezone.now().date(),
        )

        with self.assertRaisesMessage(ValidationError, "Invalid reference payload."):
            _resolve_reference_specs(
                conversation=self.conversation,
                reference_types=["EXPENSE"],
                reference_ids=[],
            )

        with self.assertRaisesMessage(ValidationError, "Invalid reference payload."):
            _resolve_reference_specs(
                conversation=self.conversation,
                reference_types=[""],
                reference_ids=[str(expense.id)],
            )

        with self.assertRaisesMessage(
            ValidationError,
            "One or more selected chores are unavailable.",
        ):
            _resolve_reference_specs(
                conversation=self.conversation,
                reference_types=[MessageReference.ReferenceType.CHORE],
                reference_ids=[str(inactive_chore.id)],
            )

        with self.assertRaisesMessage(ValidationError, "Invalid reference payload."):
            _resolve_reference_specs(
                conversation=self.conversation,
                reference_types=["INVALID"],
                reference_ids=[str(expense.id)],
            )
