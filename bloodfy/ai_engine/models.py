"""
AI Engine app models.
"""

import uuid
from django.db import models
from donors.models import Donor
from requests_management.models import BloodRequest


class AIRanking(models.Model):
    """
    Store AI ranking scores for audit and analysis.
    Records how donors were scored for each blood request.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.CASCADE,
        related_name='ai_rankings'
    )
    
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name='ai_rankings'
    )
    
    # Individual score components (0-100 scale)
    compatibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Blood Compatibility Score'
    )
    
    distance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Distance Score'
    )
    
    responsiveness_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Responsiveness Score'
    )
    
    eligibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Eligibility Score'
    )
    
    # Final weighted score
    final_rank_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Final Rank Score'
    )
    
    # Rank position (1 = best)
    rank_position = models.PositiveIntegerField(
        verbose_name='Rank Position'
    )
    
    # Distance in kilometers
    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Distance (km)'
    )
    
    # Additional metadata
    algorithm_version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name='Algorithm Version'
    )
    
    was_notified = models.BooleanField(
        default=False,
        verbose_name='Was Notified'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'AI Ranking'
        verbose_name_plural = 'AI Rankings'
        unique_together = ['blood_request', 'donor']
        ordering = ['blood_request', 'rank_position']
        indexes = [
            models.Index(fields=['blood_request', 'rank_position']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"Rank #{self.rank_position}: {self.donor} for Request {self.blood_request.id}"


class AIModelMetrics(models.Model):
    """
    Track AI model performance metrics over time.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    date = models.DateField(
        unique=True,
        verbose_name='Metrics Date'
    )
    
    # Accuracy metrics
    total_requests = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Requests Processed'
    )
    
    successful_matches = models.PositiveIntegerField(
        default=0,
        verbose_name='Successful Matches'
    )
    
    accuracy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Accuracy Rate (%)'
    )
    
    # Response metrics
    average_response_time_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Avg Response Time (hours)'
    )
    
    # Top-N accuracy
    top_1_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Top-1 Accuracy (%)'
    )
    
    top_3_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Top-3 Accuracy (%)'
    )
    
    top_5_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Top-5 Accuracy (%)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI Model Metrics'
        verbose_name_plural = 'AI Model Metrics'
        ordering = ['-date']
    
    def __str__(self):
        return f"AI Metrics for {self.date}: {self.accuracy_rate}% accuracy"


class TriageLog(models.Model):
    """
    Audit log for every medical urgency triage assessment.
    Stores both the input and the AI/rule-based output so admins
    can review, override, and improve the system over time.
    """

    URGENCY_CHOICES = [
        ('emergency', 'Emergency'),
        ('urgent', 'Urgent'),
        ('normal', 'Normal'),
    ]

    METHOD_CHOICES = [
        ('rule_based', 'Rule-Based'),
        ('llm', 'LLM-Powered'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Link to the blood request (optional — triage may be standalone)
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triage_logs'
    )

    # Input data (stored as JSON for flexibility)
    diagnosis = models.TextField(
        verbose_name='Patient Diagnosis'
    )
    patient_age = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Patient Age'
    )
    units_required = models.PositiveIntegerField(
        default=1,
        verbose_name='Units Required'
    )
    blood_group = models.CharField(
        max_length=5,
        verbose_name='Blood Group'
    )
    current_stock = models.PositiveIntegerField(
        default=0,
        verbose_name='Available Stock at Assessment Time'
    )

    # Output / assessment
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        verbose_name='Assessed Urgency'
    )
    confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        verbose_name='Confidence Score (0-1)'
    )
    reasoning = models.TextField(
        verbose_name='Assessment Reasoning'
    )
    auto_escalate = models.BooleanField(
        default=False,
        verbose_name='Auto-Escalated'
    )
    recommended_actions = models.JSONField(
        default=list,
        verbose_name='Recommended Actions'
    )
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='rule_based',
        verbose_name='Assessment Method'
    )

    # Admin override
    admin_override_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        blank=True,
        null=True,
        verbose_name='Admin Override Urgency'
    )
    overridden_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triage_overrides',
        verbose_name='Overridden By'
    )
    override_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Override Reason'
    )

    # Who triggered it
    assessed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triage_assessments',
        verbose_name='Assessed By'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Triage Log'
        verbose_name_plural = 'Triage Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['urgency_level']),
            models.Index(fields=['created_at']),
            models.Index(fields=['method']),
        ]

    def __str__(self):
        return f"Triage [{self.urgency_level.upper()}] — {self.blood_group} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def effective_urgency(self):
        """Return the admin override if set, otherwise the AI assessment."""
        return self.admin_override_level or self.urgency_level
