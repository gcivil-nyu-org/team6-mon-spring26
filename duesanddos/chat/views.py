from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import CustomUser
from households.models import HouseholdMember

from .models import Message
from .services import (
    compute_message_preview_text,
    create_message_with_references,
    delete_message_for_everyone,
    ensure_chat_context,
    get_accessible_conversations,
    get_conversation_or_404,
    get_visible_messages_queryset,
    get_chore_picker_items,
    get_or_create_dm,
    get_participant_or_404,
    get_expense_picker_items,
    hide_message_for_user,
    serialize_message,
    unread_counts_for_user,
)

MESSAGE_PAGE_SIZE = 50


def _serialize_message(message, request_user):
    return serialize_message(message, request_user)


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

    for conversation in conversations:
        latest = (
            get_visible_messages_queryset(conversation, request.user)
            .prefetch_related("references")
            .order_by("id")
            .last()
        )
        if latest is None:
            conversation.preview_text = "No Messages"
        else:
            conversation.preview_text = compute_message_preview_text(
                body=latest.body,
                has_references=latest.references.exists(),
                is_deleted=latest.deleted_at is not None,
            )

    thread_queryset = (
        get_visible_messages_queryset(selected_conversation, request.user)
        .select_related("author")
        .prefetch_related("references__expense__payer", "references__chore__assignees")
        .order_by("-id")[:MESSAGE_PAGE_SIZE]
    )
    thread_messages = list(thread_queryset)
    thread_messages.reverse()
    selected_participant.mark_read(thread_messages[-1] if thread_messages else None)
    serialized_thread_messages = [
        _serialize_message(message, request.user) for message in thread_messages
    ]

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
        "thread_messages": serialized_thread_messages,
        "other_members": other_members,
        "expense_picker_items": get_expense_picker_items(household),
        "chore_picker_items": get_chore_picker_items(household),
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
@transaction.atomic
def send_message(request, conversation_id):
    if request.method != "POST":
        return redirect("chat:detail", conversation_id=conversation_id)

    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return redirect("household_settings")

    conversation = get_conversation_or_404(request.user, household, conversation_id)
    get_participant_or_404(conversation, request.user)

    body = request.POST.get("body", "")
    reference_types = request.POST.getlist("reference_type[]") or request.POST.getlist(
        "reference_type"
    )
    reference_ids = request.POST.getlist("reference_id[]") or request.POST.getlist(
        "reference_id"
    )
    try:
        create_message_with_references(
            conversation=conversation,
            author=request.user,
            body=body,
            reference_types=reference_types,
            reference_ids=reference_ids,
        )
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            error_message = next(iter(exc.message_dict.values()))[0]
        else:
            error_message = exc.messages[0]
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

    queryset = (
        get_visible_messages_queryset(conversation, request.user)
        .select_related("author")
        .prefetch_related("references__expense__payer", "references__chore__assignees")
        .order_by("id")
    )
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
    latest_message = (
        get_visible_messages_queryset(conversation, request.user)
        .order_by("-id")
        .first()
    )
    participant.mark_read(latest_message)
    return JsonResponse({"status": "ok"})


def _get_message_in_user_household_or_404(request_user, message_id):
    household, _group_conversation = ensure_chat_context(request_user)
    if household is None:
        raise Http404("Conversation not found.")

    message = (
        Message.objects.select_related("author", "conversation")
        .prefetch_related("references__expense__payer", "references__chore__assignees")
        .filter(pk=message_id)
        .first()
    )
    if message is None:
        raise Http404("Message not found.")

    conversation = get_conversation_or_404(
        request_user, household, message.conversation_id
    )
    get_participant_or_404(conversation, request_user)
    return message


@login_required
@transaction.atomic
def delete_for_me(request, message_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)

    message = _get_message_in_user_household_or_404(request.user, message_id)
    hide_message_for_user(message, request.user)
    return JsonResponse({"status": "ok", "message_id": message.id})


@login_required
@transaction.atomic
def delete_for_everyone(request, message_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)

    message = _get_message_in_user_household_or_404(request.user, message_id)
    if message.author_id != request.user.id:
        return JsonResponse({"error": "Forbidden."}, status=403)

    delete_message_for_everyone(message, request.user)
    return JsonResponse(
        {
            "status": "ok",
            "message_id": message.id,
            "message": _serialize_message(message, request.user),
        }
    )
