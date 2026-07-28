# Generated manually for lab/radiology verification workflow

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('radiology', '0002_radiologyreporttemplate'),
        ('consultations', '0007_radiologyrequest_walkin_fields'),
    ]
    operations = [
        migrations.AddField(
            model_name='labtestrequest',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lab_requests_verified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='labtestrequest',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='radiologyrequest',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='radiology_requests_verified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='radiologyrequest',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='radiologyrequest',
            name='report_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requests', to='radiology.radiologyreporttemplate'),
        ),
    ]
