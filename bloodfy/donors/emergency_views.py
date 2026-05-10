"""
Emergency blood search views.
Handles emergency donor search and contact functionality.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt

from .models import Donor
from .serializers import DonorListSerializer
from utils.responses import success_response, error_response


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


class EmergencyDonorSearchView(APIView):
    """
    Search for emergency donors by blood group and location.
    Only returns APPROVED and AVAILABLE donors.
    """
    
    # Public endpoint - no auth required (emergency blood search)
    authentication_classes = []   # Skip token validation entirely
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        GET /api/emergency/search?blood_group=O-&location=Lahore
        """
        blood_group = request.query_params.get('blood_group', '')
        location = request.query_params.get('location', '')
        
        # Fix URL encoding: 'A ' should be 'A+' (browser encodes + as space)
        blood_group = blood_group.replace(' ', '+')
        
        # Validate required parameters
        if not blood_group:
            return error_response(
                message="Blood group is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not location:
            return error_response(
                message="Location is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Query approved and available donors
        queryset = Donor.objects.select_related('user').filter(
            user__donor_status='DONOR_APPROVED',
            blood_group=blood_group,
            is_active=True,
            availability_status=True,
            city__icontains=location
        )
        
        # Get user's location if available (for distance calculation)
        user_lat = request.query_params.get('latitude')
        user_lon = request.query_params.get('longitude')
        
        results = []
        AVG_CITY_SPEED_KMH = 30  # Average urban driving speed
        
        for donor in queryset:
            donor_data = {
                'id': str(donor.id),
                'name': donor.user.get_full_name(),
                'blood_group': donor.blood_group,
                'city': donor.city,
                'phone_number': donor.user.phone_number if donor.user.phone_number else None,
                'distance': None,
                'eta_minutes': None,
                'latitude': float(donor.latitude) if donor.latitude else None,
                'longitude': float(donor.longitude) if donor.longitude else None,
                'has_coordinates': bool(donor.latitude and donor.longitude)
            }
            
            # Calculate distance if coordinates are available
            if (user_lat and user_lon and 
                donor.latitude and donor.longitude):
                try:
                    distance = haversine_distance(
                        user_lat, user_lon,
                        donor.latitude, donor.longitude
                    )
                    donor_data['distance'] = round(distance, 2)
                    # ETA = distance / speed * 60 minutes (add 5min buffer)
                    donor_data['eta_minutes'] = round((distance / AVG_CITY_SPEED_KMH) * 60) + 5
                except Exception as e:
                    print(f"Distance calculation error: {e}")
                    donor_data['distance'] = None
                    donor_data['eta_minutes'] = None
            
            results.append(donor_data)
        
        # Sort by distance if available, otherwise by response_rate
        if any(r['distance'] is not None for r in results):
            results.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))
        else:
            results.sort(key=lambda x: x['name'])
        
        return success_response(
            data={
                'donors': results,
                'count': len(results),
                'blood_group': blood_group,
                'location': location
            },
            message=f"Found {len(results)} donor(s) for {blood_group} in {location}"
        )


class EmergencyContactView(APIView):
    """
    Trigger emergency contact to a donor.
    Logs the contact attempt.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/emergency/contact
        Body: {
            "donor_id": "uuid",
            "contact_type": "SMS" or "CALL"
        }
        """
        donor_id = request.data.get('donor_id')
        contact_type = request.data.get('contact_type', 'CALL')
        
        # Validate donor_id
        if not donor_id:
            return error_response(
                message="Donor ID is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate contact_type
        if contact_type not in ['SMS', 'CALL']:
            return error_response(
                message="Contact type must be 'SMS' or 'CALL'",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Get donor
        try:
            donor = Donor.objects.select_related('user').get(
                id=donor_id,
                user__donor_status='DONOR_APPROVED',
                is_active=True
            )
        except Donor.DoesNotExist:
            return error_response(
                message="Donor not found or not available",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Build the SMS message
        requester_phone = request.user.phone_number or 'Bloodify Emergency Line'
        sms_message = (
            f"EMERGENCY - Bloodfy Alert!\n"
            f"{request.user.get_full_name()} urgently needs blood.\n"
            f"Please contact them at: {requester_phone}\n"
            f"Your help can save a life!"
        )
        
        # Log contact attempt
        contact_info = {
            'donor_name': donor.user.get_full_name(),
            'donor_phone': donor.user.phone_number,
            'contact_type': contact_type,
            'requested_by': request.user.get_full_name(),
            'requested_by_phone': request.user.phone_number,
            'sms_message': sms_message,  # Always include message text
        }
        
        # Send SMS via Twilio if contact type is SMS
        if contact_type == 'SMS' and donor.user.phone_number:
            from notifications.sms_service import TwilioSMSService
            try:
                sms_service = TwilioSMSService()
                sms_result = sms_service.send_sms(
                    to_phone=donor.user.phone_number,
                    message=sms_message,
                )
                contact_info['sms_status'] = 'delivered' if sms_result['success'] else 'failed'
                contact_info['sms_sid'] = sms_result.get('sid', '')
                contact_info['sms_mode'] = sms_result.get('mode', 'twilio')
                
                if not sms_result['success']:
                    contact_info['sms_error'] = sms_result.get('error', 'Unknown error')
                    # Still return success — SMS attempt was made, show preview to admin
                    contact_info['sms_status'] = 'logged'
            except Exception as e:
                import traceback
                print(f"[SMS ERROR] {traceback.format_exc()}")
                # Graceful fallback — log the SMS instead of crashing
                contact_info['sms_status'] = 'logged'
                contact_info['sms_sid'] = f'FALLBACK_{donor.user.phone_number}'
                contact_info['sms_error'] = str(e)
                contact_info['sms_mode'] = 'fallback'
        
        # Log the emergency contact for audit
        import logging
        logger = logging.getLogger('bloodfy')
        logger.info(
            "[EMERGENCY CONTACT] %s to %s (%s) by %s | Status: %s",
            contact_type,
            donor.user.get_full_name(),
            donor.user.phone_number,
            request.user.get_full_name(),
            contact_info.get('sms_status', 'N/A'),
        )
        
        return success_response(
            data=contact_info,
            message=f"{contact_type} contact initiated successfully"
        )
