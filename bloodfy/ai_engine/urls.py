"""
AI Engine app URL routes.
"""

from django.urls import path
from .views import (
    RankDonorsView,
    RankingHistoryView,
    ReactivationCheckView,
    AIMetricsView,
    TriageAssessView,
    TriageLogListView,
    TriageOverrideView,
)

urlpatterns = [
    # Donor ranking
    path('rank-donors/', RankDonorsView.as_view(), name='ai-rank-donors'),
    path('ranking-history/<uuid:request_id>/', RankingHistoryView.as_view(), name='ai-ranking-history'),
    path('reactivation-check/', ReactivationCheckView.as_view(), name='ai-reactivation-check'),
    path('metrics/', AIMetricsView.as_view(), name='ai-metrics'),

    # Medical urgency triage
    path('triage/', TriageAssessView.as_view(), name='ai-triage-assess'),
    path('triage/logs/', TriageLogListView.as_view(), name='ai-triage-logs'),
    path('triage/<uuid:triage_id>/override/', TriageOverrideView.as_view(), name='ai-triage-override'),
]
