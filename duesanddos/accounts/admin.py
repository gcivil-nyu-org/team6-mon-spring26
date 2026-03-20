from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile, Household


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ["username", "email", "phone_number", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("phone_number",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("phone_number", "email")}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "notifications_enabled"]


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["name", "admin", "created_at"]
    search_fields = ["name", "admin__username"]
