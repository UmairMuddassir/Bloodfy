"""
AI Engine app views.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import AIRanking, AIModelMetrics, TriageLog
from .ranking_engine import process_blood_request, rank_donors_for_request
from .triage_service import TriageService
from .llm_provider import get_llm_provider
from .serializers import (
    AIRankingListSerializer, RankDonorsRequestSerializer,
    RankDonorsResponseSerializer, AIModelMetricsSerializer,
    ReactivationCheckSerializer, ReactivationResultSerializer,
    TriageRequestSerializer, TriageResponseSerializer,
    TriageLogSerializer, TriageOverrideSerializer,
)
from requests_management.models import BloodRequest
from donors.models import Donor
from utils.responses import success_response, error_response, created_response
from utils.permissions import IsAdmin

logger = logging.getLogger('bloodfy')


class RankDonorsView(APIView):
    """Trigger AI ranking for a blood request."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Trigger donor ranking for a blood request or simulate for dashboard."""
        serializer = RankDonorsRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        request_id = serializer.validated_data.get('blood_request_id')
        max_donors = serializer.validated_data.get('max_donors', 10)
        max_distance = serializer.validated_data.get('max_distance_km', 50)
        
        if request_id:
            # REAL RANKING FOR A REQUEST
            try:
                blood_request = BloodRequest.objects.get(id=request_id)
            except BloodRequest.DoesNotExist:
                return error_response(
                    message="Blood request not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Check permission
            if request.user.user_type != 'admin':
                if hasattr(request.user, 'recipient_profile'):
                    if blood_request.recipient != request.user.recipient_profile:
                        return error_response(
                            message="Access denied",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                else:
                    return error_response(
                        message="Access denied",
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            
            # Process ranking
            rankings, ranked_donors = process_blood_request(
                blood_request,
                max_donors=max_donors,
                max_distance_km=max_distance
            )
            
            results = AIRankingListSerializer(rankings, many=True).data
            blood_group = blood_request.blood_group
        else:
            # SIMULATION FOR DASHBOARD
            blood_group = serializer.validated_data.get('blood_group_needed', 'O-')
            location = serializer.validated_data.get('location', 'Lahore')
            
            # Find donors in the same city with compatible blood group
            from utils.constants import BLOOD_COMPATIBILITY
            compatible_groups = BLOOD_COMPATIBILITY.get(blood_group, [blood_group])
            
            donors = Donor.objects.filter(
                blood_group__in=compatible_groups,
                city__iexact=location,
                is_active=True,
                is_eligible=True,
                availability_status=True
            ).select_related('user')[:max_donors]
            
            # Use real scoring functions for simulation
            from .ranking_engine import (
                haversine_distance, calculate_distance_score,
                calculate_compatibility_score, calculate_responsiveness_score,
                calculate_eligibility_score
            )
            from utils.constants import AI_RANKING_WEIGHTS
            
            # Default hospital coordinates (Lahore centre) for simulation
            hospital_lat, hospital_lon = 31.5204, 74.3587
            
            results = []
            scored_donors = []
            for donor in donors:
                # Calculate real scores
                d_lat = float(donor.latitude) if donor.latitude else hospital_lat
                d_lon = float(donor.longitude) if donor.longitude else hospital_lon
                dist_km = haversine_distance(hospital_lat, hospital_lon, d_lat, d_lon)
                
                compat_score = calculate_compatibility_score(donor.blood_group, blood_group)
                dist_score = calculate_distance_score(dist_km)
                resp_score = calculate_responsiveness_score(donor)
                elig_score = calculate_eligibility_score(donor)
                
                final_score = (
                    AI_RANKING_WEIGHTS['compatibility'] * compat_score +
                    AI_RANKING_WEIGHTS['distance'] * dist_score +
                    AI_RANKING_WEIGHTS['responsiveness'] * resp_score +
                    AI_RANKING_WEIGHTS['eligibility'] * elig_score
                )
                scored_donors.append((donor, final_score, dist_km))
            
            # Sort by score descending
            scored_donors.sort(key=lambda x: x[1], reverse=True)
            
            for i, (donor, score, dist_km) in enumerate(scored_donors, 1):
                results.append({
                    'id': str(donor.id),
                    'donor': {
                        'id': str(donor.id),
                        'user': {
                            'first_name': donor.user.first_name,
                            'last_name': donor.user.last_name,
                            'phone_number': donor.user.phone_number
                        },
                        'city': donor.city,
                        'blood_group': donor.blood_group
                    },
                    'score': round(score / 100, 4),
                    'distance': round(dist_km, 2),
                    'rank_position': i
                })

        return success_response(
            data={
                'blood_request_id': str(request_id) if request_id else None,
                'blood_group': blood_group,
                'total_eligible_donors': len(results),
                'ranked_donors': results,
                'algorithm_version': '1.0',
                'calculated_at': timezone.now().isoformat()
            },
            message="Donors ranked successfully"
        )


class RankingHistoryView(APIView):
    """Get ranking history for a blood request."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, request_id):
        """Get AI ranking history."""
        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return error_response(
                message="Blood request not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        rankings = AIRanking.objects.filter(
            blood_request=blood_request
        ).select_related('donor__user').order_by('rank_position')
        
        serializer = AIRankingListSerializer(rankings, many=True)
        
        return success_response(
            data={
                'blood_request_id': str(request_id),
                'rankings': serializer.data,
                'count': rankings.count()
            },
            message="Ranking history retrieved"
        )


class ReactivationCheckView(APIView):
    """Check and reactivate eligible donors."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Manually trigger reactivation check."""
        serializer = ReactivationCheckSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        donor_id = serializer.validated_data.get('donor_id')
        check_all = serializer.validated_data.get('check_all', False)
        
        reactivated = []
        
        if donor_id:
            # Check specific donor
            try:
                donor = Donor.objects.get(id=donor_id)
                was_eligible = donor.is_eligible
                donor.update_eligibility()
                if not was_eligible and donor.is_eligible:
                    reactivated.append({
                        'id': str(donor.id),
                        'name': donor.user.get_full_name()
                    })
            except Donor.DoesNotExist:
                return error_response(
                    message="Donor not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            total_checked = 1
        elif check_all:
            # Check all inactive donors
            inactive_donors = Donor.objects.filter(is_eligible=False)
            total_checked = inactive_donors.count()
            
            for donor in inactive_donors:
                was_eligible = donor.is_eligible
                donor.update_eligibility()
                if not was_eligible and donor.is_eligible:
                    reactivated.append({
                        'id': str(donor.id),
                        'name': donor.user.get_full_name()
                    })
        else:
            return error_response(
                message="Provide donor_id or set check_all to true",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return success_response(
            data={
                'total_checked': total_checked,
                'reactivated': len(reactivated),
                'reactivated_donors': reactivated
            },
            message=f"Checked {total_checked} donors, reactivated {len(reactivated)}"
        )


class AIMetricsView(APIView):
    """Get AI model metrics."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get latest AI metrics."""
        metrics = AIModelMetrics.objects.order_by('-date')
        latest = metrics.first()
        
        accuracy = float(latest.accuracy_rate) if latest else 0
        
        serializer = AIModelMetricsSerializer(metrics[:30], many=True)
        
        return success_response(
            data={
                'accuracy': accuracy,
                'metrics': serializer.data,
                'count': metrics.count()
            },
            message="AI metrics retrieved"
        )


# =============================================================================
# Medical Urgency Triage Views
# =============================================================================

class TriageAssessView(APIView):
    """
    POST /api/ai/triage/
    Assess the medical urgency of a blood request.
    
    Uses LLM if configured (GEMINI_API_KEY or OPENAI_API_KEY),
    otherwise falls back to rule-based assessment.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Perform urgency triage assessment."""
        serializer = TriageRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                message="Invalid triage request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data

        # Initialise the triage service (with optional LLM)
        llm = get_llm_provider()
        service = TriageService(llm_provider=llm)

        # Run assessment
        result = service.assess({
            "diagnosis": validated["diagnosis"],
            "patient_age": validated.get("patient_age"),
            "units_required": validated.get("units_required", 1),
            "blood_group": validated["blood_group"],
            "current_stock": validated.get("current_stock", 0),
        })

        # Persist triage log for audit trail
        blood_request = None
        blood_request_id = validated.get("blood_request_id")
        if blood_request_id:
            try:
                blood_request = BloodRequest.objects.get(id=blood_request_id)
            except BloodRequest.DoesNotExist:
                pass  # non-critical — log without link

        triage_log = TriageLog.objects.create(
            blood_request=blood_request,
            diagnosis=validated["diagnosis"],
            patient_age=validated.get("patient_age"),
            units_required=validated.get("units_required", 1),
            blood_group=validated["blood_group"],
            current_stock=validated.get("current_stock", 0),
            urgency_level=result["urgency_level"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            auto_escalate=result["auto_escalate"],
            recommended_actions=result["recommended_actions"],
            method=result["method"],
            assessed_by=request.user,
        )

        # If auto_escalate and there is a linked blood request, update its urgency
        if result["auto_escalate"] and blood_request:
            if blood_request.urgency_level != "emergency":
                blood_request.urgency_level = "emergency"
                blood_request.save(update_fields=["urgency_level"])
                logger.info(
                    "Auto-escalated blood request %s to EMERGENCY",
                    blood_request.id,
                )

        # Build response
        response_data = {
            **result,
            "triage_log_id": str(triage_log.id),
        }

        return created_response(
            data=response_data,
            message=f"Triage assessment: {result['urgency_level'].upper()}"
        )


class TriageLogListView(APIView):
    """
    GET /api/ai/triage/logs/
    List triage assessment history (Admin only).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        """Retrieve triage log history."""
        queryset = TriageLog.objects.select_related(
            'blood_request', 'assessed_by', 'overridden_by'
        )

        # Filters
        urgency = request.query_params.get('urgency')
        method = request.query_params.get('method')
        blood_group = request.query_params.get('blood_group')

        if urgency:
            queryset = queryset.filter(urgency_level=urgency)
        if method:
            queryset = queryset.filter(method=method)
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)

        queryset = queryset.order_by('-created_at')[:100]
        serializer = TriageLogSerializer(queryset, many=True)

        return success_response(
            data={
                'triage_logs': serializer.data,
                'count': len(serializer.data),
            },
            message="Triage logs retrieved"
        )


class TriageOverrideView(APIView):
    """
    POST /api/ai/triage/<triage_id>/override/
    Admin override for a triage assessment.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, triage_id):
        """Override a triage assessment's urgency level."""
        try:
            triage_log = TriageLog.objects.get(id=triage_id)
        except TriageLog.DoesNotExist:
            return error_response(
                message="Triage log not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = TriageOverrideSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Invalid override data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        triage_log.admin_override_level = serializer.validated_data['urgency_level']
        triage_log.override_reason = serializer.validated_data['reason']
        triage_log.overridden_by = request.user
        triage_log.save(update_fields=[
            'admin_override_level', 'override_reason', 'overridden_by',
        ])

        # If the override escalates to emergency and there's a linked request, update it
        if (serializer.validated_data['urgency_level'] == 'emergency'
                and triage_log.blood_request):
            triage_log.blood_request.urgency_level = 'emergency'
            triage_log.blood_request.save(update_fields=['urgency_level'])

        return success_response(
            data=TriageLogSerializer(triage_log).data,
            message=f"Triage overridden to {serializer.validated_data['urgency_level'].upper()}"
        )
