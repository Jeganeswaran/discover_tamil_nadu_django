from django.db import migrations, models


def split_existing_names(apps, schema_editor):
    FamApplication = apps.get_model('applications', 'FamApplication')
    for application in FamApplication.objects.all().iterator():
        first_name, separator, last_name = application.full_name.partition(' ')
        application.first_name = first_name
        application.last_name = last_name if separator else ''
        application.save(update_fields=['first_name', 'last_name'])


class Migration(migrations.Migration):
    dependencies = [('applications', '0002_sitebrand')]

    operations = [
        migrations.AddField(
            model_name='famapplication',
            name='first_name',
            field=models.CharField(default='', max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='famapplication',
            name='last_name',
            field=models.CharField(default='', max_length=80),
            preserve_default=False,
        ),
        migrations.RunPython(split_existing_names, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='famapplication',
            name='full_name',
        ),
    ]