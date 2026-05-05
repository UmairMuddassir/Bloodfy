# Generated manually — adds TriageLog model for medical urgency triage audit trail.

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0002_initial'),
        ('requests_management', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TriageLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('diagnosis', models.TextField(verbose_name='Patient Diagnosis')),
                ('patient_age', models.PositiveIntegerField(blank=True, null=True, verbose_name='Patient Age')),
                ('units_required', models.PositiveIntegerField(default=1, verbose_name='Units Required')),
                ('blood_group', models.CharField(max_length=5, verbose_name='Blood Group')),
                ('current_stock', models.PositiveIntegerField(default=0, verbose_name='Available Stock at Assessment Time')),
                ('urgency_level', models.CharField(
                    choices=[('emergency', 'Emergency'), ('urgent', 'Urgent'), ('normal', 'Normal')],
                    max_length=20,
                    verbose_name='Assessed Urgency',
                )),
                ('confidence', models.DecimalField(decimal_places=2, max_digits=3, verbose_name='Confidence Score (0-1)')),
                ('reasoning', models.TextField(verbose_name='Assessment Reasoning')),
                ('auto_escalate', models.BooleanField(default=False, verbose_name='Auto-Escalated')),
                ('recommended_actions', models.JSONField(default=list, verbose_name='Recommended Actions')),
                ('method', models.CharField(
                    choices=[('rule_based', 'Rule-Based'), ('llm', 'LLM-Powered')],
                    default='rule_based',
                    max_length=20,
                    verbose_name='Assessment Method',
                )),
                ('admin_override_level', models.CharField(
                    blank=True,
                    choices=[('emergency', 'Emergency'), ('urgent', 'Urgent'), ('normal', 'Normal')],
                    max_length=20,
                    null=True,
                    verbose_name='Admin Override Urgency',
                )),
                ('override_reason', models.TextField(blank=True, null=True, verbose_name='Override Reason')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('blood_request', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='triage_logs',
                    to='requests_management.bloodrequest',
                )),
                ('assessed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='triage_assessments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Assessed By',
                )),
                ('overridden_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='triage_overrides',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Overridden By',
                )),
            ],
            options={
                'verbose_name': 'Triage Log',
                'verbose_name_plural': 'Triage Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='triagelog',
            index=models.Index(fields=['urgency_level'], name='ai_triage_urgency_idx'),
        ),
        migrations.AddIndex(
            model_name='triagelog',
            index=models.Index(fields=['created_at'], name='ai_triage_created_idx'),
        ),
        migrations.AddIndex(
            model_name='triagelog',
            index=models.Index(fields=['method'], name='ai_triage_method_idx'),
        ),
    ]
