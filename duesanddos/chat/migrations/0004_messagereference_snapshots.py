from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_messagereference_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="messagereference",
            name="snapshot_href",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="messagereference",
            name="snapshot_is_available",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="messagereference",
            name="snapshot_meta",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="messagereference",
            name="snapshot_subtitle",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="messagereference",
            name="snapshot_title",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
