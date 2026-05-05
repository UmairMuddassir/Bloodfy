"""
Donors app views.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.models import AppNotification

User = get_user_model()

from .models import Donor, DonationHistory, DonorRequest
from .serializers import (
    DonorSerializer, DonorListSerializer, DonorRegistrationSerializer,
    DonorUpdateSerializer, DonationHistorySerializer,
    DonationHistoryCreateSerializer, DonorEligibilitySerializer,
    DonorStatisticsSerializer, DonorRequestSerializer,
    DonorRequestListSerializer, DonorApprovalSerializer
)
from utils.responses import success_response, error_response, created_response
from utils.permissions import IsAdmin, IsDonorOrAdmin, IsOwnerOrAdmin, AdminWriteOnly
from utils.pagination import StandardResultsSetPagination


class DonorListView(APIView):
    """List all donors (Admin only) or register as donor."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all APPROVED donors with filters."""
        # CRITICAL: Only show DONOR_APPROVED donors
        queryset = Donor.objects.select_related('user').filter(
            user__donor_status='DONOR_APPROVED'
        )
        
        # Apply filters
        blood_group = request.query_params.get('blood_group')
        city = request.query_params.get('city')
        is_active = request.query_params.get('is_active')
        is_eligible = request.query_params.get('is_eligible')
        
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if is_eligible is not None:
            queryset = queryset.filter(is_eligible=is_eligible.lower() == 'true')
        
        serializer = DonorListSerializer(queryset, many=True)
        
        return success_response(
            data={
                'donors': serializer.data,
                'count': queryset.count()
            },
            message="Donors retrieved successfully"
        )


class DonorRegisterView(APIView):
    """Register current user as a donor (creates pending request)."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = DonorRegistrationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Donor registration failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        donor_request = serializer.save()
        
        # Create notification for admins
        try:
            admins = User.objects.filter(user_type='admin')
            for admin in admins:
                AppNotification.objects.create(
                    user=admin,
                    title="New Donor Registration Request",
                    message=f"User {request.user.get_full_name()} has applied to become a donor.",
                    notification_type='donor_approval',
                    related_id=str(donor_request.id)
                )
        except Exception:
            pass
        
        return created_response(
            data=DonorRequestSerializer(donor_request).data,
            message="Donor request submitted successfully. Awaiting admin approval."
        )


class DonorDetailView(APIView):
    """Get, update donor profile."""
    
    permission_classes = [IsAuthenticated]
    
    def get_donor(self, donor_id, request):
        """Get donor with permission check."""
        try:
            donor = Donor.objects.select_related('user').get(id=donor_id)
        except Donor.DoesNotExist:
            return None
        
        # Check permission
        if request.user.user_type != 'admin' and donor.user != request.user:
            return None
        
        return donor
    
    def get(self, request, donor_id):
        """Get donor profile."""
        donor = self.get_donor(donor_id, request)
        
        if not donor:
            return error_response(
                message="Donor not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DonorSerializer(donor)
        return success_response(
            data=serializer.data,
            message="Donor retrieved successfully"
        )
    
    def put(self, request, donor_id):
        """Update donor profile."""
        donor = self.get_donor(donor_id, request)
        
        if not donor:
            return error_response(
                message="Donor not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DonorUpdateSerializer(donor, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return error_response(
                message="Update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        return success_response(
            data=DonorSerializer(donor).data,
            message="Donor updated successfully"
        )

    def delete(self, request, donor_id):
        """Delete donor profile (Admin only - enforced by IsAdmin)."""
        # Check admin permission explicitly for delete
        if request.user.user_type != 'admin':
            return error_response(
                message="Only administrators can remove donors from the registry",
                status_code=status.HTTP_403_FORBIDDEN
            )
            
        donor = self.get_donor(donor_id, request)
        if not donor:
            return error_response(
                message="Donor not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        try:
            user = donor.user
            donor.delete()
            
            # Reset donor_status to None after donor profile deletion
            user.donor_status = None
            user.donor_status_updated_at = timezone.now()
            user.donor_status_updated_by = request.user
            user.save(update_fields=['donor_status', 'donor_status_updated_at', 'donor_status_updated_by'])
            
            return success_response(message="Donor removed from registry successfully")
        except Exception as e:
            return error_response(
                message=f"Failed to delete donor: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DonorEligibilityView(APIView):
    """Check donor eligibility status."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check current user's eligibility."""
        if not hasattr(request.user, 'donor_profile'):
            return error_response(
                message="You are not registered as a donor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        donor = request.user.donor_profile
        
        data = {
            'is_eligible': donor.is_eligible,
            'days_until_eligible': donor.days_until_eligible,
            'next_eligible_date': donor.next_eligible_date,
            'last_donation_date': donor.last_donation_date,
            'message': (
                "You are eligible to donate blood!" if donor.is_eligible
                else f"You can donate again in {donor.days_until_eligible} days."
            )
        }
        
        return success_response(
            data=data,
            message="Eligibility status retrieved"
        )


class DonationHistoryView(APIView):
    """Get and add donation history."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, donor_id):
        """Get donation history for a donor."""
        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            return error_response(
                message="Donor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if request.user.user_type != 'admin' and donor.user != request.user:
            return error_response(
                message="Access denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        history = DonationHistory.objects.filter(donor=donor)
        serializer = DonationHistorySerializer(history, many=True)
        
        return success_response(
            data={
                'donation_history': serializer.data,
                'total_donations': donor.donation_count
            },
            message="Donation history retrieved"
        )
    
    def post(self, request, donor_id):
        """Add donation history (Admin only - requires IsAdmin permission)."""
        # Admin check - keep inline for object-level view
        if request.user.user_type != 'admin':
            return error_response(
                message="Only administrators can add donation history",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            return error_response(
                message="Donor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DonationHistoryCreateSerializer(
            data=request.data,
            context={'donor': donor}
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to add donation",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        donation = serializer.save()
        
        return created_response(
            data=DonationHistorySerializer(donation).data,
            message="Donation recorded successfully"
        )


class DonorStatisticsView(APIView):
    """Get donor statistics (Authenticated users)."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive donor statistics."""
        donors = Donor.objects.all()
        
        # Basic counts
        total_donors = donors.count()
        active_donors = donors.filter(is_active=True).count()
        eligible_donors = donors.filter(is_eligible=True, is_active=True).count()
        
        # By blood group
        by_blood_group = dict(
            donors.values('blood_group')
            .annotate(count=Count('id'))
            .values_list('blood_group', 'count')
        )
        
        # By city
        by_city = dict(
            donors.values('city')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
            .values_list('city', 'count')
        )
        
        # Average response rate
        avg_response = donors.aggregate(avg=Avg('response_rate'))['avg'] or 0
        
        data = {
            'total_donors': total_donors,
            'active_donors': active_donors,
            'total_active_donors': active_donors, # Match frontend expectation
            'eligible_donors': eligible_donors,
            'by_blood_group': by_blood_group,
            'by_city': by_city,
            'average_response_rate': round(avg_response, 2)
        }
        
        return success_response(
            data=data,
            message="Donor statistics retrieved"
        )


class DonorReactivateView(APIView):
    """Reactivate a donor (Admin only or automatic)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, donor_id):
        """Manually reactivate a donor."""
        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            return error_response(
                message="Donor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Update eligibility based on last donation
        was_eligible = donor.is_eligible
        donor.update_eligibility()
        
        if not was_eligible and donor.is_eligible:
            # TODO: Send reactivation notification
            pass
        
        return success_response(
            data={
                'is_eligible': donor.is_eligible,
                'is_active': donor.is_active,
                'was_reactivated': not was_eligible and donor.is_eligible
            },
            message="Donor eligibility checked and updated"
        )


class DonorPendingListView(APIView):
    """List all pending donor requests (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all pending donor requests."""
        queryset = DonorRequest.objects.filter(status='pending').select_related('user')
        
        serializer = DonorRequestListSerializer(queryset, many=True)
        
        return success_response(
            data={
                'pending_requests': serializer.data,
                'count': queryset.count()
            },
            message="Pending donor requests retrieved successfully"
        )


class DonorApprovalView(APIView):
    """Approve or reject donor requests (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, request_id):
        """Approve or reject a donor request."""
        try:
            donor_request = DonorRequest.objects.select_related('user').get(id=request_id)
        except DonorRequest.DoesNotExist:
            return error_response(
                message="Donor request not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already processed
        if donor_request.status != 'pending':
            return error_response(
                message=f"This request has already been {donor_request.status}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DonorApprovalSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid approval data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        action = serializer.validated_data['action']
        user = donor_request.user
        
        if action == 'approve':
            # Create Donor profile from request data
            donor = Donor.objects.create(
                user=user,
                blood_group=donor_request.blood_group,
                city=donor_request.city,
                address=donor_request.address,
                latitude=donor_request.latitude,
                longitude=donor_request.longitude,
                medical_history=donor_request.medical_history,
                weight_kg=donor_request.weight_kg,
                date_of_birth=donor_request.date_of_birth,
                cnic=donor_request.cnic
            )
            
            # Update user donor_status to DONOR_APPROVED
            user.donor_status = 'DONOR_APPROVED'
            user.donor_status_updated_at = timezone.now()
            user.donor_status_updated_by = request.user
            user.save(update_fields=['donor_status', 'donor_status_updated_at', 'donor_status_updated_by'])
            
            # Update request status
            donor_request.status = 'approved'
            donor_request.reviewed_by = request.user
            donor_request.reviewed_at = timezone.now()
            donor_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            
            # Create notification for user
            try:
                AppNotification.objects.create(
                    user=user,
                    title="Donor Application Approved",
                    message="Congratulations! Your application to become a donor has been approved.",
                    notification_type='success',
                    related_id=str(donor.id)
                )
            except Exception:
                pass
            
            return success_response(
                data=DonorSerializer(donor).data,
                message="Donor request approved successfully"
            )
        
        else:  # reject
            rejection_reason = serializer.validated_data.get('rejection_reason', '')
            
            # Update user donor_status to DONOR_REJECTED
            user.donor_status = 'DONOR_REJECTED'
            user.donor_status_updated_at = timezone.now()
            user.donor_status_updated_by = request.user
            user.save(update_fields=['donor_status', 'donor_status_updated_at', 'donor_status_updated_by'])
            
            # Update request status
            donor_request.status = 'rejected'
            donor_request.reviewed_by = request.user
            donor_request.reviewed_at = timezone.now()
            donor_request.rejection_reason = rejection_reason
            donor_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])
            
            # Create notification for user
            try:
                AppNotification.objects.create(
                    user=user,
                    title="Donor Application Rejected",
                    message="We regret to inform you that your application to become a donor has been rejected.",
                    notification_type='danger',
                    related_id=str(donor_request.id)
                )
            except Exception:
                pass
            
            return success_response(
                data=DonorRequestSerializer(donor_request).data,
                message="Donor request rejected"
            )


class AdminDonorCreateView(APIView):
    """Create a new donor directly (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        from .serializers import AdminDonorCreateSerializer
        
        serializer = AdminDonorCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to create donor",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            donor = serializer.save()
        except Exception as e:
            return error_response(
                message=f"Failed to save donor: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return created_response(
            data=DonorListSerializer(donor).data,
            message="Donor created successfully"
        )


