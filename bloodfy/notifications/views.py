"""
Notifications app views.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from .models import NotificationLog, NotificationTemplate, AppNotification
from .serializers import (
    NotificationLogSerializer, NotificationLogListSerializer,
    SendManualNotificationSerializer, NotificationTemplateSerializer,
    NotificationStatsSerializer, AppNotificationSerializer
)
from donors.models import Donor
from utils.responses import success_response, error_response, created_response
from utils.permissions import IsAdmin


class NotificationListView(APIView):
    """List notifications."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get notifications based on user role."""
        if request.user.user_type == 'admin':
            queryset = NotificationLog.objects.select_related('donor__user').all()
        elif hasattr(request.user, 'donor_profile'):
            queryset = NotificationLog.objects.filter(
                donor=request.user.donor_profile
            )
        else:
            queryset = NotificationLog.objects.none()
        
        # Apply filters
        message_type = request.query_params.get('type')
        delivery_status = request.query_params.get('status')
        
        if message_type:
            queryset = queryset.filter(message_type=message_type)
        if delivery_status:
            queryset = queryset.filter(delivery_status=delivery_status)
        
        queryset = queryset.order_by('-created_at')[:100]
        serializer = NotificationLogListSerializer(queryset, many=True)
        
        return success_response(
            data={
                'notifications': serializer.data,
                'count': queryset.count()
            },
            message="Notifications retrieved"
        )


class SendManualNotificationView(APIView):
    """Send manual notification (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Send a manual notification to a donor."""
        serializer = SendManualNotificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        donor_id = serializer.validated_data['donor_id']
        message_type = serializer.validated_data['message_type']
        message_content = serializer.validated_data['message_content']
        
        try:
            donor = Donor.objects.select_related('user').get(id=donor_id)
        except Donor.DoesNotExist:
            return error_response(
                message="Donor not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Create notification log
        notification = NotificationLog.objects.create(
            donor=donor,
            message_type=message_type,
            message_content=message_content,
            subject=serializer.validated_data.get('subject'),
            recipient_phone=donor.user.phone_number,
            recipient_email=donor.user.email,
            delivery_status='pending'
        )
        
        # Notification delivery — logs the notification and marks as sent.
        # Twilio/Email integration can be added by implementing a delivery
        # service and calling it here before updating the status.
        from django.utils import timezone
        import logging
        logger = logging.getLogger('bloodfy')
        
        logger.info(
            "Notification [%s] to %s (%s): %s",
            message_type,
            donor.user.get_full_name(),
            notification.recipient_phone or notification.recipient_email,
            message_content[:80],
        )
        notification.delivery_status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        
        return created_response(
            data=NotificationLogSerializer(notification).data,
            message="Notification sent successfully"
        )


class NotificationLogsView(APIView):
    """View detailed notification logs (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get detailed notification logs."""
        queryset = NotificationLog.objects.select_related(
            'donor__user', 'blood_request'
        ).order_by('-created_at')[:200]
        
        serializer = NotificationLogSerializer(queryset, many=True)
        
        return success_response(
            data={
                'logs': serializer.data,
                'count': queryset.count()
            },
            message="Notification logs retrieved"
        )


class NotificationStatsView(APIView):
    """Get notification statistics (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get notification statistics."""
        logs = NotificationLog.objects.all()
        
        total = logs.count()
        sent = logs.filter(delivery_status='sent').count()
        delivered = logs.filter(delivery_status='delivered').count()
        failed = logs.filter(delivery_status='failed').count()
        pending = logs.filter(delivery_status='pending').count()
        
        # Response stats
        responded = logs.exclude(response_status='pending').exclude(response_status='no_response').count()
        
        by_type = dict(
            logs.values('message_type')
            .annotate(count=Count('id'))
            .values_list('message_type', 'count')
        )
        
        by_status = dict(
            logs.values('delivery_status')
            .annotate(count=Count('id'))
            .values_list('delivery_status', 'count')
        )
        
        data = {
            'total_sent': total,
            'total_delivered': delivered,
            'total_failed': failed,
            'total_pending': pending,
            'delivery_rate': round((delivered / total * 100) if total > 0 else 0, 2),
            'response_rate': round((responded / total * 100) if total > 0 else 0, 2),
            'by_type': by_type,
            'by_status': by_status
        }
        
        return success_response(
            data=data,
            message="Notification stats retrieved"
        )


class NotificationTemplateListView(APIView):
    """List and create notification templates."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """List all templates."""
        templates = NotificationTemplate.objects.filter(is_active=True)
        serializer = NotificationTemplateSerializer(templates, many=True)
        
        return success_response(
            data={
                'templates': serializer.data,
                'count': templates.count()
            },
            message="Templates retrieved"
        )
    
    def post(self, request):
        """Create new template."""
        serializer = NotificationTemplateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to create template",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        template = serializer.save()
        
        return created_response(
            data=NotificationTemplateSerializer(template).data,
            message="Template created"
        )

class AppNotificationAPIView(APIView):
    """View for managing in-app notifications."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's notifications."""
        notifications = AppNotification.objects.filter(user=request.user).order_by('-created_at')[:50]
        unread_count = AppNotification.objects.filter(user=request.user, is_read=False).count()
        
        serializer = AppNotificationSerializer(notifications, many=True)
        
        return success_response(
            data={
                'notifications': serializer.data,
                'unread_count': unread_count
            },
            message="In-app notifications retrieved"
        )
    
    def post(self, request, notification_id=None):
        """Mark notification as read."""
        if notification_id:
            try:
                notification = AppNotification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
                return success_response(message="Notification marked as read")
            except AppNotification.DoesNotExist:
                return error_response(message="Notification not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Mark all as read if no ID provided
        AppNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return success_response(message="All notifications marked as read")
