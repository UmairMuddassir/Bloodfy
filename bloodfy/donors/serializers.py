"""
Donors app serializers.
"""

from rest_framework import serializers
from .models import Donor, DonationHistory, DonorRequest
from users.serializers import UserSerializer
from utils.validators import validate_donation_eligibility


class DonorSerializer(serializers.ModelSerializer):
    """Serializer for donor details."""
    
    user = UserSerializer(read_only=True)
    next_eligible_date = serializers.DateField(read_only=True)
    days_until_eligible = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Donor
        fields = [
            'id', 'user', 'blood_group', 'city', 'address',
            'latitude', 'longitude', 'last_donation_date',
            'donation_count', 'is_active', 'is_eligible',
            'response_rate', 'availability_status',
            'medical_history', 'weight_kg', 'date_of_birth', 'cnic',
            'next_eligible_date', 'days_until_eligible',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'donation_count', 'is_eligible', 'response_rate',
            'total_requests_received', 'total_requests_accepted',
            'created_at', 'updated_at'
        ]


class DonorRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for donor registration - creates pending request."""
    
    class Meta:
        model = DonorRequest
        fields = [
            'blood_group', 'city', 'address', 'latitude', 'longitude',
            'medical_history', 'weight_kg', 'date_of_birth', 'cnic'
        ]
    
    def validate_cnic(self, value):
        """Validate CNIC is unique."""
        if value and DonorRequest.objects.filter(cnic=value).exists():
            raise serializers.ValidationError("A donor request with this CNIC already exists.")
        if value and Donor.objects.filter(cnic=value).exists():
            raise serializers.ValidationError("A donor with this CNIC already exists.")
        return value
    
    def create(self, validated_data):
        """Create donor request and set user status to DONOR_PENDING."""
        from django.utils import timezone
        user = self.context['request'].user
        
        # Check if user already has a donor profile
        if hasattr(user, 'donor_profile'):
            raise serializers.ValidationError("User already has an approved donor profile.")
        
        # Check if user already has a pending request
        if hasattr(user, 'donor_request'):
            raise serializers.ValidationError("User already has a pending donor request.")
        
        # Create donor request
        donor_request = DonorRequest.objects.create(user=user, **validated_data)
        
        # Update user's donor_status to DONOR_PENDING
        user.donor_status = 'DONOR_PENDING'
        user.donor_status_updated_at = timezone.now()
        user.save(update_fields=['donor_status', 'donor_status_updated_at'])
        
        return donor_request


class DonorUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating donor profile."""
    
    class Meta:
        model = Donor
        fields = [
            'city', 'address', 'latitude', 'longitude',
            'availability_status', 'medical_history',
            'weight_kg'
        ]


class DonorListSerializer(serializers.ModelSerializer):
    """Serializer for listing donors (compact view)."""
    
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Donor
        fields = [
            'id', 'name', 'email', 'phone', 'blood_group',
            'city', 'is_active', 'is_eligible', 'response_rate',
            'availability_status', 'last_donation_date'
        ]
    
    def get_name(self, obj):
        return obj.user.get_full_name()


class DonationHistorySerializer(serializers.ModelSerializer):
    """Serializer for donation history."""
    
    donor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DonationHistory
        fields = [
            'id', 'donor', 'donor_name', 'blood_group',
            'units_donated', 'donation_date', 'next_eligible_date',
            'hospital_name', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'next_eligible_date', 'created_at', 'updated_at']
    
    def get_donor_name(self, obj):
        return obj.donor.user.get_full_name()


class DonationHistoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating donation history."""
    
    class Meta:
        model = DonationHistory
        fields = [
            'blood_group', 'units_donated', 'donation_date',
            'hospital_name', 'notes'
        ]
    
    def validate_units_donated(self, value):
        """Validate units donated."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Units donated must be between 1 and 5.")
        return value
    
    def create(self, validated_data):
        """Create donation history and update donor."""
        donor = self.context['donor']
        
        # Set blood group from donor if not provided
        if 'blood_group' not in validated_data:
            validated_data['blood_group'] = donor.blood_group
        
        donation = DonationHistory.objects.create(donor=donor, **validated_data)
        
        # Update donor's last donation date and count
        donor.record_donation(validated_data['donation_date'])
        
        return donation


class DonorEligibilitySerializer(serializers.Serializer):
    """Serializer for donor eligibility check response."""
    
    is_eligible = serializers.BooleanField()
    days_until_eligible = serializers.IntegerField()
    next_eligible_date = serializers.DateField(allow_null=True)
    last_donation_date = serializers.DateField(allow_null=True)
    message = serializers.CharField()


class DonorStatisticsSerializer(serializers.Serializer):
    """Serializer for donor statistics."""
    
    total_donors = serializers.IntegerField()
    active_donors = serializers.IntegerField()
    eligible_donors = serializers.IntegerField()
    by_blood_group = serializers.DictField()
    by_city = serializers.DictField()
    average_response_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class DonorRequestSerializer(serializers.ModelSerializer):
    """Serializer for donor request details."""
    
    user = UserSerializer(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DonorRequest
        fields = [
            'id', 'user', 'blood_group', 'city', 'address',
            'latitude', 'longitude', 'medical_history', 'weight_kg',
            'date_of_birth', 'cnic', 'status', 'reviewed_by',
            'reviewed_by_name', 'reviewed_at', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at'
        ]
    
    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name()
        return None


class DonorRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing donor requests (compact view)."""
    
    name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField() # For cached JS compatibility
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    user = serializers.SerializerMethodField() # For cached JS compatibility
    
    class Meta:
        model = DonorRequest
        fields = [
            'id', 'name', 'user_name', 'email', 'phone', 'user', 'blood_group',
            'city', 'status', 'created_at'
        ]
    
    def get_name(self, obj):
        return obj.user.get_full_name()
        
    def get_user_name(self, obj):
        return obj.user.get_full_name()
        
    def get_user(self, obj):
        return {'email': obj.user.email}


class DonorApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting donor requests."""
    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if attrs['action'] == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting a request.'
            })
        return attrs


class AdminDonorCreateSerializer(serializers.ModelSerializer):
    """Serializer for admins to create a donor directly."""
    
    # User fields
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True)
    phone_number = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = Donor
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'password',
            'blood_group', 'city', 'address', 'medical_history', 
            'weight_kg', 'date_of_birth', 'cnic'
        ]
    
    def validate_email(self, value):
        from users.models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
        
    def create(self, validated_data):
        from users.models import User
        from django.db import transaction
        from django.utils import timezone

        # Extract user data
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number')
        password = validated_data.pop('password')
        
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number,
            'password': password,
            'username': email, # Use email as username
            'user_type': 'user',
            'donor_status': 'DONOR_APPROVED',
            'donor_status_updated_at': timezone.now()
        }
        
        with transaction.atomic():
            # Create User
            user = User.objects.create_user(**user_data)
            
            # Explicitly ensure status is set (in case create_user ignores extra fields)
            if user.donor_status != 'DONOR_APPROVED':
                user.donor_status = 'DONOR_APPROVED'
                user.save(update_fields=['donor_status'])
            
            user.donor_status_updated_by = self.context['request'].user
            user.save()
            
            # Create Donor
            donor = Donor.objects.create(user=user, **validated_data)
            
        return donor


