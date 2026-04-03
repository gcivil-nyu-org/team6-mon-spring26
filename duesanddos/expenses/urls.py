from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/add/", views.add_expense_pro, name="add_expense"),
    path("expenses/", views.expenses_list_view, name="expenses_list"),
    path("expenses/add/", views.add_expense_pro, name="add_expense_pro"),
    path(
        "settle-split/<int:settlement_id>/",
        views.confirm_settlement,
        name="settle_split",
    ),
    path(
        "expenses/delete/<int:expense_id>/",
        views.delete_expense_pro,
        name="delete_expense_pro",
    ),
    path("settle/request/", views.request_settlement, name="request_settlement"),
    path(
        "settle/confirm/<int:settlement_id>/",
        views.confirm_settlement,
        name="confirm_settlement",
    ),
    path(
        "settlement/request-delete/<int:settlement_id>/",
        views.request_delete_settlement,
        name="request_delete_settlement",
    ),
    path(
        "settlement/approve-delete/<int:settlement_id>/",
        views.approve_delete_settlement,
        name="approve_delete_settlement",
    ),
]
