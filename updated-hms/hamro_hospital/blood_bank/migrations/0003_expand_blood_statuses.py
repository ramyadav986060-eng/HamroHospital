# Generated manually for blood inventory lifecycle statuses

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('blood_bank', '0002_bloodrequest_and_issue_report')]
    operations = [
        migrations.AlterField(
            model_name='bloodunit',
            name='status',
            field=models.CharField(choices=[('collected', 'Collected'), ('tested', 'Tested'), ('available', 'Available'), ('reserved', 'Reserved'), ('issued', 'Issued'), ('expired', 'Expired'), ('discarded', 'Discarded'), ('returned', 'Returned')], default='available', max_length=10),
        ),
    ]
