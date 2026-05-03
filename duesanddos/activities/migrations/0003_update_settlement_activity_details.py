from django.db import migrations


def forwards(apps, schema_editor):
    ActivityLog = apps.get_model("activities", "ActivityLog")
    qs = ActivityLog.objects.filter(
        action="PAYMENT_SETTLED", details__startswith="Submitted settlement of "
    )
    for log in qs.iterator():
        log.details = log.details.replace(
            "Submitted settlement of ", "Settlement request submitted: ", 1
        )
        log.save(update_fields=["details"])


def backwards(apps, schema_editor):
    ActivityLog = apps.get_model("activities", "ActivityLog")
    qs = ActivityLog.objects.filter(
        action="PAYMENT_SETTLED", details__startswith="Settlement request submitted: "
    )
    for log in qs.iterator():
        log.details = log.details.replace(
            "Settlement request submitted: ", "Submitted settlement of ", 1
        )
        log.save(update_fields=["details"])


class Migration(migrations.Migration):
    dependencies = [
        ("activities", "0002_alter_activitylog_action"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
