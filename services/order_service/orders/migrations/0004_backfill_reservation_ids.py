
import uuid

from django.db import migrations


def backfill_reservation_ids(apps, schema_editor):
    OrderItem = apps.get_model("orders", "OrderItem")
    database = schema_editor.connection.alias

    items = OrderItem.objects.using(database).filter(
        reservation_id__isnull=True
    )

    for item in items.iterator():
        item.reservation_id = uuid.uuid4()
        item.save(
            using=database,
            update_fields=["reservation_id"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_orderitem_reservation_id"),
    ]

    operations = [
        migrations.RunPython(
            backfill_reservation_ids,
            migrations.RunPython.noop,
        ),
    ]
