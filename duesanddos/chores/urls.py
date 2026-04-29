from django.urls import path
from . import views

urlpatterns = [
    path("chores/", views.chores_list_view, name="chores_list"),
    path("chores/add/", views.add_chore_view, name="add_chore"),
    path("chores/<int:chore_id>/edit/", views.edit_chore_view, name="edit_chore"),
    path("chores/<int:chore_id>/delete/", views.delete_chore_view, name="delete_chore"),
    path(
        "chores/<int:chore_id>/complete/",
        views.complete_chore_occurrence_view,
        name="complete_chore_occurrence",
    ),
    path("chores/sync-gcal/", views.sync_chores_to_gcal_view, name="sync_chores_to_gcal"),
]
