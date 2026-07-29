import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepartmentUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g. "Unit 1", "Unit 2", "General Unit"', max_length=100)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='departments.department')),
            ],
            options={
                'db_table': 'departments_departmentunit',
                'ordering': ['display_order', 'name'],
                'unique_together': {('department', 'name')},
            },
        ),
    ]
