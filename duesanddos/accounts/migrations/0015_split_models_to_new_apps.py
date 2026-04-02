# Hand-written migration for the accounts → new apps split.
#
# This single migration:
#   1. Re-points Profile.active_household from accounts.Household → households.Household
#   2. Deletes the moved model states from the accounts app
#
# It depends on households.0001_initial so that the households.Household
# model exists in the project state before we alter the FK.
#
# On a FRESH (test) database the migration runs after households/0001 creates
# the households_household table, so there is no conflict.
#
# On a LIVE database this migration should be applied with --fake because
# the actual table renames were handled by the previous set of manual steps.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_expensesplit_is_settled_expensesplit_settled_at_and_more"),
        ("households", "0001_initial"),
    ]

    operations = [
        # 1. Re-wire Profile.active_household to point at the new app's model.
        migrations.AlterField(
            model_name="profile",
            name="active_household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="active_profiles",
                to="households.household",
            ),
        ),
        # 2. Remove the old model states from accounts.
        #    The actual DB tables are kept / migrated by the new apps.
        migrations.DeleteModel(name="ActivityLog"),
        migrations.DeleteModel(name="ExpenseSplit"),
        migrations.DeleteModel(name="Expense"),
        migrations.DeleteModel(name="HouseholdMember"),
        migrations.DeleteModel(name="Household"),
    ]
