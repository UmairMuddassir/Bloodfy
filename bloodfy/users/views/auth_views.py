"""
Users app views for authentication.
"""

import random
import string
from datetime import timedelta

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone

from ..models import User, OTPVerification
from ..serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    OTPVerificationSerializer,
    ResendOTPSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from utils.responses import success_response, error_response, created_response


def generate_otp():
    """Generate a 6-digit OTP."""
    return ''.join(random.choices(string.digits, k=6))


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Registration failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.save()
        
        # Generate OTP for email verification
        otp = generate_otp()
        OTPVerification.objects.create(
            user=user,
            code=otp,
            purpose='email_verification',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # TODO: Send OTP via email (implement email service)
        # For now, we'll include it in response for development
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return created_response(
            data={
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            message="Registration successful. Please verify your email."
        )


class LoginView(APIView):
    """User login endpoint."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return error_response(
                message="Login failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return success_response(
            data={
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
            message="Login successful"
        )


class LogoutView(APIView):
    """User logout endpoint - blacklist refresh token."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return success_response(
                message="Logout successful"
            )
        except Exception as e:
            return error_response(
                message="Logout failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )


class VerifyEmailView(APIView):
    """Email verification with OTP."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Verification failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.validated_data['user']
        otp_record = serializer.validated_data['otp_record']
        
        # Mark user as verified
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        
        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        
        return success_response(
            message="Email verified successfully"
        )


class ResendOTPView(APIView):
    """Resend OTP for email verification or password reset."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to resend OTP",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.user
        purpose = serializer.validated_data['purpose']
        
        # Generate new OTP
        otp = generate_otp()
        OTPVerification.objects.create(
            user=user,
            code=otp,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # TODO: Send OTP via email
        
        return success_response(
            message="OTP sent successfully"
        )


class PasswordResetRequestView(APIView):
    """Request password reset - send OTP."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to process request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        if hasattr(serializer, 'user'):
            user = serializer.user
            
            # Generate OTP
            otp = generate_otp()
            OTPVerification.objects.create(
                user=user,
                code=otp,
                purpose='password_reset',
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # TODO: Send OTP via email
        
        # Always return success to prevent email enumeration
        return success_response(
            message="If an account exists with that email, you will receive a password reset code."
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with OTP and new password."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Password reset failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.validated_data['user']
        otp_record = serializer.validated_data['otp_record']
        new_password = serializer.validated_data['new_password']
        
        # Update password
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        
        return success_response(
            message="Password reset successful. You can now login with your new password."
        )


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view with standardized response."""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            return success_response(
                data={'tokens': response.data},
                message="Token refreshed successfully"
            )
        
        return response
