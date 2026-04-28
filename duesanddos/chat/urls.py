from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("chat/", views.chat_index, name="index"),
    path("chat/<int:conversation_id>/", views.chat_index, name="detail"),
    path("chat/start-dm/<int:user_id>/", views.start_dm, name="start_dm"),
    path("chat/<int:conversation_id>/send/", views.send_message, name="send_message"),
    path("chat/<int:conversation_id>/messages/", views.messages_json, name="messages"),
    path(
        "chat/messages/<int:message_id>/delete-for-me/",
        views.delete_for_me,
        name="delete_for_me",
    ),
    path(
        "chat/messages/<int:message_id>/delete-for-everyone/",
        views.delete_for_everyone,
        name="delete_for_everyone",
    ),
    path("chat/unread-counts/", views.unread_counts, name="unread_counts"),
    path("chat/<int:conversation_id>/mark-read/", views.mark_read, name="mark_read"),
]
