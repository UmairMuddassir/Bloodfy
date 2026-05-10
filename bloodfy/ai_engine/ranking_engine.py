"""
AI Engine - Donor Ranking Algorithm.
Uses NumPy for vectorized score computation and Haversine distance calculation.
"""

import logging
from decimal import Decimal
from datetime import date
from typing import List, Dict, Tuple
from math import radians, cos, sin, asin, sqrt

import numpy as np

from django.db.models import Q
from django.utils import timezone

from donors.models import Donor
from requests_management.models import BloodRequest
from .models import AIRanking
from utils.constants import BLOOD_COMPATIBILITY, AI_RANKING_WEIGHTS, DISTANCE_SCORE_RANGES

logger = logging.getLogger('bloodfy')


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth (in km).
    Uses the Haversine formula.
    """
    if any(v is None for v in [lat1, lon1, lat2, lon2]):
        return float('inf')
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Earth's radius in kilometers
    r = 6371
    
    return c * r


def calculate_distance_score(distance_km: float) -> float:
    """
    Calculate distance score based on predefined ranges.
    Closer donors get higher scores.
    """
    if distance_km == float('inf'):
        return 0.0
    
    for max_distance, score in DISTANCE_SCORE_RANGES:
        if distance_km <= max_distance:
            return score
    
    return 0.0


def calculate_compatibility_score(donor_blood: str, request_blood: str) -> float:
    """
    Check blood compatibility and return score.
    Returns 100 if compatible, 0 if not.
    """
    compatible_groups = BLOOD_COMPATIBILITY.get(request_blood, [])
    return 100.0 if donor_blood in compatible_groups else 0.0


def calculate_responsiveness_score(donor: Donor) -> float:
    """
    Calculate responsiveness score based on donor's response rate.
    """
    return float(donor.response_rate)


def calculate_eligibility_score(donor: Donor) -> float:
    """
    Calculate eligibility score.
    100 if eligible, 0 if not.
    """
    return 100.0 if donor.is_eligible else 0.0


def rank_donors_for_request(
    blood_request: BloodRequest,
    max_donors: int = 10,
    max_distance_km: float = 50.0,
    include_unavailable: bool = False
) -> List[Dict]:
    """
    Main ranking algorithm.
    Finds and ranks donors based on:
    - Blood compatibility (40%)
    - Distance (30%)
    - Responsiveness (20%)
    - Eligibility (10%)
    
    Returns list of ranked donors with scores.
    """
    logger.info(f"Ranking donors for request {blood_request.id}")
    
    # Get request location
    recipient = blood_request.recipient
    request_lat = float(recipient.latitude) if recipient.latitude else None
    request_lon = float(recipient.longitude) if recipient.longitude else None
    
    # Build base query for eligible donors
    queryset = Donor.objects.filter(
        blood_group__in=BLOOD_COMPATIBILITY.get(blood_request.blood_group, []),
        is_active=True,
        is_eligible=True, # Ensure donor is not on cooldown
    ).select_related('user')
    
    if not include_unavailable:
        queryset = queryset.filter(availability_status=True)
    
    # Filter by city if no coordinates
    if request_lat is None or request_lon is None:
        queryset = queryset.filter(city__iexact=recipient.hospital_city)
    
    ranked_donors = []
    
    for donor in queryset:
        # Calculate distance
        donor_lat = float(donor.latitude) if donor.latitude else None
        donor_lon = float(donor.longitude) if donor.longitude else None
        
        if request_lat and request_lon and donor_lat and donor_lon:
            distance = haversine_distance(request_lat, request_lon, donor_lat, donor_lon)
        else:
            # Same city, approximate distance
            distance = 10.0  # Default 10km for same city
        
        # Skip if beyond max distance
        if distance > max_distance_km:
            continue
        
        # Calculate individual scores
        compatibility_score = calculate_compatibility_score(
            donor.blood_group,
            blood_request.blood_group
        )
        distance_score = calculate_distance_score(distance)
        responsiveness_score = calculate_responsiveness_score(donor)
        eligibility_score = calculate_eligibility_score(donor)
        
        # Calculate weighted final score using NumPy vectorized computation
        weights = AI_RANKING_WEIGHTS
        scores_array = np.array([
            compatibility_score,
            distance_score,
            responsiveness_score,
            eligibility_score,
        ])
        weights_array = np.array([
            weights['compatibility'],
            weights['distance'],
            weights['responsiveness'],
            weights['eligibility'],
        ])
        final_score = float(np.dot(scores_array, weights_array))
        
        ranked_donors.append({
            'donor': donor,
            'distance_km': round(distance, 2),
            'compatibility_score': compatibility_score,
            'distance_score': distance_score,
            'responsiveness_score': responsiveness_score,
            'eligibility_score': eligibility_score,
            'final_score': round(final_score, 2),
        })
    
    # Sort by final score (descending)
    ranked_donors.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Take top N donors
    ranked_donors = ranked_donors[:max_donors]
    
    # Assign rank positions
    for i, donor_data in enumerate(ranked_donors, 1):
        donor_data['rank_position'] = i
    
    logger.info(f"Found {len(ranked_donors)} donors for request {blood_request.id}")
    
    return ranked_donors


def save_rankings(blood_request: BloodRequest, ranked_donors: List[Dict]) -> List[AIRanking]:
    """
    Save ranking results to database for audit.
    """
    # Clear previous rankings for this request
    AIRanking.objects.filter(blood_request=blood_request).delete()
    
    rankings = []
    for donor_data in ranked_donors:
        ranking = AIRanking.objects.create(
            blood_request=blood_request,
            donor=donor_data['donor'],
            compatibility_score=Decimal(str(donor_data['compatibility_score'])),
            distance_score=Decimal(str(donor_data['distance_score'])),
            responsiveness_score=Decimal(str(donor_data['responsiveness_score'])),
            eligibility_score=Decimal(str(donor_data['eligibility_score'])),
            final_rank_score=Decimal(str(donor_data['final_score'])),
            rank_position=donor_data['rank_position'],
            distance_km=Decimal(str(donor_data['distance_km'])),
            algorithm_version='1.0'
        )
        rankings.append(ranking)
    
    # Update blood request with matched donors
    blood_request.ai_matched_donors.set([d['donor'] for d in ranked_donors])
    blood_request.mark_as_matched()
    
    return rankings


def process_blood_request(
    blood_request: BloodRequest,
    max_donors: int = 10,
    max_distance_km: float = 50.0
) -> Tuple[List[AIRanking], List[Dict]]:
    """
    Full processing pipeline for a blood request.
    Returns saved rankings and donor data.
    """
    # Rank donors
    ranked_donors = rank_donors_for_request(
        blood_request,
        max_donors=max_donors,
        max_distance_km=max_distance_km
    )
    
    # Save to database
    rankings = save_rankings(blood_request, ranked_donors)
    
    return rankings, ranked_donors
