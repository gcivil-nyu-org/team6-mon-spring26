from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Profile
from chores.models import Chore
from expenses.models import Expense
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant, Message, MessageReference

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

    def test_chat_page_context_includes_reference_picker_datasets(self):
        expense = Expense.objects.create(
            title="Groceries",
            amount="84.29",
            payer=self.user,
            household=self.household,
        )
        active_chore = Chore.objects.create(
            household=self.household,
            description="Vacuum living room",
            created_by=self.user,
            has_due_date=True,
            due_date=expense.date_spent,
        )
        inactive_chore = Chore.objects.create(
            household=self.household,
            description="Archived task",
            created_by=self.user,
            is_active=False,
            has_due_date=True,
            due_date=expense.date_spent,
        )

        response = self.client.get(reverse("chat:index"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("expense_picker_items", response.context)
        self.assertIn("chore_picker_items", response.context)
        self.assertEqual(response.context["expense_picker_items"][0]["id"], expense.id)
        chore_ids = [item["id"] for item in response.context["chore_picker_items"]]
        self.assertIn(active_chore.id, chore_ids)
        self.assertNotIn(inactive_chore.id, chore_ids)

    def test_sending_card_only_expense_message_succeeds(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="84.29",
            payer=self.user,
            household=self.household,
        )

        response = self.client.post(
            reverse("chat:send_message", args=[conversation.id]),
            {
                "body": "   ",
                "reference_type[]": ["EXPENSE"],
                "reference_id[]": [str(expense.id)],
            },
        )

        self.assertRedirects(response, reverse("chat:detail", args=[conversation.id]))
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.body, "")
        self.assertEqual(message.references.count(), 1)
        self.assertEqual(message.references.get().expense, expense)

    def test_sending_mixed_references_with_text_preserves_order(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="84.29",
            payer=self.user,
            household=self.household,
        )
        chore = Chore.objects.create(
            household=self.household,
            description="Vacuum living room",
            created_by=self.user,
            has_due_date=True,
            due_date=expense.date_spent,
        )

        response = self.client.post(
            reverse("chat:send_message", args=[conversation.id]),
            {
                "body": "Please handle these",
                "reference_type[]": ["EXPENSE", "CHORE"],
                "reference_id[]": [str(expense.id), str(chore.id)],
            },
        )

        self.assertRedirects(response, reverse("chat:detail", args=[conversation.id]))
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.body, "Please handle these")
        references = list(message.references.order_by("position"))
        self.assertEqual(
            [reference.reference_type for reference in references],
            [
                MessageReference.ReferenceType.EXPENSE,
                MessageReference.ReferenceType.CHORE,
            ],
        )

    def test_invalid_reference_payload_fails_without_creating_message(self):
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
            {
                "body": "Should fail",
                "reference_type[]": ["EXPENSE"],
                "reference_id[]": ["999999"],
            },
        )

        self.assertRedirects(response, reverse("chat:detail", args=[conversation.id]))
        self.assertFalse(Message.objects.filter(conversation=conversation).exists())

    def test_card_only_latest_message_uses_shared_references_preview(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="84.29",
            payer=self.user,
            household=self.household,
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.user,
            body="card placeholder",
        )
        MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=expense,
            position=0,
        )
        message.body = ""
        message.save(update_fields=["body"])

        response = self.client.get(reverse("chat:detail", args=[conversation.id]))

        self.assertContains(response, "Shared references")

    def test_thread_renders_reference_cards_before_text_and_unavailable_stub(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.user,
        )
        ConversationParticipant.objects.create(
            conversation=conversation, user=self.user
        )
        expense = Expense.objects.create(
            title="Groceries",
            amount="84.29",
            payer=self.user,
            household=self.household,
        )
        chore = Chore.objects.create(
            household=self.household,
            description="Vacuum living room",
            created_by=self.user,
            has_due_date=True,
            due_date=expense.date_spent,
        )
        message = Message.objects.create(
            conversation=conversation,
            author=self.user,
            body="Please review both items",
        )
        MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.EXPENSE,
            expense=expense,
            position=0,
        )
        missing_reference = MessageReference.objects.create(
            message=message,
            reference_type=MessageReference.ReferenceType.CHORE,
            chore=chore,
            position=1,
        )
        chore.delete()

        response = self.client.get(reverse("chat:detail", args=[conversation.id]))

        content = response.content.decode()
        self.assertLess(
            content.index("chat-message-references"),
            content.rindex("Please review both items"),
        )
        self.assertContains(
            response,
            f'href="{reverse("expenses_list")}?highlight_expense={expense.id}"',
            html=False,
        )
        self.assertContains(response, "Chore unavailable")
        self.assertContains(
            response,
            f'data-reference-id="{missing_reference.id}"',
            html=False,
        )
        self.assertNotContains(response, "<p></p>", html=False)
