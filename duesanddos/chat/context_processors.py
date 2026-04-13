from .services import ensure_chat_context, unread_counts_for_user


def chat_unread_counts(request):
    if not request.user.is_authenticated:
        return {}

    household, _group_conversation = ensure_chat_context(request.user)
    if household is None:
        return {"chat_unread_total": 0, "chat_unread_by_conversation": {}}

    payload = unread_counts_for_user(request.user, household)
    return {
        "chat_unread_total": payload["total_unread"],
        "chat_unread_by_conversation": payload["by_conversation"],
    }
