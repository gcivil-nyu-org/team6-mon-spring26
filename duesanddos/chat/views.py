from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import CustomUser
from households.models import HouseholdMember

from .models import Message
from .services import (
    ensure_chat_context,
    get_accessible_conversations,
    get_conversation_or_404,
    get_or_create_dm,
    get_participant_or_404,
    unread_counts_for_user,
)

MESSAGE_PAGE_SIZE = 50


def _serialize_message(message, request_user):
    profile = getattr(message.author, "profile", None)
    avatar = ""
    if profile and profile.avatar:
        try:
            avatar = profile.avatar.url
        except ValueError:
            avatar = ""

    return {
        "id": message.id,
        "author_id": message.author_id,
        "author_username": message.author.username,
        "author_avatar_url": avatar,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "is_own_message": message.author_id == request_user.id,
    }


@login_required
def chat_index(request, conversation_id=None):
    household, group_conversation = ensure_chat_context(request.user)
    if household is None:
        return redirect("household_settings")

    conversations = list(get_accessible_conversations(request.user, household))
    selected_conversation = group_conversation
    if conversation_id is not None:
        selected_conversation = get_conversation_or_404(
            request.user, household, conversation_id
        )
    elif conversations:
        selected_conversation = conversations[0]

    selected_conversation = selected_conversation or group_conversation
    selected_participant = get_participant_or_404(selected_conversation, request.user)

    thread_messages = list(
        selected_conversation.messages.select_related("author").order_by("-id")[
            :MESSAGE_PAGE_SIZE
        ]
    )
    thread_messages.reverse()
    selected_participant.mark_read(thread_messages[-1] if thread_messages else None)

    other_members = (
        HouseholdMember.objects.filter(household=household)
        .exclude(user=request.user)
        .select_related("user")
        .order_by("user__username")
    )

    context = {
        "active_conversation": selected_conversation,
        "conversations": conversations,
        "group_conversation": group_conversation,
        "messages": thread_messages,
        "other_members": other_members,
        "message_max_length": Message.MAX_BODY_LENGTH,
        "poll_interval_ms": 5000,
    }
    return render(request, "chat/chat.html", context)


@login_required
def start_dm(request, user_id):
    if request.method != "POST":
        return redirect("chat:index")

    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return redirect("household_settings")

    target_user = get_object_or_404(CustomUser, pk=user_id)
    if target_user == request.user:
        raise Http404("Conversation not found.")
    if not household.members.filter(user=target_user).exists():
        raise Http404("Conversation not found.")

    conversation = get_or_create_dm(household, request.user, target_user)
    return redirect("chat:detail", conversation.id)


@login_required
def send_message(request, conversation_id):
    if request.method != "POST":
        return redirect("chat:detail", conversation_id=conversation_id)

    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return redirect("household_settings")

    conversation = get_conversation_or_404(request.user, household, conversation_id)
    get_participant_or_404(conversation, request.user)

    body = request.POST.get("body", "")
    try:
        message = Message(
            conversation=conversation,
            author=request.user,
            body=body,
        )
        message.save()
    except ValidationError as exc:
        error_message = exc.message_dict.get("body", exc.messages)[0]
        messages.error(request, error_message)
    else:
        messages.success(request, "Message sent.")

    return redirect("chat:detail", conversation.id)


@login_required
def messages_json(request, conversation_id):
    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return JsonResponse({"error": "No active household."}, status=403)

    conversation = get_conversation_or_404(request.user, household, conversation_id)
    get_participant_or_404(conversation, request.user)

    queryset = conversation.messages.select_related("author").order_by("id")
    after_id = request.GET.get("after_id")
    if after_id:
        queryset = queryset.filter(id__gt=after_id)
    else:
        last_ids = list(
            queryset.order_by("-id")[:MESSAGE_PAGE_SIZE].values_list("id", flat=True)
        )
        if last_ids:
            queryset = queryset.filter(id__in=last_ids)

    serialized = [_serialize_message(message, request.user) for message in queryset]
    return JsonResponse(
        {
            "messages": serialized,
            "has_more": False,
            "conversation_id": conversation.id,
            "server_time": timezone.now().isoformat(),
        }
    )


@login_required
def unread_counts(request):
    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return JsonResponse({"total_unread": 0, "by_conversation": {}})
    return JsonResponse(unread_counts_for_user(request.user, household))


@login_required
def mark_read(request, conversation_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)

    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return JsonResponse({"error": "No active household."}, status=403)

    conversation = get_conversation_or_404(request.user, household, conversation_id)
    participant = get_participant_or_404(conversation, request.user)
    latest_message = conversation.messages.order_by("-id").first()
    participant.mark_read(latest_message)
    return JsonResponse({"status": "ok"})
