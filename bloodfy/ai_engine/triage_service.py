"""
AI Engine — Medical Urgency Triage Service.

Assesses blood request urgency using a rule-based engine with an optional
LLM upgrade path (Gemini / OpenAI).  Falls back gracefully if LLM is
unavailable.

Usage:
    from ai_engine.triage_service import TriageService

    service = TriageService()
    result  = service.assess({
        "diagnosis": "road accident with hemorrhage",
        "patient_age": 32,
        "units_required": 4,
        "blood_group": "O-",
        "current_stock": 1,
    })
    print(result)
    # {
    #   "urgency_level": "emergency",
    #   "confidence": 0.95,
    #   "reasoning": "...",
    #   "auto_escalate": True,
    #   "recommended_actions": [...]
    # }
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional


def _keyword_match(keyword: str, text: str) -> bool:
    """
    Return True if `keyword` appears in `text` as a whole-word/phrase match.
    Uses regex word boundaries so 'stab' won't match inside 'stable'.
    Multi-word phrases (e.g. 'road accident') are matched as-is (spaces already
    serve as natural boundaries).
    """
    pattern = r'(?<![\w-])' + re.escape(keyword) + r'(?![\w-])'
    return bool(re.search(pattern, text))

logger = logging.getLogger("bloodfy")

# ---------------------------------------------------------------------------
# Keyword banks (lowercased)
# ---------------------------------------------------------------------------

EMERGENCY_KEYWORDS: List[str] = [
    "hemorrhage", "haemorrhage", "hemorrhaging",
    "trauma", "accident", "road accident", "rta",
    "massive blood loss", "blood loss",
    "shock", "hypovolemic shock",
    "dic", "disseminated intravascular",
    "pph", "postpartum hemorrhage", "postpartum haemorrhage",
    "placenta previa", "ruptured uterus",
    "emergency surgery", "emergency c-section", "emergency cesarean",
    "stab", "gunshot", "blast", "burn",
    "ruptured aneurysm", "gi bleed", "gastrointestinal bleed",
    "cardiac surgery emergency",
]

URGENT_KEYWORDS: List[str] = [
    "surgery", "operation", "thalassemia", "thalassaemia",
    "severe anemia", "severe anaemia",
    "transfusion", "blood transfusion",
    "hemoglobin", "haemoglobin",
    "dengue", "liver failure", "kidney failure",
    "leukemia", "leukaemia", "lymphoma", "chemotherapy",
    "aplastic anemia", "sickle cell",
    "scheduled surgery",
    # NOTE: 'pre-operative' removed — too broad; routine pre-op is NORMAL.
    # It is covered by 'scheduled surgery' when surgery is actually imminent.
]

NORMAL_KEYWORDS: List[str] = [
    "routine", "scheduled", "elective",
    "followup", "follow-up", "follow up",
    "pre-operative arrangement", "prophylactic",
    "chronic", "stable",
]


# ---------------------------------------------------------------------------
# Rule-based triage engine
# ---------------------------------------------------------------------------

class TriageResult:
    """Immutable triage assessment result."""

    __slots__ = (
        "urgency_level",
        "confidence",
        "reasoning",
        "auto_escalate",
        "recommended_actions",
        "method",
    )

    def __init__(
        self,
        urgency_level: str,
        confidence: float,
        reasoning: str,
        auto_escalate: bool,
        recommended_actions: List[str],
        method: str = "rule_based",
    ):
        self.urgency_level = urgency_level
        self.confidence = round(min(max(confidence, 0.0), 1.0), 2)
        self.reasoning = reasoning
        self.auto_escalate = auto_escalate
        self.recommended_actions = recommended_actions
        self.method = method

    def to_dict(self) -> Dict[str, Any]:
        return {
            "urgency_level": self.urgency_level,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "auto_escalate": self.auto_escalate,
            "recommended_actions": self.recommended_actions,
            "method": self.method,
        }


class TriageService:
    """
    Medical Urgency Triage engine.

    1.  Attempts LLM-based assessment (if a provider is configured).
    2.  Falls back to deterministic rule-based assessment.
    """

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: Optional LLM provider instance (see llm_provider.py).
                          If ``None``, pure rule-based assessment is used.
        """
        self._llm = llm_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the urgency of a blood request.

        Args:
            request_data: Dict with keys ``diagnosis``, ``patient_age``,
                ``units_required``, ``blood_group``, ``current_stock``.

        Returns:
            Dict matching the TriageResult schema.
        """
        # Normalise inputs
        diagnosis = str(request_data.get("diagnosis", "")).lower().strip()
        patient_age = self._safe_int(request_data.get("patient_age"), default=None)
        units_required = self._safe_int(request_data.get("units_required"), 1)
        blood_group = str(request_data.get("blood_group", "")).upper().strip()
        current_stock = self._safe_int(request_data.get("current_stock"), 0)

        # Try LLM first (if configured)
        if self._llm is not None:
            try:
                llm_result = self._assess_with_llm(
                    diagnosis, patient_age, units_required,
                    blood_group, current_stock
                )
                if llm_result is not None:
                    return llm_result.to_dict()
            except Exception as exc:
                logger.warning("LLM triage failed, falling back to rules: %s", exc)

        # Deterministic fallback
        result = self._assess_rule_based(
            diagnosis, patient_age, units_required,
            blood_group, current_stock
        )
        return result.to_dict()

    # ------------------------------------------------------------------
    # Rule-based engine
    # ------------------------------------------------------------------

    def _assess_rule_based(
        self,
        diagnosis: str,
        patient_age: Optional[int],
        units_required: int,
        blood_group: str,
        current_stock: int,
    ) -> TriageResult:
        """Deterministic rule-based urgency assessment."""

        reasons: List[str] = []
        actions: List[str] = []
        score = 0  # Higher = more urgent.  >=80 → emergency, >=40 → urgent

        # ---- Stock shortage (immediate trigger) ----
        if current_stock == 0 and units_required > 0:
            score += 90
            reasons.append(
                f"Zero stock available for {blood_group} but {units_required} unit(s) needed"
            )
            actions.append("Initiate emergency donor call-out immediately")
            actions.append("Contact neighbouring blood banks for transfer")
        elif units_required > current_stock:
            score += 60
            reasons.append(
                f"Demand ({units_required} units) exceeds available stock ({current_stock} units)"
            )
            actions.append("Reserve all available stock and search for additional donors")

        # ---- Keyword matching ----
        emergency_hits = [kw for kw in EMERGENCY_KEYWORDS if _keyword_match(kw, diagnosis)]
        urgent_hits    = [kw for kw in URGENT_KEYWORDS    if _keyword_match(kw, diagnosis)]
        normal_hits    = [kw for kw in NORMAL_KEYWORDS    if _keyword_match(kw, diagnosis)]

        if emergency_hits:
            score += 80
            reasons.append(
                f"Emergency keywords detected: {', '.join(emergency_hits[:3])}"
            )
            actions.append("Alert all available donors within 10 km radius")
        elif urgent_hits:
            score += 40
            reasons.append(
                f"Urgent condition detected: {', '.join(urgent_hits[:3])}"
            )
            actions.append("Trigger AI donor matching for compatible donors")
        elif normal_hits:
            score += 10
            reasons.append("Routine/scheduled request")

        # ---- Age vulnerability ----
        if patient_age is not None:
            if patient_age < 5:
                score += 25
                reasons.append(f"Pediatric patient (age {patient_age})")
                actions.append("Prioritise pediatric-compatible blood units")
            elif patient_age > 75:
                score += 20
                reasons.append(f"Elderly patient (age {patient_age})")
                actions.append("Ensure cross-match compatibility is verified")

        # ---- Large volume ----
        if units_required >= 5:
            score += 15
            reasons.append(f"Large volume required ({units_required} units)")
            actions.append("Prepare multiple bags and begin staged transfusion plan")

        # ---- Rare blood group ----
        if blood_group in ("AB-", "B-", "O-"):
            score += 10
            reasons.append(f"Rare blood group ({blood_group})")
            actions.append(f"Search expanded network for {blood_group} donors")

        # ---- Classify ----
        if score >= 80:
            level = "emergency"
            confidence = min(0.95, 0.70 + (score - 80) * 0.005)
            auto_escalate = True
        elif score >= 40:
            level = "urgent"
            confidence = min(0.90, 0.65 + (score - 40) * 0.005)
            auto_escalate = False
        else:
            level = "normal"
            confidence = 0.80 if reasons else 0.60
            auto_escalate = False

        # Fallback reasoning if nothing matched
        if not reasons:
            reasons.append("No high-risk indicators detected in diagnosis text")
        if not actions:
            actions.append("Process through standard request queue")
            actions.append("Notify matched donors via regular channels")

        return TriageResult(
            urgency_level=level,
            confidence=confidence,
            reasoning=". ".join(reasons) + ".",
            auto_escalate=auto_escalate,
            recommended_actions=actions,
            method="rule_based",
        )

    # ------------------------------------------------------------------
    # LLM-powered engine (optional upgrade)
    # ------------------------------------------------------------------

    def _assess_with_llm(
        self,
        diagnosis: str,
        patient_age: Optional[int],
        units_required: int,
        blood_group: str,
        current_stock: int,
    ) -> Optional[TriageResult]:
        """Use the configured LLM provider for triage."""

        prompt = self._build_triage_prompt(
            diagnosis, patient_age, units_required, blood_group, current_stock
        )

        raw_response = self._llm.generate(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
            temperature=0.1,  # Low creativity — medical context
            max_tokens=500,
            timeout_seconds=5,
        )

        if not raw_response:
            return None

        return self._parse_llm_response(raw_response)

    def _system_prompt(self) -> str:
        return (
            "You are BloodBot, the medical urgency triage AI for the Bloodify "
            "blood bank system in Pakistan. Given patient data, classify the "
            "request urgency as 'emergency', 'urgent', or 'normal'. "
            "Return ONLY a valid JSON object with keys: urgency_level, "
            "confidence (0.0-1.0), reasoning (1-2 sentences), auto_escalate "
            "(bool), recommended_actions (list of strings). "
            "ALWAYS err on the side of caution — escalate when uncertain. "
            "Consider the Pakistan healthcare context."
        )

    def _build_triage_prompt(
        self,
        diagnosis: str,
        patient_age: Optional[int],
        units_required: int,
        blood_group: str,
        current_stock: int,
    ) -> str:
        return json.dumps({
            "diagnosis": diagnosis,
            "patient_age": patient_age,
            "units_required": units_required,
            "blood_group": blood_group,
            "current_stock": current_stock,
        }, indent=2)

    def _parse_llm_response(self, raw: str) -> Optional[TriageResult]:
        """Parse LLM JSON output into a TriageResult."""
        try:
            # Strip markdown fences if present
            cleaned = re.sub(r"```json\s*", "", raw)
            cleaned = re.sub(r"```\s*", "", cleaned)
            data = json.loads(cleaned.strip())

            level = data.get("urgency_level", "normal").lower()
            if level not in ("emergency", "urgent", "normal"):
                level = "urgent"  # Default safe

            return TriageResult(
                urgency_level=level,
                confidence=float(data.get("confidence", 0.75)),
                reasoning=str(data.get("reasoning", "LLM assessment")),
                auto_escalate=bool(data.get("auto_escalate", level == "emergency")),
                recommended_actions=list(data.get("recommended_actions", [])),
                method="llm",
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Failed to parse LLM triage response: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
        """Safely convert a value to int.

        Returns ``default`` when value is None or unconvertible.
        Pass ``default=None`` explicitly to allow None returns (e.g. patient_age).
        """
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
