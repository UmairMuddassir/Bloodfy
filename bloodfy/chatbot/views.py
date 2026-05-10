"""
Chatbot app views.
"""

import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone

from .models import FAQ, ChatSession, ChatMessage
from .serializers import (
    FAQSerializer, FAQListSerializer, ChatQuerySerializer,
    ChatResponseSerializer, ChatSessionSerializer,
    ChatMessageSerializer, FeedbackSerializer
)
from .services import ChatbotService
from utils.responses import success_response, error_response, created_response
from utils.permissions import IsAdmin


class ChatQueryView(APIView):
    """Process chatbot queries."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Process a chat message."""
        serializer = ChatQuerySerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        
        try:
            # Get or create session
            session = None
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except (ChatSession.DoesNotExist, Exception):
                    session = None
            
            if not session:
                session = ChatSession.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    session_key=str(uuid.uuid4())
                )
            
            # Save user message
            ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=message
            )
            
            # Process with chatbot service
            service = ChatbotService(
                user=request.user if request.user.is_authenticated else None
            )
            response_data = service.process_query(message, str(session.id))
            
            # Save bot response — handle faq_id carefully
            faq_id = response_data.get('faq_id')
            faq_obj = None
            if faq_id:
                try:
                    faq_obj = FAQ.objects.get(id=faq_id)
                except (FAQ.DoesNotExist, Exception):
                    faq_obj = None
            
            ChatMessage.objects.create(
                session=session,
                message_type='bot',
                content=response_data['message'],
                intent=response_data.get('intent', 'unknown'),
                confidence=response_data.get('confidence', 0.5),
                faq_matched=faq_obj
            )
            
            # Update session message count
            session.message_count += 2
            session.save(update_fields=['message_count'])
            
            return success_response(
                data={
                    'message': response_data['message'],
                    'intent': response_data.get('intent', 'unknown'),
                    'confidence': response_data.get('confidence', 0.5),
                    'session_id': str(session.id),
                    'faq_id': response_data.get('faq_id'),
                    'suggestions': response_data.get('suggestions', [])
                },
                message="Query processed"
            )
        
        except Exception as e:
            import traceback
            print(f"[CHATBOT ERROR] {traceback.format_exc()}")
            
            # Return a helpful fallback response instead of crashing
            return success_response(
                data={
                    'message': (
                        "I'm the Bloodify AI Assistant! 🤖\n\n"
                        "I can help you with:\n"
                        "🩸 Blood stock & availability\n"
                        "👤 Donor registration & eligibility\n"
                        "🔍 Finding compatible donors\n"
                        "🚨 Emergency blood requests\n\n"
                        "Try asking: \"Check A+ stock\" or \"Am I eligible to donate?\""
                    ),
                    'intent': 'fallback',
                    'confidence': 0.5,
                    'session_id': None,
                    'faq_id': None,
                    'suggestions': [
                        "Check blood stock",
                        "How to register?",
                        "Am I eligible?",
                        "Emergency request"
                    ]
                },
                message="Query processed"
            )


class FAQListView(APIView):
    """List FAQs."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get list of FAQs."""
        category = request.query_params.get('category')
        search = request.query_params.get('search')
        
        queryset = FAQ.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if search:
            queryset = queryset.filter(
                question__icontains=search
            ) | queryset.filter(
                answer__icontains=search
            )
        
        queryset = queryset.order_by('-priority', '-view_count')
        
        serializer = FAQListSerializer(queryset, many=True)
        
        return success_response(
            data={
                'faqs': serializer.data,
                'count': queryset.count()
            },
            message="FAQs retrieved"
        )


class FAQDetailView(APIView):
    """Get FAQ details."""
    
    permission_classes = [AllowAny]
    
    def get(self, request, faq_id):
        """Get FAQ details."""
        try:
            faq = FAQ.objects.get(id=faq_id, is_active=True)
        except FAQ.DoesNotExist:
            return error_response(
                message="FAQ not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Increment view count
        faq.view_count += 1
        faq.save(update_fields=['view_count'])
        
        serializer = FAQSerializer(faq)
        
        return success_response(
            data=serializer.data,
            message="FAQ retrieved"
        )


class FAQManagementView(APIView):
    """Manage FAQs (Admin only)."""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Create new FAQ."""
        serializer = FAQSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Failed to create FAQ",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        faq = serializer.save()
        
        return created_response(
            data=FAQSerializer(faq).data,
            message="FAQ created"
        )
    
    def put(self, request, faq_id):
        """Update FAQ."""
        try:
            faq = FAQ.objects.get(id=faq_id)
        except FAQ.DoesNotExist:
            return error_response(
                message="FAQ not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = FAQSerializer(faq, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return error_response(
                message="Update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        return success_response(
            data=FAQSerializer(faq).data,
            message="FAQ updated"
        )
    
    def delete(self, request, faq_id):
        """Delete FAQ."""
        try:
            faq = FAQ.objects.get(id=faq_id)
        except FAQ.DoesNotExist:
            return error_response(
                message="FAQ not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        faq.is_active = False
        faq.save(update_fields=['is_active'])
        
        return success_response(
            message="FAQ deleted"
        )


class ChatFeedbackView(APIView):
    """Submit feedback for chat responses."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Submit feedback."""
        serializer = FeedbackSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        message_id = serializer.validated_data['message_id']
        was_helpful = serializer.validated_data['was_helpful']
        
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return error_response(
                message="Message not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        message.was_helpful = was_helpful
        message.save(update_fields=['was_helpful'])
        
        return success_response(
            message="Feedback submitted"
        )
