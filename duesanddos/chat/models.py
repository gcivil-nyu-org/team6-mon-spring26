from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Q
from django.utils import timezone


class ConversationQuerySet(models.QuerySet):
    def accessible_to(self, user, household):
        return self.filter(household=household, participants__user=user).distinct()


class ConversationManager(models.Manager):
    def get_queryset(self):
        return ConversationQuerySet(self.model, using=self._db)

    def accessible_to(self, user, household):
        return self.get_queryset().accessible_to(user, household)

    def ensure_household_group_conversation(self, household, created_by):
        conversation = (
            self.filter(
                household=household,
                conversation_type=Conversation.ConversationType.GROUP,
            )
            .order_by("id")
            .first()
        )
        if conversation is None:
            conversation = self.create(
                household=household,
                conversation_type=Conversation.ConversationType.GROUP,
                created_by=created_by,
                title="Household Chat",
            )
        conversation.ensure_group_participants()
        return conversation

    def get_direct_message(self, household, user_a, user_b):
        user_ids = sorted([user_a.id, user_b.id])
        return (
            self.filter(
                household=household,
                conversation_type=Conversation.ConversationType.DIRECT,
            )
            .annotate(
                participant_count=Count("participants", distinct=True),
                matched_users=Count(
                    "participants",
                    filter=Q(participants__user_id__in=user_ids),
                    distinct=True,
                ),
            )
            .filter(participant_count=2, matched_users=2)
            .first()
        )

    @transaction.atomic
    def create_direct_message(self, household, created_by, user_a, user_b):
        if user_a == user_b:
            raise ValidationError("You cannot start a direct message with yourself.")

        if not household.members.filter(user=user_a).exists():
            raise ValidationError("Both users must belong to the same household.")
        if not household.members.filter(user=user_b).exists():
            raise ValidationError("Both users must belong to the same household.")

        existing = self.get_direct_message(household, user_a, user_b)
        if existing is not None:
            return existing

        conversation = self.create(
            household=household,
            conversation_type=Conversation.ConversationType.DIRECT,
            created_by=created_by,
        )
        ConversationParticipant.objects.create(conversation=conversation, user=user_a)
        ConversationParticipant.objects.create(conversation=conversation, user=user_b)
        return conversation


class Conversation(models.Model):
    class ConversationType(models.TextChoices):
        GROUP = "group", "Group"
        DIRECT = "direct", "Direct"

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="chat_conversations",
    )
    conversation_type = models.CharField(
        max_length=16,
        choices=ConversationType.choices,
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConversationManager()

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["household", "updated_at"]),
        ]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.conversation_type == self.ConversationType.GROUP:
            return self.title or "Household Chat"

        participants = list(self.participants.select_related("user").all()[:2])
        if len(participants) == 2:
            usernames = sorted(
                [participant.user.username for participant in participants]
            )
            return f"{usernames[0]} and {usernames[1]}"
        return "Direct Message"

    def ensure_group_participants(self):
        if self.conversation_type != self.ConversationType.GROUP:
            return

        current_ids = set(self.participants.values_list("user_id", flat=True))
        missing = self.household.members.exclude(
            user_id__in=current_ids
        ).select_related("user")
        for membership in missing:
            ConversationParticipant.objects.create(
                conversation=self,
                user=membership.user,
            )


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_participations",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey(
        "Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="chat_unique_participant_per_conversation",
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"

    def clean(self):
        if not self.conversation_id or not self.user_id:
            return
        if not self.conversation.household.members.filter(user=self.user).exists():
            raise ValidationError("Participants must be members of the household.")

    @property
    def unread_count(self):
        queryset = self.conversation.messages.exclude(author=self.user)
        if self.last_read_message_id:
            queryset = queryset.filter(id__gt=self.last_read_message_id)
        return queryset.count()

    def mark_read(self, message=None):
        if message is None:
            message = self.conversation.messages.order_by("-id").first()
        if message is None:
            return
        self.last_read_message = message
        self.last_read_at = timezone.now()
        self.save(update_fields=["last_read_message", "last_read_at"])


class Message(models.Model):
    MAX_BODY_LENGTH = 2000

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    body = models.TextField(max_length=MAX_BODY_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.author} in {self.conversation_id}"

    def clean(self):
        if not self.body or not self.body.strip():
            raise ValidationError({"body": "Message body cannot be empty."})
        self.body = self.body.strip()
        if len(self.body) > self.MAX_BODY_LENGTH:
            raise ValidationError(
                {"body": f"Message body cannot exceed {self.MAX_BODY_LENGTH} chars."}
            )
        if self.conversation_id and self.author_id:
            if not self.conversation.participants.filter(user=self.author).exists():
                raise ValidationError("Message author must be a participant.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        Conversation.objects.filter(pk=self.conversation_id).update(
            updated_at=timezone.now()
        )
