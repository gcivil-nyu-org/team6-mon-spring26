from django.db import migrations


def backfill_group_conversations(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    ConversationParticipant = apps.get_model("chat", "ConversationParticipant")
    Household = apps.get_model("households", "Household")

    for household in Household.objects.all():
        created_by_membership = household.members.order_by("joined_at").first()
        if created_by_membership is None:
            continue

        conversation = (
            Conversation.objects.filter(
                household=household,
                conversation_type="group",
            )
            .order_by("id")
            .first()
        )
        if conversation is None:
            conversation = Conversation.objects.create(
                household=household,
                conversation_type="group",
                title="Household Chat",
                created_by=created_by_membership.user,
            )

        existing_user_ids = set(
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).values_list("user_id", flat=True)
        )
        for membership in household.members.exclude(user_id__in=existing_user_ids):
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=membership.user,
            )


def reverse_backfill_group_conversations(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    Conversation.objects.filter(
        conversation_type="group", title="Household Chat"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            backfill_group_conversations,
            reverse_backfill_group_conversations,
        )
    ]
