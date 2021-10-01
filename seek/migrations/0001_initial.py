# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2020-08-04 01:45
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Assay_assets',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assay_id', models.IntegerField(default=None)),
                ('asset_id', models.IntegerField(default=None)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(default=None)),
                ('updated_at', models.DateTimeField(default=None)),
                ('relationship_type_id', models.IntegerField(default=None)),
                ('asset_type', models.CharField(default=None, max_length=255)),
                ('direction', models.IntegerField(default=None)),
            ],
            options={
                'db_table': 'assay_assets',
            },
        ),
        migrations.CreateModel(
            name='Content_blobs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('md5sum', models.CharField(default=None, max_length=255)),
                ('url', models.TextField(default=None)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('original_filename', models.CharField(default=None, max_length=255)),
                ('content_type', models.CharField(default=None, max_length=255)),
                ('asset_id', models.IntegerField(default=None)),
                ('asset_type', models.CharField(default=None, max_length=255)),
                ('asset_version', models.IntegerField(default=1)),
                ('is_webpage', models.BooleanField(default=0)),
                ('external_link', models.BooleanField(default=None)),
                ('sha1sum', models.CharField(default=None, max_length=255)),
                ('file_size', models.BigIntegerField(default=None)),
                ('created_at', models.DateTimeField(default=None)),
                ('updated_at', models.DateTimeField(default=None)),
            ],
            options={
                'db_table': 'content_blobs',
            },
        ),
        migrations.CreateModel(
            name='Data_files',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contributor_id', models.IntegerField(default=None)),
                ('title', models.CharField(default=None, max_length=255)),
                ('description', models.TextField(default=None)),
                ('template_id', models.IntegerField(default=None)),
                ('last_used_at', models.DateTimeField()),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('version', models.IntegerField(default=1)),
                ('first_letter', models.CharField(default=None, max_length=1)),
                ('other_creators', models.TextField(default=None)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('policy_id', models.IntegerField(default=None)),
                ('doi', models.CharField(default=None, max_length=255)),
                ('license', models.CharField(default=None, max_length=255)),
                ('simulation_data', models.BooleanField(default=0)),
                ('deleted_contributor', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'data_files',
            },
        ),
        migrations.CreateModel(
            name='Documents',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default=None, max_length=255)),
                ('description', models.TextField(default=None)),
                ('contributor_id', models.IntegerField(default=None)),
                ('version', models.IntegerField(default=1)),
                ('first_letter', models.CharField(default=None, max_length=1)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('policy_id', models.IntegerField(default=None)),
                ('doi', models.CharField(default=None, max_length=255)),
                ('license', models.CharField(default=None, max_length=255)),
                ('last_used_at', models.DateTimeField()),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('other_creators', models.TextField(default=None)),
                ('deleted_contributor', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'documents',
            },
        ),
        migrations.CreateModel(
            name='Permissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contributor_type', models.CharField(default=None, max_length=255)),
                ('contributor_id', models.IntegerField(default=None)),
                ('policy_id', models.IntegerField(default=None)),
                ('access_type', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'permissions',
            },
        ),
        migrations.CreateModel(
            name='Policies',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default=None, max_length=255)),
                ('sharing_scope', models.IntegerField(default=None)),
                ('access_type', models.IntegerField(default=0)),
                ('use_whitelist', models.BooleanField(default=None)),
                ('use_blacklist', models.BooleanField(default=None)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'policies',
            },
        ),
        migrations.CreateModel(
            name='Projects_samples',
            fields=[
                ('project_id', models.IntegerField(default=None, primary_key=True)),
                ('sample_id', models.IntegerField(default=None, primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'projects_samples',
            },
        ),
        migrations.CreateModel(
            name='Sample_attributes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default=None, max_length=255)),
                ('sample_attribute_type_id', models.IntegerField(default=None)),
                ('required', models.BooleanField(default=0)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('pos', models.IntegerField(default=None)),
                ('sample_type_id', models.IntegerField(default=None)),
                ('unit_id', models.IntegerField(default=None)),
                ('is_title', models.BooleanField(default=0)),
                ('template_column_index', models.IntegerField(default=None)),
                ('accessor_name', models.CharField(default=None, max_length=255)),
                ('sample_controlled_vocab_id', models.IntegerField(default=None)),
                ('linked_sample_type_id', models.IntegerField(default=None)),
            ],
            options={
                'db_table': 'sample_attributes',
            },
        ),
        migrations.CreateModel(
            name='Sample_types',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default=None, max_length=255)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('first_letter', models.CharField(default=None, max_length=1)),
                ('description', models.TextField(default=None)),
                ('uploaded_template', models.BooleanField(default=0)),
                ('contributor_id', models.IntegerField(default=None)),
                ('deleted_contributor', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'sample_types',
            },
        ),
        migrations.CreateModel(
            name='Samples',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default=None, max_length=255)),
                ('sample_type_id', models.IntegerField(default=None)),
                ('json_metadata', models.TextField(default=None)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('contributor_id', models.IntegerField(default=None)),
                ('policy_id', models.IntegerField(default=None)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('first_letter', models.CharField(default=None, max_length=1)),
                ('other_creators', models.TextField(default=None)),
                ('originating_data_file_id', models.IntegerField(default=None)),
                ('deleted_contributor', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'samples',
            },
        ),
        migrations.CreateModel(
            name='Sops',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contributor_id', models.IntegerField(default=None)),
                ('title', models.CharField(default=None, max_length=255)),
                ('description', models.TextField(default=None)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('last_used_at', models.DateTimeField()),
                ('version', models.IntegerField(default=1)),
                ('first_letter', models.CharField(default=None, max_length=1)),
                ('other_creators', models.TextField(default=None)),
                ('uuid', models.CharField(default=None, max_length=255)),
                ('policy_id', models.IntegerField(default=None)),
                ('doi', models.CharField(default=None, max_length=255)),
                ('license', models.CharField(default=None, max_length=255)),
                ('deleted_contributor', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'sops',
            },
        ),
        migrations.CreateModel(
            name='User_profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.CharField(choices=[(0, 'Undefined'), (1, 'IMPAcTb'), (2, 'MIT_SRP')], max_length=255)),
                ('institute', models.TextField()),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('login', models.CharField(default=None, max_length=255)),
                ('crypted_password', models.CharField(default=None, max_length=255)),
                ('salt', models.CharField(default=None, max_length=255)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('remember_token', models.CharField(default=None, max_length=255)),
                ('remember_token_expires_at', models.DateTimeField()),
                ('activation_code', models.CharField(default=None, max_length=255)),
                ('activated_at', models.DateTimeField()),
                ('person_id', models.IntegerField(default=None)),
                ('reset_password_code', models.CharField(default=None, max_length=255)),
                ('reset_password_code_until', models.DateTimeField()),
                ('posts_count', models.IntegerField(default=None)),
                ('last_seen_at', models.DateTimeField()),
                ('uuid', models.CharField(default=None, max_length=255)),
            ],
            options={
                'db_table': 'users',
            },
        ),
        migrations.AlterUniqueTogether(
            name='projects_samples',
            unique_together=set([('project_id', 'sample_id')]),
        ),
    ]