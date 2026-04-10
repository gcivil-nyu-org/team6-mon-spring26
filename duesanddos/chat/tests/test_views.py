from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message

TEST_PASSWORD = "TestPass123!"


class ChatViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password=TEST_PASSWORD,
        )
        self.other = CustomUser.objects.create_user(
            username="other",
            email="other@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Main Home")
        HouseholdMember.objects.create(user=self.user, household=self.household)
        HouseholdMember.objects.create(user=self.other, household=self.household)
        self.profile = Profile.objects.create(
            user=self.user,
            active_household=self.household,
        )
        Profile.objects.create(user=self.other, active_household=self.household)
        self.client.login(username="viewer", password=TEST_PASSWORD)

    def test_unauthenticated_users_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("chat:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_users_without_active_household_redirected_to_household_settings(self):
        self.profile.active_household = None
        self.profile.save(update_fields=["active_household"])

        response = self.client.get(reverse("chat:index"))

        self.assertRedirects(response, reverse("household_settings"))

    def test_user_can_access_group_chat_for_active_household(self):
        response = self.client.get(reverse("chat:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/chat.html")
        self.assertContains(response, "Household Chat")

    def test_start_dm_with_same_household_member_reuses_conversation(self):
        existing = Conversation.objects.create_direct_message(
            household=self.household,
            created_by=self.user,
            user_a=self.user,
            user_b=self.other,
        )

        response = self.client.post(reverse("chat:start_dm", args=[self.other.id]))

        self.assertRedirects(response, reverse("chat:detail", args=[existing.id]))
        self.assertEqual(
            Conversation.objects.filter(
                household=self.household,
                conversation_type=Conversation.ConversationType.DIRECT,
            ).count(),
            1,
        )

    def test_sending_valid_message_succeeds(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )

        response = self.client.post(
            reverse("chat:send_message", args=[conversation.id]),
            {"body": "Hello household"},
        )

        self.assertRedirects(response, reverse("chat:detail", args=[conversation.id]))
        self.assertTrue(
            Message.objects.filter(
                conversation=conversation,
                author=self.user,
                body="Hello household",
            ).exists()
        )

    def test_sending_empty_message_fails(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )

        response = self.client.post(
            reverse("chat:send_message", args=[conversation.id]),
            {"body": "   "},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Message.objects.filter(conversation=conversation).exists())

    def test_chat_page_renders_conversation_list_and_empty_dm_state(self):
        response = self.client.get(reverse("chat:index"))

        self.assertContains(response, "Household Chat")
        self.assertContains(response, "Start a direct conversation")
        self.assertContains(response, 'class="chat-shell"')
        self.assertContains(response, 'data-sidebar-open="false"')
        self.assertContains(response, "data-live-status")
        self.assertContains(response, "data-character-count")

    def test_nav_badge_container_is_present(self):
        response = self.client.get(reverse("chat:index"))
        self.assertContains(response, 'id="chat-unread-badge"')

    def test_chat_page_renders_message_avatar_markers_and_thread_context(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.other,
        )
        Message.objects.create(
            conversation=conversation,
            author=self.other,
            body="Checking in with the house",
        )

        response = self.client.get(reverse("chat:detail", args=[conversation.id]))

        self.assertContains(response, "chat-message-avatar")
        self.assertContains(response, "chat-thread-badge")
        self.assertContains(response, 'data-message-author-initial="O"')
        self.assertContains(response, "Live updates")

    def test_chat_page_uses_thread_messages_context_without_populating_toast_messages(
        self,
    ):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.user,
        )
        Message.objects.create(
            conversation=conversation,
            author=self.user,
            body="Toast collision regression",
        )

        response = self.client.get(reverse("chat:detail", args=[conversation.id]))

        template_context = response.context[-1].dicts[-1]
        self.assertIn("thread_messages", template_context)
        self.assertNotIn("messages", template_context)
        self.assertContains(response, "Toast collision regression")
        self.assertNotContains(response, 'data-content="Toast collision regression"')
