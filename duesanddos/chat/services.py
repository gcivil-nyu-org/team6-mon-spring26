from django.http import Http404

from households.models import HouseholdMember

from .models import Conversation, ConversationParticipant


def get_active_household_for_user(user):
    profile = user.profile
    household = profile.active_household
    if household is None:
        return None
    if not HouseholdMember.objects.filter(user=user, household=household).exists():
        profile.active_household = None
        profile.save(update_fields=["active_household"])
        return None
    return household


def ensure_chat_context(user):
    household = get_active_household_for_user(user)
    if household is None:
        return None, None
    group_conversation = Conversation.objects.ensure_household_group_conversation(
        household=household,
        created_by=user,
    )
    return household, group_conversation


def get_accessible_conversations(user, household):
    conversations = (
        Conversation.objects.accessible_to(user, household)
        .select_related("created_by", "household")
        .prefetch_related("participants__user", "messages__author")
        .order_by("-updated_at", "-id")
    )
    for conversation in conversations:
        if conversation.conversation_type == Conversation.ConversationType.GROUP:
            conversation.ensure_group_participants()
    return conversations


def get_conversation_or_404(user, household, conversation_id):
    conversation = (
        Conversation.objects.accessible_to(user, household)
        .select_related("household")
        .prefetch_related("participants__user")
        .filter(pk=conversation_id)
        .first()
    )
    if conversation is None:
        raise Http404("Conversation not found.")
    if conversation.conversation_type == Conversation.ConversationType.GROUP:
        conversation.ensure_group_participants()
        if not conversation.participants.filter(user=user).exists():
            raise Http404("Conversation not found.")
    return conversation


def get_or_create_dm(household, requester, target_user):
    return Conversation.objects.create_direct_message(
        household=household,
        created_by=requester,
        user_a=requester,
        user_b=target_user,
    )


def get_participant_or_404(conversation, user):
    participant = ConversationParticipant.objects.filter(
        conversation=conversation,
        user=user,
    ).first()
    if participant is None:
        raise Http404("Conversation not found.")
    return participant


def unread_counts_for_user(user, household):
    conversations = Conversation.objects.accessible_to(user, household)
    counts = {}
    total = 0
    participants = ConversationParticipant.objects.filter(
        conversation__in=conversations,
        user=user,
    ).select_related("conversation")
    for participant in participants:
        count = participant.unread_count
        counts[str(participant.conversation_id)] = count
        total += count
    return {"total_unread": total, "by_conversation": counts}
