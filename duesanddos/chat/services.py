from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse
from django.utils.text import Truncator

from chores.models import Chore
from expenses.models import Expense
from households.models import HouseholdMember

from .models import Conversation, ConversationParticipant, Message, MessageReference

MESSAGE_PREVIEW_PLACEHOLDER = "Shared references"


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
        .prefetch_related(
            "participants__user",
            "messages__author",
            "messages__references__expense__payer",
            "messages__references__chore__assignees",
        )
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


def normalize_message_body(body):
    normalized = (body or "").strip()
    if len(normalized) > Message.MAX_BODY_LENGTH:
        raise ValidationError(
            {"body": f"Message body cannot exceed {Message.MAX_BODY_LENGTH} chars."}
        )
    return normalized


def compute_message_preview_text(body="", has_references=False, max_length=72):
    trimmed = (body or "").strip()
    if trimmed:
        return Truncator(trimmed).chars(max_length)
    if has_references:
        return MESSAGE_PREVIEW_PLACEHOLDER
    return ""


def get_expense_picker_items(household):
    items = []
    expenses = household.expenses.select_related("payer").order_by("-date_spent", "-id")
    for expense in expenses:
        items.append(
            {
                "id": expense.id,
                "title": expense.title,
                "subtitle": f"${expense.amount:.2f} • {expense.payer.username}",
                "meta": f"Spent {_format_date(expense.date_spent)}",
            }
        )
    return items


def get_chore_picker_items(household):
    items = []
    chores = household.chores.filter(is_active=True).prefetch_related("assignees")
    for chore in chores.order_by("description"):
        items.append(
            {
                "id": chore.id,
                "title": chore.description,
                "subtitle": summarize_chore_schedule(chore),
                "meta": summarize_chore_assignees(chore),
            }
        )
    return items


def create_message_with_references(
    *,
    conversation,
    author,
    body,
    reference_types,
    reference_ids,
):
    normalized_body = normalize_message_body(body)
    reference_specs = _resolve_reference_specs(
        conversation=conversation,
        reference_types=reference_types,
        reference_ids=reference_ids,
    )
    if not normalized_body and not reference_specs:
        raise ValidationError("Add a message or at least one reference before sending.")

    message = Message(
        conversation=conversation,
        author=author,
        body=normalized_body,
    )
    message._allow_blank_body = bool(reference_specs)
    message.save(skip_composition_validation=bool(reference_specs))

    for position, spec in enumerate(reference_specs):
        snapshot = _build_reference_snapshot(spec["reference_type"], spec["object"])
        kwargs = {
            "message": message,
            "reference_type": spec["reference_type"],
            "snapshot_title": snapshot["title"],
            "snapshot_subtitle": snapshot["subtitle"],
            "snapshot_meta": snapshot["meta"],
            "snapshot_href": snapshot["href"],
            "snapshot_is_available": snapshot["is_available"],
            "position": position,
        }
        if spec["reference_type"] == MessageReference.ReferenceType.EXPENSE:
            kwargs["expense"] = spec["object"]
        else:
            kwargs["chore"] = spec["object"]

        reference = MessageReference(**kwargs)
        reference.full_clean()
        reference.save()

    return message


def serialize_message(message, request_user):
    profile = getattr(message.author, "profile", None)
    avatar = ""
    if profile and profile.avatar:
        try:
            avatar = profile.avatar.url
        except ValueError:
            avatar = ""

    references = [
        serialize_reference(reference) for reference in message.references.all()
    ]
    return {
        "id": message.id,
        "author_id": message.author_id,
        "author_username": message.author.username,
        "author_avatar_url": avatar,
        "body": message.body,
        "preview_text": compute_message_preview_text(
            body=message.body,
            has_references=bool(references),
        ),
        "references": references,
        "created_at": message.created_at.isoformat(),
        "is_own_message": message.author_id == request_user.id,
    }


def serialize_reference(reference):
    if reference.snapshot_title:
        return {
            "id": reference.id,
            "reference_type": reference.reference_type,
            "title": reference.snapshot_title,
            "subtitle": reference.snapshot_subtitle,
            "meta": reference.snapshot_meta,
            "href": reference.snapshot_href or None,
            "is_available": reference.snapshot_is_available,
        }

    payload = {
        "id": reference.id,
        "reference_type": reference.reference_type,
        "href": None,
        "is_available": False,
    }
    if (
        reference.reference_type == MessageReference.ReferenceType.EXPENSE
        and reference.expense is not None
    ):
        expense = reference.expense
        payload.update(
            {
                "title": expense.title,
                "subtitle": f"${expense.amount:.2f} • {expense.payer.username}",
                "meta": f"Spent {_format_date(expense.date_spent)}",
                "href": (f'{reverse("expenses_list")}?highlight_expense={expense.id}'),
                "is_available": True,
            }
        )
        return payload

    if (
        reference.reference_type == MessageReference.ReferenceType.CHORE
        and reference.chore is not None
    ):
        chore = reference.chore
        payload.update(
            {
                "title": chore.description,
                "subtitle": summarize_chore_schedule(chore),
                "meta": summarize_chore_assignees(chore),
                "href": f'{reverse("chores_list")}?highlight_chore={chore.id}',
                "is_available": True,
            }
        )
        return payload

    if reference.reference_type == MessageReference.ReferenceType.EXPENSE:
        payload.update(
            {
                "title": "Expense unavailable",
                "subtitle": "This expense is no longer available.",
                "meta": "Unavailable",
            }
        )
    else:
        payload.update(
            {
                "title": "Chore unavailable",
                "subtitle": "This chore is no longer available.",
                "meta": "Unavailable",
            }
        )
    return payload


def summarize_chore_schedule(chore):
    if chore.repeat_type == "ONE_TIME":
        if chore.has_due_date and chore.due_date:
            summary = f"Due {_format_date(chore.due_date)}"
            if chore.due_time:
                summary += f" at {chore.due_time.strftime('%-I:%M %p')}"
            return summary
        return "One-time"

    if chore.repeat_type == "DAILY":
        return "Repeats daily"

    weekly_days = []
    labels = [
        ("repeat_monday", "Mon"),
        ("repeat_tuesday", "Tue"),
        ("repeat_wednesday", "Wed"),
        ("repeat_thursday", "Thu"),
        ("repeat_friday", "Fri"),
        ("repeat_saturday", "Sat"),
        ("repeat_sunday", "Sun"),
    ]
    for attr, label in labels:
        if getattr(chore, attr):
            weekly_days.append(label)
    if weekly_days:
        return f"Repeats {' / '.join(weekly_days)}"
    return "Repeats weekly"


def summarize_chore_assignees(chore):
    assignees = list(
        chore.assignees.order_by("username").values_list("username", flat=True)
    )
    if not assignees:
        return "Unassigned"
    if len(assignees) == 1:
        return f"Assigned to {assignees[0]}"
    if len(assignees) == 2:
        return f"Assigned to {assignees[0]} and {assignees[1]}"
    return f"Assigned to {assignees[0]} +{len(assignees) - 1} more"


def _resolve_reference_specs(*, conversation, reference_types, reference_ids):
    if len(reference_types) != len(reference_ids):
        raise ValidationError("Invalid reference payload.")

    reference_specs = []
    for reference_type, reference_id in zip(reference_types, reference_ids):
        if not reference_type or not str(reference_id).strip():
            raise ValidationError("Invalid reference payload.")

        if reference_type == MessageReference.ReferenceType.EXPENSE:
            obj = (
                Expense.objects.filter(
                    household=conversation.household,
                    pk=reference_id,
                )
                .select_related("payer")
                .first()
            )
            if obj is None:
                raise ValidationError("One or more selected expenses are unavailable.")
        elif reference_type == MessageReference.ReferenceType.CHORE:
            obj = (
                Chore.objects.filter(
                    household=conversation.household,
                    is_active=True,
                    pk=reference_id,
                )
                .prefetch_related("assignees")
                .first()
            )
            if obj is None:
                raise ValidationError("One or more selected chores are unavailable.")
        else:
            raise ValidationError("Invalid reference payload.")

        reference_specs.append({"reference_type": reference_type, "object": obj})
    return reference_specs


def _format_date(value):
    return value.strftime("%b %d, %Y").replace(" 0", " ")


def _build_reference_snapshot(reference_type, obj):
    if reference_type == MessageReference.ReferenceType.EXPENSE:
        return {
            "title": obj.title,
            "subtitle": f"${obj.amount:.2f} • {obj.payer.username}",
            "meta": f"Spent {_format_date(obj.date_spent)}",
            "href": f'{reverse("expenses_list")}?highlight_expense={obj.id}',
            "is_available": True,
        }

    return {
        "title": obj.description,
        "subtitle": summarize_chore_schedule(obj),
        "meta": summarize_chore_assignees(obj),
        "href": f'{reverse("chores_list")}?highlight_chore={obj.id}',
        "is_available": True,
    }
