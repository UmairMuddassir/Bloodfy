"""
AI Engine app serializers.
"""

from rest_framework import serializers
from .models import AIRanking, AIModelMetrics, TriageLog
from donors.serializers import DonorListSerializer


class AIRankingSerializer(serializers.ModelSerializer):
    """Serializer for AI ranking details."""
    
    donor_info = DonorListSerializer(source='donor', read_only=True)
    
    class Meta:
        model = AIRanking
        fields = [
            'id', 'blood_request', 'donor', 'donor_info',
            'compatibility_score', 'distance_score',
            'responsiveness_score', 'eligibility_score',
            'final_rank_score', 'rank_position', 'distance_km',
            'algorithm_version', 'was_notified', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class AIRankingListSerializer(serializers.ModelSerializer):
    """Serializer for listing AI rankings (compact view)."""
    
    donor_name = serializers.SerializerMethodField()
    donor_blood_group = serializers.CharField(source='donor.blood_group', read_only=True)
    
    class Meta:
        model = AIRanking
        fields = [
            'id', 'donor', 'donor_name', 'donor_blood_group',
            'final_rank_score', 'rank_position', 'distance_km',
            'was_notified', 'calculated_at'
        ]
    
    def get_donor_name(self, obj):
        return obj.donor.user.get_full_name()


class RankDonorsRequestSerializer(serializers.Serializer):
    """Serializer for triggering AI donor ranking."""
    
    blood_request_id = serializers.UUIDField(required=False)
    
    # Matching dashboard frontend keys for preview/simulation
    blood_group_needed = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    urgency_level = serializers.CharField(required=False)
    
    max_donors = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50
    )
    max_distance_km = serializers.IntegerField(
        default=50,
        min_value=5,
        max_value=200
    )
    include_unavailable = serializers.BooleanField(default=False)


class RankDonorsResponseSerializer(serializers.Serializer):
    """Serializer for AI ranking response."""
    
    blood_request_id = serializers.UUIDField()
    blood_group = serializers.CharField()
    total_eligible_donors = serializers.IntegerField()
    ranked_donors = AIRankingListSerializer(many=True)
    algorithm_version = serializers.CharField()
    calculated_at = serializers.DateTimeField()


class AIModelMetricsSerializer(serializers.ModelSerializer):
    """Serializer for AI model metrics."""
    
    class Meta:
        model = AIModelMetrics
        fields = [
            'id', 'date', 'total_requests', 'successful_matches',
            'accuracy_rate', 'average_response_time_hours',
            'top_1_accuracy', 'top_3_accuracy', 'top_5_accuracy',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReactivationCheckSerializer(serializers.Serializer):
    """Serializer for reactivation check request."""
    
    donor_id = serializers.UUIDField(required=False)
    check_all = serializers.BooleanField(default=False)


class ReactivationResultSerializer(serializers.Serializer):
    """Serializer for reactivation check result."""
    
    total_checked = serializers.IntegerField()
    reactivated = serializers.IntegerField()
    reactivated_donors = serializers.ListField()


# =============================================================================
# Medical Urgency Triage Serializers
# =============================================================================

class TriageRequestSerializer(serializers.Serializer):
    """Validate incoming triage assessment requests."""

    diagnosis = serializers.CharField(
        max_length=2000,
        help_text="Patient diagnosis or reason for blood need"
    )
    patient_age = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        help_text="Patient age in years"
    )
    units_required = serializers.IntegerField(
        default=1,
        min_value=1,
        max_value=50,
        help_text="Number of blood units needed"
    )
    blood_group = serializers.ChoiceField(
        choices=['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'],
        help_text="Required blood group"
    )
    current_stock = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Available units of this blood group at the hospital"
    )
    blood_request_id = serializers.UUIDField(
        required=False,
        help_text="Optional: link triage to an existing blood request"
    )


class TriageResponseSerializer(serializers.Serializer):
    """Shape the triage assessment response."""

    urgency_level = serializers.ChoiceField(
        choices=['emergency', 'urgent', 'normal']
    )
    confidence = serializers.FloatField()
    reasoning = serializers.CharField()
    auto_escalate = serializers.BooleanField()
    recommended_actions = serializers.ListField(
        child=serializers.CharField()
    )
    method = serializers.CharField()
    triage_log_id = serializers.UUIDField(required=False)


class TriageLogSerializer(serializers.ModelSerializer):
    """Full triage log for admin review."""

    effective_urgency = serializers.CharField(read_only=True)
    assessed_by_name = serializers.SerializerMethodField()
    overridden_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TriageLog
        fields = [
            'id', 'blood_request', 'diagnosis', 'patient_age',
            'units_required', 'blood_group', 'current_stock',
            'urgency_level', 'confidence', 'reasoning',
            'auto_escalate', 'recommended_actions', 'method',
            'admin_override_level', 'overridden_by', 'overridden_by_name',
            'override_reason', 'assessed_by', 'assessed_by_name',
            'effective_urgency', 'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'effective_urgency',
            'assessed_by_name', 'overridden_by_name',
        ]

    def get_assessed_by_name(self, obj):
        if obj.assessed_by:
            return obj.assessed_by.get_full_name()
        return None

    def get_overridden_by_name(self, obj):
        if obj.overridden_by:
            return obj.overridden_by.get_full_name()
        return None


class TriageOverrideSerializer(serializers.Serializer):
    """Validate admin override of triage urgency."""

    urgency_level = serializers.ChoiceField(
        choices=['emergency', 'urgent', 'normal'],
        help_text="New urgency level"
    )
    reason = serializers.CharField(
        max_length=1000,
        help_text="Reason for override"
    )

