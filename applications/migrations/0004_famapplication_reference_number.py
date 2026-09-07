from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('applications', '0003_split_full_name')]

    operations = [
        migrations.AddField(
            model_name='famapplication',
            name='reference_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
