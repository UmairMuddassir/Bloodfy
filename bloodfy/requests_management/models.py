"""
Requests Management app models.
"""

import uuid
from django.db import models
from django.utils import timezone
from recipients.models import Recipient
from donors.models import Donor
from utils.constants import BLOOD_GROUPS, URGENCY_LEVELS, REQUEST_STATUS
from utils.validators import validate_blood_group, validate_units


class BloodRequest(models.Model):
    """
    Blood Request model.
    Tracks blood donation requests from recipients.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    recipient = models.ForeignKey(
        Recipient,
        on_delete=models.CASCADE,
        related_name='blood_requests'
    )
    
    # Blood requirement details
    blood_group = models.CharField(
        max_length=5,
        choices=BLOOD_GROUPS,
        validators=[validate_blood_group],
        verbose_name='Required Blood Group'
    )
    
    units_required = models.PositiveIntegerField(
        validators=[validate_units],
        verbose_name='Units Required'
    )
    
    units_fulfilled = models.PositiveIntegerField(
        default=0,
        verbose_name='Units Fulfilled'
    )
    
    # Hospital details (can override recipient's default)
    hospital_name = models.CharField(
        max_length=255,
        verbose_name='Hospital Name'
    )
    
    hospital_address = models.TextField(
        verbose_name='Hospital Address'
    )
    
    hospital_city = models.CharField(
        max_length=100,
        verbose_name='City'
    )
    
    # Request urgency and status
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_LEVELS,
        default='normal',
        verbose_name='Urgency Level'
    )
    
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default='pending',
        verbose_name='Request Status'
    )
    
    # AI-matched donors
    ai_matched_donors = models.ManyToManyField(
        Donor,
        related_name='matched_requests',
        blank=True,
        verbose_name='AI Matched Donors'
    )
    
    # Patient information
    patient_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Patient Name'
    )
    
    patient_age = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Patient Age'
    )
    
    diagnosis = models.TextField(
        blank=True,
        null=True,
        verbose_name='Diagnosis/Reason'
    )
    
    doctor_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Attending Doctor'
    )
    
    # Additional notes
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Additional Notes'
    )
    
    # Admin approval
    is_approved = models.BooleanField(
        default=False,
        verbose_name='Admin Approved'
    )
    
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests'
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True
    )
    
    # Assigned donor (after admin choice)
    assigned_donor = models.ForeignKey(
        Donor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        verbose_name='Assigned Donor'
    )
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    matched_at = models.DateTimeField(blank=True, null=True)
    assigned_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Blood Request'
        verbose_name_plural = 'Blood Requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['blood_group']),
            models.Index(fields=['status']),
            models.Index(fields=['urgency_level']),
            models.Index(fields=['hospital_city']),
            models.Index(fields=['requested_at']),
        ]
    
    def __str__(self):
        return f"Request #{str(self.id)[:8]} - {self.blood_group} ({self.units_required} units)"
    
    @property
    def is_urgent(self):
        """Check if request is urgent or emergency."""
        return self.urgency_level in ['urgent', 'emergency']
    
    @property
    def is_fulfilled(self):
        """Check if request has been fully fulfilled."""
        return self.units_fulfilled >= self.units_required
    
    @property
    def remaining_units(self):
        """Calculate remaining units needed."""
        return max(0, self.units_required - self.units_fulfilled)
    
    def mark_as_matched(self):
        """Mark the request as matched with donors."""
        self.status = 'matched'
        self.matched_at = timezone.now()
        self.save(update_fields=['status', 'matched_at', 'updated_at'])
    
    def assign_donor(self, donor):
        """Assign a specific donor to this request."""
        self.assigned_donor = donor
        self.status = 'assigned'
        self.assigned_at = timezone.now()
        self.save(update_fields=['assigned_donor', 'status', 'assigned_at', 'updated_at'])

        # Notify the recipient
        try:
            from notifications.models import AppNotification
            
            donor_name = donor.user.get_full_name()
            donor_phone = donor.user.phone_number
            
            AppNotification.objects.create(
                user=self.recipient.user,
                title="Donor Assigned to Your Request",
                message=f"Administrator has assigned a donor for your {self.blood_group} request. Donor: {donor_name}, Contact: {donor_phone}. Please coordinate immediately.",
                notification_type='assignment',
                related_id=str(self.id)
            )
        except Exception as e:
            print(f"Error notifying recipient of donor assignment: {e}")
    
    def mark_as_completed(self):
        """Mark the request as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def mark_as_cancelled(self, reason=None):
        """Mark the request as cancelled."""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.notes = f"{self.notes or ''}\nCancellation reason: {reason}"
        self.save(update_fields=['status', 'cancelled_at', 'notes', 'updated_at'])
    
    def approve(self, admin_user):
        """Approve the blood request."""
        self.is_approved = True
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save(update_fields=['is_approved', 'approved_by', 'approved_at', 'updated_at'])

    def find_matches(self):
        """Find and link eligible donors to this request using AI logic."""
        from ai_engine.ranking_engine import process_blood_request
        
        # Trigger the actual AI Ranking Engine
        # This will calculate scores and save AIRanking logs to the database!
        try:
            rankings, donors = process_blood_request(self, max_donors=15, max_distance_km=100)
            
            matches_found = 0
            for ranked_donor in donors:
                # Add to many-to-many relationship
                self.ai_matched_donors.add(ranked_donor)
                
                # Create response record so they see it in their dashboard
                DonorResponse.objects.get_or_create(
                    blood_request=self,
                    donor=ranked_donor,
                    defaults={'response_status': 'pending'}
                )
                
                # Update donor metrics
                ranked_donor.total_requests_received += 1
                ranked_donor.save(update_fields=['total_requests_received'])
                matches_found += 1
                
            if matches_found > 0:
                self.mark_as_matched()
            
            return matches_found
        except Exception as e:
            print(f"Error in find_matches using AI ranking: {e}")
            return 0


class DonorResponse(models.Model):
    """
    Track individual donor responses to blood requests.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.CASCADE,
        related_name='donor_responses'
    )
    
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name='request_responses'
    )
    
    response_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined'),
            ('no_response', 'No Response'),
        ],
        default='pending'
    )
    
    response_at = models.DateTimeField(
        blank=True,
        null=True
    )
    
    decline_reason = models.TextField(
        blank=True,
        null=True
    )
    
    # Timestamps
    notified_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Donor Response'
        verbose_name_plural = 'Donor Responses'
        unique_together = ['blood_request', 'donor']
        ordering = ['-notified_at']
    
    def __str__(self):
        return f"{self.donor} - {self.blood_request} ({self.response_status})"
    
    def accept(self):
        """Mark response as accepted."""
        self.response_status = 'accepted'
        self.response_at = timezone.now()
        self.save(update_fields=['response_status', 'response_at', 'updated_at'])
        
        # Update donor statistics
        self.donor.total_requests_accepted += 1
        self.donor.save(update_fields=['total_requests_accepted'])
        self.donor.update_response_rate()
    
    def decline(self, reason=None):
        """Mark response as declined."""
        self.response_status = 'declined'
        self.response_at = timezone.now()
        self.decline_reason = reason
        self.save(update_fields=['response_status', 'response_at', 'decline_reason', 'updated_at'])
        
        # Update donor response rate
        self.donor.update_response_rate()
