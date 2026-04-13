from django.contrib import admin

from .models import Conversation, ConversationParticipant, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "conversation_type", "updated_at")
    list_filter = ("conversation_type",)
    search_fields = ("title", "household__name", "created_by__username")


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "joined_at", "last_read_at")
    search_fields = ("conversation__title", "user__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "author", "created_at")
    search_fields = ("body", "author__username")
