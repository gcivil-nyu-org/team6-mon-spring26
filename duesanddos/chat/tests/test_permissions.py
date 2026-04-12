from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Profile
from households.models import Household, HouseholdMember

from chat.models import Conversation, ConversationParticipant

TEST_PASSWORD = "TestPass123!"


class ChatPermissionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="member1",
            email="member1@example.com",
            password=TEST_PASSWORD,
        )
        self.housemate = CustomUser.objects.create_user(
            username="member2",
            email="member2@example.com",
            password=TEST_PASSWORD,
        )
        self.stranger = CustomUser.objects.create_user(
            username="stranger",
            email="stranger@example.com",
            password=TEST_PASSWORD,
        )
        self.household = Household.objects.create(name="Home One")
        self.other_household = Household.objects.create(name="Home Two")

        for user in [self.user, self.housemate, self.stranger]:
            Profile.objects.create(user=user)

        HouseholdMember.objects.create(user=self.user, household=self.household)
        HouseholdMember.objects.create(user=self.housemate, household=self.household)
        HouseholdMember.objects.create(
            user=self.stranger, household=self.other_household
        )

        self.user.profile.active_household = self.household
        self.user.profile.save(update_fields=["active_household"])

        self.client.login(username="member1", password=TEST_PASSWORD)

    def test_user_cannot_access_conversation_from_another_household(self):
        conversation = Conversation.objects.create(
            household=self.other_household,
            conversation_type=Conversation.ConversationType.GROUP,
            created_by=self.stranger,
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.stranger,
        )

        response = self.client.get(reverse("chat:detail", args=[conversation.id]))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_start_dm_with_non_member(self):
        response = self.client.post(reverse("chat:start_dm", args=[self.stranger.id]))

        self.assertEqual(response.status_code, 404)

    def test_inaccessible_conversation_send_fails(self):
        conversation = Conversation.objects.create(
            household=self.household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=self.housemate,
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.housemate,
        )

        response = self.client.post(
            reverse("chat:send_message", args=[conversation.id]),
            {"body": "Not allowed"},
        )

        self.assertEqual(response.status_code, 404)

    def test_start_dm_with_self_is_invalid(self):
        response = self.client.post(reverse("chat:start_dm", args=[self.user.id]))
        self.assertEqual(response.status_code, 404)
