from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser, Profile
from chores.models import Chore
from expenses.models import Expense
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message, MessageReference
from chat.services import create_message_with_references, serialize_reference

TEST_PASSWORD = "TestPass123!"


class ChatModelTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="owner",
            email="owner@example.com",
            password=TEST_PASSWORD,
        )
        self.member = CustomUser.objects.create_user(
            username="member",
            email="member@example.com",
            password=TEST_PASSWORD,
        )
        self.outsider = CustomUser.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Alpha Home")
        self.other_household = Household.objects.create(name="Beta Home")

        for user in [self.owner, self.member, self.outsider]:
            Profile.objects.create(user=user)

        HouseholdMember.objects.create(
            user=self.owner, household=self.household, role="Admin"
        )
        HouseholdMember.objects.create(user=self.member, household=self.household)
        HouseholdMember.objects.create(
            user=self.outsider, household=self.other_household
        )

    def test_can_create_group_conversation_for_household(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
            title="Household Chat",
        )

        self.assertEqual(conversation.household, self.household)
        self.assertEqual(
            conversation.conversation_type, Conversation.ConversationType.GROUP
        )

    def test_dm_requires_same_household_members(self):
        conversation = Conversation(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.owner,
        )
        conversation.full_clean()
        conversation.save()

        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.owner,
        )
        participant = ConversationParticipant(
            conversation=conversation,
            user=self.outsider,
        )

        with self.assertRaises(ValidationError):
            participant.full_clean()

    def test_cannot_create_self_dm(self):
        with self.assertRaises(ValidationError):
            Conversation.objects.create_direct_message(
                household=self.household,
                created_by=self.owner,
                user_a=self.owner,
                user_b=self.owner,
            )

    def test_participant_uniqueness_enforced(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )

        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )
        with self.assertRaises(IntegrityError):
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=self.owner,
            )

    def test_message_requires_participant_author(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )

        message = Message(
            conversation=conversation,
            author=self.member,
            body="Hello there",
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_with_text_only_is_valid(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )

        message = Message(
            conversation=conversation,
            author=self.owner,
            body="  Checking in  ",
        )

        message.full_clean()
        self.assertEqual(message.body, "Checking in")

    def test_message_with_neither_text_nor_references_is_invalid(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )

        message = Message(
            conversation=conversation,
            author=self.owner,
            body="   ",
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_reference_must_point_to_exactly_one_domain_object(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="Reference payload",
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="42.50",
            payer=self.owner,
            household=self.household,
        )
        chore = Chore.objects.create(
            household=self.household,
            description="Take out recycling",
            created_by=self.owner,
            has_due_date=True,
            due_date=timezone.now().date(),
        )

        with self.assertRaises(ValidationError):
            MessageReference(
                message=message,
                reference_type=MessageReference.ReferenceType.EXPENSE,
                expense=expense,
                chore=chore,
                position=0,
            ).full_clean()

        with self.assertRaises(ValidationError):
            MessageReference(
                message=message,
                reference_type=MessageReference.ReferenceType.EXPENSE,
                position=0,
            ).full_clean()

    def test_reference_must_match_message_household(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="Cross-household reference",
        )
        outsider_expense = Expense.objects.create(
            title="Other home item",
            amount="12.00",
            payer=self.outsider,
            household=self.other_household,
        )

        with self.assertRaises(ValidationError):
            MessageReference(
                message=message,
                reference_type=MessageReference.ReferenceType.EXPENSE,
                expense=outsider_expense,
                position=0,
            ).full_clean()

    def test_reference_snapshot_is_stored_at_send_time_and_used_after_live_data_changes(
        self,
    ):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )

        expense = Expense.objects.create(
            title="Groceries",
            amount="42.50",
            payer=self.owner,
            household=self.household,
        )
        chore = Chore.objects.create(
            household=self.household,
            description="Take out recycling",
            created_by=self.owner,
            has_due_date=True,
            due_date=timezone.now().date(),
        )
        chore.assignees.add(self.member)

        message = create_message_with_references(
            conversation=conversation,
            author=self.owner,
            body="",
            reference_types=[
                MessageReference.ReferenceType.EXPENSE,
                MessageReference.ReferenceType.CHORE,
            ],
            reference_ids=[str(expense.id), str(chore.id)],
        )

        references = list(message.references.order_by("position"))
        expense_id = expense.id
        chore_id = chore.id
        self.assertEqual(references[0].snapshot_title, "Groceries")
        self.assertEqual(references[0].snapshot_subtitle, "$42.50 • owner")
        self.assertEqual(
            references[0].snapshot_href,
            f'{reverse("expenses_list")}?highlight_expense={expense_id}',
        )
        self.assertEqual(references[1].snapshot_title, "Take out recycling")
        self.assertEqual(references[1].snapshot_meta, "Assigned to member")
        self.assertEqual(
            references[1].snapshot_href,
            f'{reverse("chores_list")}?highlight_chore={chore_id}',
        )

        expense.title = "Changed title"
        expense.save(update_fields=["title"])
        chore.delete()

        serialized_expense = serialize_reference(references[0])
        serialized_chore = serialize_reference(references[1])
        self.assertEqual(serialized_expense["title"], "Groceries")
        self.assertEqual(
            serialized_expense["href"],
            f'{reverse("expenses_list")}?highlight_expense={expense_id}',
        )
        self.assertTrue(serialized_expense["is_available"])
        self.assertEqual(serialized_chore["title"], "Take out recycling")
        self.assertEqual(
            serialized_chore["href"],
            f'{reverse("chores_list")}?highlight_chore={chore_id}',
        )
        self.assertTrue(serialized_chore["is_available"])

    def test_inactive_chore_cannot_be_attached(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="Inactive chore reference",
        )
        inactive_chore = Chore.objects.create(
            household=self.household,
            description="Old recurring task",
            created_by=self.owner,
            is_active=False,
            has_due_date=True,
            due_date=timezone.now().date(),
        )

        with self.assertRaises(ValidationError):
            MessageReference(
                message=message,
                reference_type=MessageReference.ReferenceType.CHORE,
                chore=inactive_chore,
                position=0,
            ).full_clean()

    def test_reference_ordering_is_preserved_by_position(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.owner
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="Ordered refs",
        )
        first_expense = Expense.objects.create(
            title="Groceries",
            amount="10.00",
            payer=self.owner,
            household=self.household,
        )
        second_expense = Expense.objects.create(
            title="Utilities",
            amount="90.00",
            payer=self.owner,
            household=self.household,
        )

        MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=second_expense,
            position=1,
        )
        MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=first_expense,
            position=0,
        )

        ordered_titles = [
            reference.expense.title
            for reference in message.references.order_by("position")
        ]
        self.assertEqual(ordered_titles, ["Groceries", "Utilities"])

    def test_unread_count_ignores_own_messages_and_old_messages(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.owner,
        )
        owner_participant = ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.owner,
        )
        member_participant = ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.member,
        )
        first = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="First",
        )
        second = Message.objects.create(
            conversation=conversation,
            author=self.member,
            body="Second",
        )
        third = Message.objects.create(
            conversation=conversation,
            author=self.owner,
            body="Third",
        )

        owner_participant.last_read_message = first
        owner_participant.last_read_at = timezone.now()
        owner_participant.save(update_fields=["last_read_message", "last_read_at"])

        self.assertEqual(owner_participant.unread_count, 1)
        self.assertEqual(member_participant.unread_count, 2)
        self.assertNotEqual(second.id, third.id)

    def test_conversation_ordering_updates_when_new_message_added(self):
        first_conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.owner,
            updated_at=timezone.now() - timezone.timedelta(hours=1),
        )
        second_conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=first_conversation,
            user=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=second_conversation,
            user=self.owner,
        )
        ConversationParticipant.objects.create(
            conversation=second_conversation,
            user=self.member,
        )

        Message.objects.create(
            conversation=first_conversation,
            author=self.owner,
            body="Newest activity",
        )

        ordered = list(
            Conversation.objects.filter(household=self.household).order_by(
                "-updated_at"
            )
        )
        self.assertEqual(ordered[0], first_conversation)
