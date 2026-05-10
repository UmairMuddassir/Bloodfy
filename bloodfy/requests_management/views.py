"""
Requests Management app views.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.models import AppNotification

User = get_user_model()

from .models import BloodRequest, DonorResponse
from .serializers import (
    BloodRequestSerializer, BloodRequestListSerializer,
    BloodRequestCreateSerializer, BloodRequestUpdateSerializer,
    DonorResponseSerializer, DonorResponseUpdateSerializer
)
from donors.models import Donor
from donors.serializers import DonorListSerializer
from utils.responses import success_response, error_response, created_response
from utils.permissions import IsAdmin, IsRecipientOrAdmin


class BloodRequestListView(APIView):
    """List and create blood requests."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List blood requests based on user role and ownership."""
        from django.db.models import Q
        
        # Base query: Start with none
        queryset = BloodRequest.objects.select_related('recipient__user', 'assigned_donor__user')
        
        if request.user.user_type == 'admin':
            # Admins see everything
            pass 
        else:
            # Users see:
            # 1. Requests they created (as recipient)
            # 2. Requests they are matched to (as donor)
            filters = Q()
            
            if hasattr(request.user, 'recipient_profile'):
                filters |= Q(recipient=request.user.recipient_profile)
                
            if hasattr(request.user, 'donor_profile'):
                filters |= Q(ai_matched_donors=request.user.donor_profile)
                
            queryset = queryset.filter(filters)
        
        # Apply filters from query params
        blood_group = request.query_params.get('blood_group')
        status_filter = request.query_params.get('status')
        urgency = request.query_params.get('urgency_level')
        city = request.query_params.get('city')
        
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if urgency:
            queryset = queryset.filter(urgency_level=urgency)
        if city:
            queryset = queryset.filter(hospital_city__icontains=city)
        
        queryset = queryset.order_by('-requested_at')
        serializer = BloodRequestListSerializer(queryset, many=True, context={'request': request})
        
        return success_response(
            data={
                'blood_requests': serializer.data,
                'count': queryset.count()
            },
            message="Blood requests retrieved"
        )
    
    def post(self, request):
        """Create a new blood request."""
        serializer = BloodRequestCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to create blood request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        blood_request = serializer.save()
        
        # Create notification for admins
        try:
            admins = User.objects.filter(user_type='admin')
            for admin in admins:
                AppNotification.objects.create(
                    user=admin,
                    title="New Blood Request",
                    message=f"A new blood request for {blood_request.blood_group} has been created at {blood_request.hospital_name}.",
                    notification_type='blood_request',
                    related_id=str(blood_request.id)
                )
        except Exception as e:
            print(f"Error creating admin notification for blood request: {e}")
        
        return created_response(
            data=BloodRequestSerializer(blood_request).data,
            message="Blood request created successfully"
        )


class BloodRequestDetailView(APIView):
    """Get, update, delete blood request."""
    
    permission_classes = [IsAuthenticated]
    
    def get_request(self, request_id, user):
        """Get blood request with permission check."""
        try:
            blood_request = BloodRequest.objects.select_related(
                'recipient__user', 'assigned_donor__user'
            ).get(id=request_id)
        except BloodRequest.DoesNotExist:
            return None
        
        # Check permission
        if user.user_type == 'admin':
            return blood_request
        
        # Check if user is the recipient (owns the request)
        if hasattr(user, 'recipient_profile'):
            if blood_request.recipient == user.recipient_profile:
                return blood_request
        
        # Check if user is an approved donor matched to this request
        if user.donor_status == 'DONOR_APPROVED' and hasattr(user, 'donor_profile'):
            if blood_request.ai_matched_donors.filter(id=user.donor_profile.id).exists():
                return blood_request
        
        return None
    
    def get(self, request, request_id):
        """Get blood request details."""
        blood_request = self.get_request(request_id, request.user)
        
        if not blood_request:
            return error_response(
                message="Blood request not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = BloodRequestSerializer(blood_request, context={'request': request})
        return success_response(
            data=serializer.data,
            message="Blood request retrieved"
        )
    
    def put(self, request, request_id):
        """Update blood request."""
        blood_request = self.get_request(request_id, request.user)
        
        if not blood_request:
            return error_response(
                message="Blood request not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Only pending requests can be updated
        if blood_request.status != 'pending':
            return error_response(
                message="Only pending requests can be updated",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BloodRequestUpdateSerializer(
            blood_request,
            data=request.data,
            partial=True
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        return success_response(
            data=BloodRequestSerializer(blood_request, context={'request': request}).data,
            message="Blood request updated"
        )
    
    def delete(self, request, request_id):
        """Cancel blood request."""
        blood_request = self.get_request(request_id, request.user)
        
        if not blood_request:
            return error_response(
                message="Blood request not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if blood_request.status in ['completed', 'cancelled']:
            return error_response(
                message="This request cannot be cancelled",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Cancelled by user')
        blood_request.mark_as_cancelled(reason)
        
        return success_response(
            message="Blood request deleted and marked as cancelled successfully",
            data={"status": "cancelled", "request_id": str(blood_request.id)}
        )


class BloodRequestCompleteView(APIView):
    """Mark blood request as completed and record donation."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        """Mark a blood request as completed."""
        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return error_response(
                message="Blood request not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check ownership
        if request.user.user_type != 'admin':
            if not hasattr(request.user, 'recipient_profile') or blood_request.recipient != request.user.recipient_profile:
                return error_response(
                    message="Access denied. Only the requester can mark this as completed.",
                    status_code=status.HTTP_403_FORBIDDEN
                )
        
        if blood_request.status == 'completed':
            return error_response(
                message="Blood request is already marked as completed",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        message = "Blood request marked as completed successfully"
        
        # AUTOMATIC COOLDOWN & PARTIAL FULFILLMENT LOGIC
        if blood_request.assigned_donor:
            try:
                from donors.models import DonationHistory
                
                # 1 Donor gives 1 Unit
                DonationHistory.objects.create(
                    donor=blood_request.assigned_donor,
                    blood_group=blood_request.assigned_donor.blood_group,
                    units_donated=1,
                    donation_date=timezone.now().date(),
                    hospital_name=blood_request.hospital_name,
                    notes=f"Automatically recorded for completed request #{str(blood_request.id)[:8]}"
                )
                
                # Update the donor's last donation date (this triggers the cooldown in the donor model)
                blood_request.assigned_donor.record_donation(timezone.now().date())
                
                # Increment the fulfilled units
                blood_request.units_fulfilled += 1
                
                if blood_request.units_fulfilled >= blood_request.units_required:
                    # Fully completed
                    blood_request.mark_as_completed()
                    message = "Request fully completed and donor placed on cooldown."
                else:
                    # Partially completed! Needs more donors.
                    # Unassign the current donor so another one can be assigned.
                    blood_request.status = 'approved'
                    blood_request.assigned_donor = None
                    blood_request.save(update_fields=['status', 'assigned_donor', 'units_fulfilled'])
                    remaining = blood_request.units_required - blood_request.units_fulfilled
                    message = f"1 unit fulfilled. {remaining} more unit(s) needed. Please assign another donor."
                    
            except Exception as e:
                print(f"Error putting donor on cooldown: {e}")
                blood_request.mark_as_completed()
        else:
            blood_request.mark_as_completed()
        
        return success_response(
            data=BloodRequestSerializer(blood_request, context={'request': request}).data,
            message=message
        )


class BloodRequestApproveView(APIView):
    """Approve blood request (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, request_id):
        """Approve a blood request."""
        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return error_response(
                message="Blood request not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if blood_request.is_approved:
            return error_response(
                message="Blood request is already approved",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        blood_request.approve(request.user)
        
        # Trigger matching
        try:
            matches_count = blood_request.find_matches()
            print(f"Auto-matching for request {blood_request.id}: {matches_count} donors found")
        except Exception as e:
            print(f"Error during auto-matching on approval: {e}")
        
        return success_response(
            data=BloodRequestSerializer(blood_request, context={'request': request}).data,
            message="Blood request accepted and approved successfully"
        )


class BloodRequestAssignView(APIView):
    """Assign a specific donor to a blood request (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, request_id):
        """Assign donor to request."""
        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return error_response(
                message="Blood request not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        donor_id = request.data.get('donor_id')
        if not donor_id:
            return error_response(message="donor_id is required")
            
        try:
            donor = Donor.objects.get(id=donor_id)
        except (Donor.DoesNotExist, ValueError):
            return error_response(
                message="Donor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        # Optional: Check if donor is matched or eligible
        # Requirement says "Admin assigns registered donor", so we keep it flexible
        
        blood_request.assign_donor(donor)
        
        return success_response(
            data=BloodRequestSerializer(blood_request, context={'request': request}).data,
            message=f"Donor {donor.user.get_full_name()} assigned to request successfully"
        )


class MatchedDonorsView(APIView):
    """Get AI-matched donors for a blood request."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, request_id):
        """Get matched donors list."""
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
        
        # Trigger matching if none exists
        if blood_request.ai_matched_donors.count() == 0:
            try:
                blood_request.find_matches()
            except Exception as e:
                print(f"Error matching on the fly: {e}")

        matched_donors = blood_request.ai_matched_donors.select_related('user').all()
        donor_serializer = DonorListSerializer(matched_donors, many=True)
        
        # Also include compatible stock inventory from nearby banks
        request_serializer = BloodRequestSerializer(blood_request, context={'request': request})
        
        return success_response(
            data={
                'blood_request_id': str(blood_request.id),
                'blood_group': blood_request.blood_group,
                'donors': donor_serializer.data,
                'matched_stock': request_serializer.data.get('matched_stock', []),
                'total_donors': matched_donors.count()
            },
            message="Matching evaluation completed successfully"
        )


class EmergencySearchView(APIView):
    """Emergency quick search for available donors."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Search for available donors by blood group and city."""
        from donors.models import Donor
        
        blood_group = request.query_params.get('blood_group')
        city = request.query_params.get('city')
        
        if not blood_group:
            return error_response(
                message="Blood group is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # CRITICAL: Only show DONOR_APPROVED donors
        queryset = Donor.objects.filter(
            blood_group=blood_group,
            is_active=True,
            is_eligible=True,
            availability_status=True,
            user__donor_status='DONOR_APPROVED'  # CRITICAL: Only approved donors
        ).select_related('user')
        
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Order by response rate
        queryset = queryset.order_by('-response_rate')[:20]
        
        serializer = DonorListSerializer(queryset, many=True)
        
        return success_response(
            data={
                'blood_group': blood_group,
                'city': city,
                'donors': serializer.data,
                'count': queryset.count()
            },
            message="Emergency search completed"
        )


class DonorResponseView(APIView):
    """View for donors to manage their responses to blood requests."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get pending requests for the current donor."""
        # Check if user is an approved donor
        if request.user.donor_status != 'DONOR_APPROVED' or not hasattr(request.user, 'donor_profile'):
            return success_response(data={'responses': []}, message="User is not an approved donor")
            
        donor = request.user.donor_profile
        responses = DonorResponse.objects.filter(donor=donor).select_related('blood_request', 'blood_request__recipient__user')
        
        status_filter = request.query_params.get('status', 'pending')
        if status_filter:
            responses = responses.filter(response_status=status_filter)
            
        serializer = DonorResponseSerializer(responses, many=True)
        return success_response(data={'responses': serializer.data}, message="Donor responses retrieved")

    def post(self, request, response_id):
        """Accept or decline a specific request."""
        try:
            response = DonorResponse.objects.get(id=response_id, donor__user=request.user)
        except DonorResponse.DoesNotExist:
            return error_response(message="Response record not found", status_code=status.HTTP_404_NOT_FOUND)
            
        action = request.data.get('action') # 'accept' or 'decline'
        reason = request.data.get('reason', '')
        
        if action == 'accept':
            response.accept()
            return success_response(message="Request accepted. Please proceed to the hospital.")
        elif action == 'decline':
            response.decline(reason)
            return success_response(message="Request declined.")
        
        return error_response(message="Invalid action", status_code=status.HTTP_400_BAD_REQUEST)

