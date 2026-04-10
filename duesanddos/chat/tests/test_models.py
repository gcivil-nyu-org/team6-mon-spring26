from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message

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
