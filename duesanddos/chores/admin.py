from django.contrib import admin
from .models import Chore


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "household",
        "repeat_type",
        "has_due_date",
        "due_date",
        "due_time",
        "is_active",
    )
    list_filter = ("household", "repeat_type", "has_due_date", "is_active")
    search_fields = ("description",)
    filter_horizontal = ("assignees",)