from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Profile
from expenses.models import Expense
from households.models import Household, HouseholdMember

from chat.models import (
    Conversation,
    ConversationParticipant,
    HiddenMessage,
    Message,
    MessageReference,
)
from chat.services import compute_message_preview_text

TEST_PASSWORD = "TestPass123!"


class ChatMessageDeletionTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user(
            username="author",
            email="author@example.com",
            password=TEST_PASSWORD,
        )
        self.peer = CustomUser.objects.create_user(
            username="peer",
            email="peer@example.com",
            password=TEST_PASSWORD,
        )
        self.outsider = CustomUser.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Deletion House")
        self.other_household = Household.objects.create(name="Other House")

        Profile.objects.create(user=self.author, active_household=self.household)
        Profile.objects.create(user=self.peer, active_household=self.household)
        Profile.objects.create(
            user=self.outsider, active_household=self.other_household
        )

        HouseholdMember.objects.create(user=self.author, household=self.household)
        HouseholdMember.objects.create(user=self.peer, household=self.household)
        HouseholdMember.objects.create(
            user=self.outsider, household=self.other_household
        )

        self.conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.author,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.author,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.peer,
        )

        self.message = Message.objects.create(
            conversation=self.conversation,
            author=self.author,
            body="Original body",
        )

    def login(self, user):
        self.client.logout()
        self.client.login(username=user.username, password=TEST_PASSWORD)

    def test_author_can_delete_for_everyone(self):
        self.login(self.author)

        response = self.client.post(
            reverse("chat:delete_for_everyone", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["message"]["is_deleted"])
        self.assertEqual(payload["message"]["deleted_label"], "Message deleted")
        self.assertEqual(payload["message"]["body"], "")
        self.message.refresh_from_db()
        self.assertIsNotNone(self.message.deleted_at)
        self.assertEqual(self.message.deleted_by_id, self.author.id)

    def test_non_author_cannot_delete_for_everyone(self):
        self.login(self.peer)

        response = self.client.post(
            reverse("chat:delete_for_everyone", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 403)
        self.message.refresh_from_db()
        self.assertIsNone(self.message.deleted_at)

    def test_participant_can_delete_for_me_on_other_users_message(self):
        self.login(self.peer)

        response = self.client.post(
            reverse("chat:delete_for_me", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            HiddenMessage.objects.filter(message=self.message, user=self.peer).exists()
        )

    def test_participant_can_delete_for_me_on_own_message(self):
        own_message = Message.objects.create(
            conversation=self.conversation,
            author=self.peer,
            body="Peer message",
        )
        self.login(self.peer)

        response = self.client.post(
            reverse("chat:delete_for_me", args=[own_message.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            HiddenMessage.objects.filter(message=own_message, user=self.peer).exists()
        )

    def test_delete_endpoints_are_idempotent(self):
        self.login(self.peer)
        delete_for_me_url = reverse("chat:delete_for_me", args=[self.message.id])
        response1 = self.client.post(delete_for_me_url)
        response2 = self.client.post(delete_for_me_url)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(
            HiddenMessage.objects.filter(message=self.message, user=self.peer).count(),
            1,
        )

        self.login(self.author)
        delete_for_everyone_url = reverse(
            "chat:delete_for_everyone", args=[self.message.id]
        )
        response3 = self.client.post(delete_for_everyone_url)
        response4 = self.client.post(delete_for_everyone_url)
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(response4.status_code, 200)
        self.message.refresh_from_db()
        self.assertIsNotNone(self.message.deleted_at)

    def test_hidden_messages_are_excluded_for_acting_user_only(self):
        self.login(self.peer)
        self.client.post(reverse("chat:delete_for_me", args=[self.message.id]))
        peer_payload = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        ).json()
        self.assertEqual(peer_payload["messages"], [])

        self.login(self.author)
        author_payload = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        ).json()
        self.assertEqual(len(author_payload["messages"]), 1)
        self.assertEqual(author_payload["messages"][0]["id"], self.message.id)

    def test_shared_deleted_messages_serialize_tombstone_and_hide_references(self):
        expense = Expense.objects.create(
            title="Bill",
            amount="25.00",
            payer=self.author,
            household=self.household,
        )
        MessageReference.objects.create(
            message=self.message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=expense,
            position=0,
        )

        self.login(self.author)
        self.client.post(reverse("chat:delete_for_everyone", args=[self.message.id]))
        payload = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        ).json()

        self.assertEqual(len(payload["messages"]), 1)
        serialized = payload["messages"][0]
        self.assertTrue(serialized["is_deleted"])
        self.assertEqual(serialized["preview_text"], "Message deleted")
        self.assertEqual(serialized["references"], [])

    def test_preview_text_uses_deleted_placeholder(self):
        preview = compute_message_preview_text(
            body="Will be ignored",
            has_references=True,
            is_deleted=True,
        )
        self.assertEqual(preview, "Message deleted")

    def test_chat_page_omits_hidden_messages_for_request_user(self):
        self.login(self.peer)
        self.client.post(reverse("chat:delete_for_me", args=[self.message.id]))

        response = self.client.get(reverse("chat:detail", args=[self.conversation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Original body")

    def test_polling_marks_shared_deleted_messages(self):
        self.login(self.author)
        self.client.post(reverse("chat:delete_for_everyone", args=[self.message.id]))
        payload = self.client.get(
            reverse("chat:messages", args=[self.conversation.id])
        ).json()

        self.assertEqual(payload["messages"][0]["is_deleted"], True)
        self.assertEqual(payload["messages"][0]["deleted_label"], "Message deleted")
        self.assertFalse(payload["messages"][0]["references"])

    def test_deletion_endpoints_enforce_conversation_access(self):
        other_conversation = Conversation.objects.create(
            household=self.other_household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.outsider,
        )
        ConversationParticipant.objects.create(
            conversation=other_conversation,
            user=self.outsider,
        )
        inaccessible_message = Message.objects.create(
            conversation=other_conversation,
            author=self.outsider,
            body="Private",
        )
        self.login(self.peer)

        response_for_me = self.client.post(
            reverse("chat:delete_for_me", args=[inaccessible_message.id])
        )
        response_for_everyone = self.client.post(
            reverse("chat:delete_for_everyone", args=[inaccessible_message.id])
        )

        self.assertEqual(response_for_me.status_code, 404)
        self.assertEqual(response_for_everyone.status_code, 404)

    def test_hidden_message_string_representation(self):
        hidden = HiddenMessage.objects.create(message=self.message, user=self.peer)
        rendered = str(hidden)
        self.assertIn(str(self.message.id), rendered)
        self.assertIn(str(self.peer.id), rendered)

    def test_delete_for_me_requires_post(self):
        self.login(self.peer)

        response = self.client.get(
            reverse("chat:delete_for_me", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"], "POST required.")

    def test_delete_for_everyone_requires_post(self):
        self.login(self.author)

        response = self.client.get(
            reverse("chat:delete_for_everyone", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"], "POST required.")

    def test_delete_endpoints_return_404_when_message_missing(self):
        self.login(self.peer)

        response = self.client.post(reverse("chat:delete_for_me", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_delete_endpoints_return_404_when_no_active_household(self):
        no_house_user = CustomUser.objects.create_user(
            username="nohouse",
            email="nohouse@example.com",
            password=TEST_PASSWORD,
        )
        Profile.objects.create(user=no_house_user, active_household=None)
        self.login(no_house_user)

        response = self.client.post(
            reverse("chat:delete_for_me", args=[self.message.id])
        )

        self.assertEqual(response.status_code, 404)
