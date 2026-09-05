from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('applications','0001_initial')]
    operations = [
        migrations.CreateModel(
            name='SiteBrand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Discover Tamil Nadu', max_length=160)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='branding/')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Site Branding', 'verbose_name_plural': 'Site Branding'},
        ),
    ]
