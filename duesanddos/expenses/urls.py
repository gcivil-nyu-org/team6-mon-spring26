from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/add/", views.add_expense, name="add_expense"),
    path("expenses/", views.expenses_list_view, name="expenses_list"),
    path("expenses/add/", views.add_expense_pro, name="add_expense_pro"),
    path("expense-history/", views.expense_history_view, name="expense_history"),
    path("settle-split/<int:split_id>/", views.settle_split_view, name="settle_split"),
    path(
        "expenses/delete/<int:expense_id>/",
        views.delete_expense_pro,
        name="delete_expense_pro",
    ),
    path(
        "expenses/edit/<int:expense_id>/",
        views.edit_expense_pro,
        name="edit_expense_pro",
    ),
]
