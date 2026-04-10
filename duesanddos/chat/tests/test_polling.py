from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message

TEST_PASSWORD = "TestPass123!"


class ChatPollingTests(TestCase):
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
        self.outsider = CustomUser.objects.create_user(
            username="gamma",
            email="gamma@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Polling House")
        self.other_household = Household.objects.create(name="Other House")

        Profile.objects.create(user=self.user, active_household=self.household)
        Profile.objects.create(user=self.other, active_household=self.household)
        Profile.objects.create(
            user=self.outsider, active_household=self.other_household
        )

        HouseholdMember.objects.create(user=self.user, household=self.household)
        HouseholdMember.objects.create(user=self.other, household=self.household)
        HouseholdMember.objects.create(
            user=self.outsider, household=self.other_household
        )

        self.conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.user,
        )
        self.user_participant = ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.user,
        )
        self.other_participant = ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.other,
        )
        self.first = Message.objects.create(
            conversation=self.conversation,
            author=self.user,
            body="First",
        )
        self.second = Message.objects.create(
            conversation=self.conversation,
            author=self.other,
            body="Second",
        )

        self.client.login(username="alpha", password=TEST_PASSWORD)

    def test_messages_endpoint_returns_only_items_after_after_id(self):
        response = self.client.get(
            reverse("chat:messages", args=[self.conversation.id]),
            {"after_id": self.first.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversation_id"], self.conversation.id)
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["id"], self.second.id)
        self.assertFalse(payload["has_more"])

    def test_messages_endpoint_returns_expected_shape(self):
        response = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        )

        payload = response.json()
        message = payload["messages"][0]
        self.assertIn("author_id", message)
        self.assertIn("author_username", message)
        self.assertIn("author_avatar_url", message)
        self.assertIn("body", message)
        self.assertIn("created_at", message)
        self.assertIn("is_own_message", message)
        self.assertIn("server_time", payload)

    def test_unread_counts_update_after_incoming_message(self):
        Message.objects.create(
            conversation=self.conversation,
            author=self.other,
            body="Unread message",
        )

        response = self.client.get(reverse("chat:unread_counts"))

        payload = response.json()
        self.assertEqual(payload["total_unread"], 2)
        self.assertEqual(payload["by_conversation"][str(self.conversation.id)], 2)

    def test_mark_read_endpoint_clears_unread_count(self):
        response = self.client.post(
            reverse("chat:mark_read", args=[self.conversation.id])
        )

        self.assertEqual(response.status_code, 200)
        self.user_participant.refresh_from_db()
        self.assertEqual(self.user_participant.last_read_message, self.second)

        unread_response = self.client.get(reverse("chat:unread_counts"))
        payload = unread_response.json()
        self.assertEqual(payload["total_unread"], 0)

    def test_polling_endpoints_deny_non_participants(self):
        self.client.logout()
        self.client.login(username="gamma", password=TEST_PASSWORD)

        message_response = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        )
        unread_response = self.client.get(reverse("chat:unread_counts"))
        mark_read_response = self.client.post(
            reverse("chat:mark_read", args=[self.conversation.id])
        )

        self.assertEqual(message_response.status_code, 404)
        self.assertEqual(unread_response.status_code, 200)
        self.assertEqual(unread_response.json()["total_unread"], 0)
        self.assertEqual(mark_read_response.status_code, 404)
