# Generated by Django 2.0.3 on 2018-04-16 10:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djangoplus.admin.models
import djangoplus.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('admin', '0005_auto_20180416_1045'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Função',
                'verbose_name_plural': 'Funções',
            },
        ),
        migrations.AddField(
            model_name='role',
            name='group',
            field=djangoplus.db.models.fields.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admin.Group', verbose_name='Grupo'),
        ),
        migrations.AddField(
            model_name='role',
            name='scope',
            field=djangoplus.db.models.fields.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='admin.Scope', verbose_name='Scope'),
        ),
        migrations.AddField(
            model_name='role',
            name='user',
            field=djangoplus.db.models.fields.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário'),
        ),
        migrations.AddField(
            model_name='role',
            name='active',
            field=djangoplus.db.models.fields.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.RemoveField(
            model_name='user',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='user',
            name='unit',
        ),
    ]
