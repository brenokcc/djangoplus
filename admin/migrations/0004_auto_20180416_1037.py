# Generated by Django 2.0.3 on 2018-04-16 10:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    atomic = False
    dependencies = [
        ('admin', '0003_auto_20180416_1034'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='ascii',
        ),
        migrations.RemoveField(
            model_name='unit',
            name='ascii',
        ),
        migrations.RenameField(
            model_name='organization',
            old_name='id',
            new_name='scope_ptr',
        ),
        migrations.RenameField(
            model_name='unit',
            old_name='id',
            new_name='scope_ptr',
        ),
        migrations.AlterField(
            model_name='organization',
            name='scope_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='admin.Scope'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='scope_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='admin.Scope'),
        ),
    ]
