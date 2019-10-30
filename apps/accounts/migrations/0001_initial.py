# Generated by Django 2.2.6 on 2019-10-30 10:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields
import django_mysql.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('algorithm', models.CharField(max_length=255)),
                ('confirmation_token', models.CharField(max_length=255)),
                ('credentials_expire_at', models.DateTimeField(null=True)),
                ('credentials_expired', models.BooleanField()),
                ('email', models.CharField(max_length=255)),
                ('email_canonical', models.CharField(max_length=255)),
                ('enabled', models.BooleanField()),
                ('expired', models.BooleanField()),
                ('expires_at', models.DateTimeField(null=True)),
                ('last_login', models.DateTimeField(null=True)),
                ('locked', models.BooleanField()),
                ('password_requested_at', models.DateTimeField(null=True)),
                ('roles', models.TextField()),
                ('salt', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=15)),
                ('username', models.CharField(max_length=255, unique=True)),
                ('username_canonical', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'fos_user',
            },
        ),
        migrations.CreateModel(
            name='Datacenter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country', django_countries.fields.CountryField(db_column='countrydomain', max_length=2)),
                ('dc12v', models.BooleanField()),
                ('greengrid', models.BooleanField()),
                ('mja3', models.BooleanField(null=True, verbose_name='meerjaren plan energie 3')),
                ('model', models.CharField(max_length=255)),
                ('name', models.CharField(db_column='naam', max_length=255)),
                ('pue', models.FloatField(verbose_name='Power usage effectiveness')),
                ('residualheat', models.BooleanField(null=True)),
                ('showonwebsite', models.BooleanField()),
                ('temperature', models.IntegerField(null=True)),
                ('temperature_type', models.CharField(choices=[('C', 'C'), ('F', 'F')], max_length=255)),
                ('virtual', models.BooleanField()),
                ('website', models.CharField(max_length=255)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'datacenters',
            },
        ),
        migrations.CreateModel(
            name='Hostingprovider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archived', models.BooleanField()),
                ('country', django_countries.fields.CountryField(db_column='countrydomain', max_length=2)),
                ('customer', models.BooleanField()),
                ('icon', models.CharField(max_length=50)),
                ('iconurl', models.CharField(max_length=255)),
                ('model', django_mysql.models.EnumField(choices=[('groeneenergie', 'green energy'), ('compensatie', 'compensation')], default='compensatie')),
                ('name', models.CharField(db_column='naam', max_length=255)),
                ('partner', models.CharField(max_length=255, null=True)),
                ('showonwebsite', models.BooleanField()),
                ('website', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'hostingproviders',
            },
        ),
        migrations.CreateModel(
            name='HostingproviderStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('green_domains', models.IntegerField()),
                ('green_checks', models.IntegerField()),
                ('hostingprovider', models.ForeignKey(db_column='id_hp', on_delete=django.db.models.deletion.CASCADE, to='accounts.Hostingprovider')),
            ],
            options={
                'db_table': 'hostingproviders_stats',
            },
        ),
        migrations.CreateModel(
            name='HostingproviderDatacenter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('approved', models.BooleanField()),
                ('approved_at', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('datacenter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Datacenter')),
                ('hostingprovider', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Hostingprovider')),
            ],
            options={
                'db_table': 'datacenters_hostingproviders',
            },
        ),
        migrations.CreateModel(
            name='HostingproviderCertificate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('energyprovider', models.CharField(max_length=255)),
                ('mainenergy_type', models.CharField(choices=[('wind', 'wind'), ('water', 'water'), ('solar', 'solar'), ('mixed', 'mixed')], db_column='mainenergytype', max_length=255)),
                ('url', models.CharField(max_length=255)),
                ('valid_from', models.DateField()),
                ('valid_to', models.DateField()),
                ('hostingprovider', models.ForeignKey(db_column='id_hp', null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Datacenter')),
            ],
            options={
                'db_table': 'hostingprovider_certificates',
            },
        ),
        migrations.AddField(
            model_name='hostingprovider',
            name='datacenter',
            field=models.ManyToManyField(through='accounts.HostingproviderDatacenter', to='accounts.Datacenter'),
        ),
        migrations.CreateModel(
            name='DatacenterCooling',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cooling', models.CharField(max_length=255)),
                ('datacenter', models.ForeignKey(db_column='id_dc', on_delete=django.db.models.deletion.CASCADE, to='accounts.Datacenter')),
            ],
            options={
                'db_table': 'datacenters_coolings',
            },
        ),
        migrations.CreateModel(
            name='DatacenterClassification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('classification', models.CharField(max_length=255)),
                ('datacenter', models.ForeignKey(db_column='id_dc', on_delete=django.db.models.deletion.CASCADE, to='accounts.Datacenter')),
            ],
            options={
                'db_table': 'datacenters_classifications',
            },
        ),
        migrations.CreateModel(
            name='DatacenterCertificate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('energyprovider', models.CharField(max_length=255)),
                ('mainenergy_type', models.CharField(choices=[('wind', 'wind'), ('water', 'water'), ('solar', 'solar'), ('mixed', 'mixed')], db_column='mainenergytype', max_length=255)),
                ('url', models.CharField(max_length=255)),
                ('valid_from', models.DateField()),
                ('valid_to', models.DateField()),
                ('datacenter', models.ForeignKey(db_column='id_dc', null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Datacenter')),
            ],
            options={
                'db_table': 'datacenter_certificates',
            },
        ),
        migrations.AddField(
            model_name='user',
            name='hostingprovider',
            field=models.ForeignKey(db_column='id_hp', on_delete=django.db.models.deletion.CASCADE, to='accounts.Hostingprovider'),
        ),
        migrations.AddIndex(
            model_name='hostingprovider',
            index=models.Index(fields=['archived'], name='hostingprov_archive_b919c2_idx'),
        ),
        migrations.AddIndex(
            model_name='hostingprovider',
            index=models.Index(fields=['showonwebsite'], name='hostingprov_showonw_43e92a_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='fos_user_email_2450e2_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email_canonical'], name='fos_user_email_c_039d43_idx'),
        ),
    ]
