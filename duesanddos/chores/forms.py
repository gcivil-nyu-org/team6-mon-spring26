from django import forms
from accounts.models import CustomUser
from .models import Chore


class ChoreForm(forms.ModelForm):
    assignees = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Chore
        fields = [
            "description",
            "repeat_type",
            "has_due_date",
            "due_date",
            "due_time",
            "start_date",
            "end_date",
            "repeat_monday",
            "repeat_tuesday",
            "repeat_wednesday",
            "repeat_thursday",
            "repeat_friday",
            "repeat_saturday",
            "repeat_sunday",
            "assignees",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "due_time": forms.TimeInput(attrs={"type": "time"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)

        if household is not None:
            self.fields["assignees"].queryset = CustomUser.objects.filter(
                memberships__household=household
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        repeat_type = cleaned_data.get("repeat_type")
        has_due_date = cleaned_data.get("has_due_date")
        due_date = cleaned_data.get("due_date")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        weekday_flags = [
            cleaned_data.get("repeat_monday"),
            cleaned_data.get("repeat_tuesday"),
            cleaned_data.get("repeat_wednesday"),
            cleaned_data.get("repeat_thursday"),
            cleaned_data.get("repeat_friday"),
            cleaned_data.get("repeat_saturday"),
            cleaned_data.get("repeat_sunday"),
        ]

        if repeat_type == "ONE_TIME" and has_due_date and not due_date:
            self.add_error("due_date", "Please select a due date.")

        if repeat_type in ["DAILY", "WEEKLY"] and not start_date:
            self.add_error("start_date", "Please select a start date for recurring chores.")

        if repeat_type == "WEEKLY" and not any(weekday_flags):
            raise forms.ValidationError(
                "Select at least one day for weekly recurring chores."
            )

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before the start date.")

        return cleaned_data