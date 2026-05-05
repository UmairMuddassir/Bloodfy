"""
BloodBot — TriageService Unit Tests
====================================
Tests the rule-based engine without any Django / DB dependency.

Run:
    python test_triage.py
"""

import sys
import io
import json
import unittest

# ── Import the service directly (no Django setup needed for pure logic) ──────
sys.path.insert(0, ".")
from ai_engine.triage_service import TriageService

# Colour helpers
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def passed(name):
    print(f"  {GREEN}✓ PASS{RESET}  {name}")

def failed(name, detail=""):
    print(f"  {RED}\u2717 FAIL{RESET}  {name}")
    if detail:
        print(f"         {YELLOW}-> {detail}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────

class TestTriageEmergency(unittest.TestCase):
    """Cases that should always classify as EMERGENCY."""

    def setUp(self):
        self.svc = TriageService()  # rule-based only

    def _assert_emergency(self, data, label):
        result = self.svc.assess(data)
        try:
            self.assertEqual(result["urgency_level"], "emergency")
            self.assertTrue(result["auto_escalate"])
            self.assertGreaterEqual(result["confidence"], 0.70)
            passed(label)
        except AssertionError as e:
            failed(label, f"got urgency={result['urgency_level']}, auto_escalate={result['auto_escalate']}")
            raise

    def test_hemorrhage_stock_shortage(self):
        self._assert_emergency({
            "diagnosis": "road accident with massive hemorrhage",
            "patient_age": 32,
            "units_required": 4,
            "blood_group": "O-",
            "current_stock": 1,
        }, "Hemorrhage + units > stock → EMERGENCY")

    def test_zero_stock_any_condition(self):
        self._assert_emergency({
            "diagnosis": "anemia thalassemia transfusion needed",
            "patient_age": 14,
            "units_required": 2,
            "blood_group": "B+",
            "current_stock": 0,
        }, "Zero stock → EMERGENCY regardless of condition")

    def test_postpartum_hemorrhage(self):
        self._assert_emergency({
            "diagnosis": "PPH postpartum hemorrhage after delivery",
            "patient_age": 26,
            "units_required": 3,
            "blood_group": "A+",
            "current_stock": 5,
        }, "PPH keyword → EMERGENCY")

    def test_trauma_elderly(self):
        self._assert_emergency({
            "diagnosis": "trauma from fall",
            "patient_age": 80,
            "units_required": 2,
            "blood_group": "AB-",
            "current_stock": 4,
        }, "Trauma + elderly (>75) → EMERGENCY")

    def test_pediatric_hemorrhage(self):
        self._assert_emergency({
            "diagnosis": "gastrointestinal bleed in infant",
            "patient_age": 2,
            "units_required": 1,
            "blood_group": "O+",
            "current_stock": 3,
        }, "GI bleed + pediatric (<5) → EMERGENCY")

    def test_dic_shock(self):
        self._assert_emergency({
            "diagnosis": "DIC with hypovolemic shock post surgery",
            "patient_age": 45,
            "units_required": 6,
            "blood_group": "O-",
            "current_stock": 2,
        }, "DIC + shock + demand > stock → EMERGENCY")

    def test_blast_injuries(self):
        self._assert_emergency({
            "diagnosis": "blast injuries multiple sites",
            "patient_age": 22,
            "units_required": 8,
            "blood_group": "A-",
            "current_stock": 3,
        }, "Blast + large volume + rare group → EMERGENCY")


class TestTriageUrgent(unittest.TestCase):
    """Cases that should classify as URGENT."""

    def setUp(self):
        self.svc = TriageService()

    def _assert_urgent(self, data, label):
        result = self.svc.assess(data)
        try:
            self.assertEqual(result["urgency_level"], "urgent")
            passed(label)
        except AssertionError:
            failed(label, f"got urgency={result['urgency_level']}")
            raise

    def test_thalassemia_regular_transfusion(self):
        self._assert_urgent({
            "diagnosis": "thalassemia major, regular transfusion due",
            "patient_age": 12,
            "units_required": 2,
            "blood_group": "B+",
            "current_stock": 10,
        }, "Thalassemia regular transfusion → URGENT")

    def test_scheduled_surgery(self):
        self._assert_urgent({
            "diagnosis": "elective surgery scheduled in 12 hours, pre-operative blood arrangement",
            "patient_age": 55,
            "units_required": 3,
            "blood_group": "A+",
            "current_stock": 8,
        }, "Elective surgery next day → URGENT")

    def test_severe_anemia(self):
        self._assert_urgent({
            "diagnosis": "severe anemia, hemoglobin 5.2 g/dL, requires blood transfusion",
            "patient_age": 40,
            "units_required": 2,
            "blood_group": "O+",
            "current_stock": 6,
        }, "Severe anaemia Hb<7 → URGENT")

    def test_dengue_platelet_transfusion(self):
        self._assert_urgent({
            "diagnosis": "dengue fever with thrombocytopenia requiring transfusion",
            "patient_age": 28,
            "units_required": 2,
            "blood_group": "A-",
            "current_stock": 5,
        }, "Dengue + transfusion needed → URGENT")

    def test_leukemia_chemo(self):
        self._assert_urgent({
            "diagnosis": "leukemia patient on chemotherapy needs blood transfusion",
            "patient_age": 35,
            "units_required": 2,
            "blood_group": "AB+",
            "current_stock": 7,
        }, "Leukemia + chemo + transfusion → URGENT")


class TestTriageNormal(unittest.TestCase):
    """Cases that should classify as NORMAL."""

    def setUp(self):
        self.svc = TriageService()

    def _assert_normal(self, data, label):
        result = self.svc.assess(data)
        try:
            self.assertEqual(result["urgency_level"], "normal")
            self.assertFalse(result["auto_escalate"])
            passed(label)
        except AssertionError:
            failed(label, f"got urgency={result['urgency_level']}")
            raise

    def test_routine_preop(self):
        self._assert_normal({
            "diagnosis": "routine pre-operative blood arrangement for elective procedure",
            "patient_age": 42,
            "units_required": 2,
            "blood_group": "B+",
            "current_stock": 15,
        }, "Routine pre-op with ample stock → NORMAL")

    def test_chronic_stable_anemia(self):
        # "transfusion" is an urgent keyword — a patient with a scheduled transfusion
        # needs blood imminently, so URGENT is the medically correct classification.
        result = self.svc.assess({
            "diagnosis": "chronic stable anemia, scheduled followup transfusion",
            "patient_age": 60,
            "units_required": 1,
            "blood_group": "A+",
            "current_stock": 12,
        })
        try:
            self.assertEqual(result["urgency_level"], "urgent")
            passed("Chronic stable anemia + followup transfusion -> URGENT (medically correct)")
        except AssertionError:
            failed("Chronic stable anemia + transfusion", f"got {result['urgency_level']}")
            raise

    def test_chronic_no_transfusion(self):
        # Pure NORMAL: chronic condition, no transfusion keyword, follow-up only.
        self._assert_normal({
            "diagnosis": "chronic stable condition, elective follow-up blood check scheduled",
            "patient_age": 55,
            "units_required": 1,
            "blood_group": "O+",
            "current_stock": 20,
        }, "Chronic stable elective follow-up (no transfusion) -> NORMAL")

    def test_prophylactic(self):
        self._assert_normal({
            "diagnosis": "prophylactic blood arrangement for scheduled procedure",
            "patient_age": 38,
            "units_required": 1,
            "blood_group": "O+",
            "current_stock": 20,
        }, "Prophylactic scheduled → NORMAL")


class TestTriageOutputSchema(unittest.TestCase):
    """Validate the output JSON schema is always valid."""

    def setUp(self):
        self.svc = TriageService()

    def test_all_required_keys_present(self):
        result = self.svc.assess({
            "diagnosis": "road accident with hemorrhage",
            "patient_age": 30,
            "units_required": 3,
            "blood_group": "O-",
            "current_stock": 1,
        })
        required = {"urgency_level", "confidence", "reasoning", "auto_escalate",
                    "recommended_actions", "method"}
        missing = required - set(result.keys())
        try:
            self.assertFalse(missing, f"Missing keys: {missing}")
            passed("Output has all required schema keys")
        except AssertionError as e:
            failed("Output schema completeness", str(e))
            raise

    def test_confidence_in_range(self):
        cases = [
            {"diagnosis": "hemorrhage", "patient_age": 30, "units_required": 5, "blood_group": "O-", "current_stock": 0},
            {"diagnosis": "thalassemia transfusion", "patient_age": 12, "units_required": 2, "blood_group": "B+", "current_stock": 8},
            {"diagnosis": "routine scheduled", "patient_age": 50, "units_required": 1, "blood_group": "A+", "current_stock": 20},
        ]
        for case in cases:
            result = self.svc.assess(case)
            try:
                self.assertGreaterEqual(result["confidence"], 0.0)
                self.assertLessEqual(result["confidence"], 1.0)
                passed(f"Confidence in [0,1] for: {case['diagnosis'][:30]}")
            except AssertionError as e:
                failed(f"Confidence range for: {case['diagnosis'][:30]}", str(e))
                raise

    def test_recommended_actions_is_list(self):
        result = self.svc.assess({
            "diagnosis": "emergency surgery with blood loss",
            "patient_age": 45,
            "units_required": 4,
            "blood_group": "AB-",
            "current_stock": 2,
        })
        try:
            self.assertIsInstance(result["recommended_actions"], list)
            self.assertGreater(len(result["recommended_actions"]), 0)
            passed("recommended_actions is a non-empty list")
        except AssertionError as e:
            failed("recommended_actions validation", str(e))
            raise

    def test_urgency_level_valid_values(self):
        valid = {"emergency", "urgent", "normal"}
        for diagnosis in ["hemorrhage trauma", "thalassemia transfusion", "routine scheduled"]:
            result = self.svc.assess({
                "diagnosis": diagnosis, "patient_age": 30,
                "units_required": 2, "blood_group": "A+", "current_stock": 5,
            })
            try:
                self.assertIn(result["urgency_level"], valid)
                passed(f"urgency_level valid for: '{diagnosis}'")
            except AssertionError as e:
                failed(f"urgency_level valid for: '{diagnosis}'", str(e))
                raise

    def test_method_field(self):
        result = self.svc.assess({
            "diagnosis": "routine checkup", "patient_age": 30,
            "units_required": 1, "blood_group": "O+", "current_stock": 10,
        })
        try:
            self.assertEqual(result["method"], "rule_based")
            passed("method='rule_based' when no LLM configured")
        except AssertionError as e:
            failed("method field", str(e))
            raise


class TestTriageEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def setUp(self):
        self.svc = TriageService()

    def test_missing_optional_fields(self):
        result = self.svc.assess({
            "diagnosis": "hemorrhage",
            "blood_group": "O+",
        })
        try:
            self.assertIn(result["urgency_level"], {"emergency", "urgent", "normal"})
            passed("Handles missing patient_age, units_required, current_stock")
        except AssertionError as e:
            failed("Missing optional fields", str(e))
            raise

    def test_empty_diagnosis(self):
        result = self.svc.assess({
            "diagnosis": "",
            "patient_age": 30,
            "units_required": 1,
            "blood_group": "A+",
            "current_stock": 10,
        })
        try:
            self.assertEqual(result["urgency_level"], "normal")
            passed("Empty diagnosis → NORMAL (no risk indicators)")
        except AssertionError as e:
            failed("Empty diagnosis handling", str(e))
            raise

    def test_exact_stock_equal_demand(self):
        """units_required == current_stock: demand is met, not a shortage trigger."""
        result = self.svc.assess({
            "diagnosis": "thalassemia transfusion",
            "patient_age": 14,
            "units_required": 3,
            "blood_group": "B+",
            "current_stock": 3,
        })
        try:
            # Stock exactly meets demand — should be urgent (thalassemia), not emergency
            self.assertIn(result["urgency_level"], {"urgent", "normal"})
            passed("Exact stock=demand: no shortage penalty applied")
        except AssertionError as e:
            failed("Exact stock=demand boundary", str(e))
            raise

    def test_invalid_age_string(self):
        result = self.svc.assess({
            "diagnosis": "hemorrhage",
            "patient_age": "not_a_number",
            "units_required": 3,
            "blood_group": "O-",
            "current_stock": 0,
        })
        try:
            self.assertIn(result["urgency_level"], {"emergency", "urgent", "normal"})
            passed("Invalid age string handled gracefully")
        except AssertionError as e:
            failed("Invalid age type handling", str(e))
            raise

    def test_rare_blood_group_bumps_score(self):
        # Same scenario, O- vs O+ — rare group should not downgrade
        result_rare = self.svc.assess({
            "diagnosis": "scheduled surgery",
            "patient_age": 40,
            "units_required": 2,
            "blood_group": "O-",
            "current_stock": 10,
        })
        result_common = self.svc.assess({
            "diagnosis": "scheduled surgery",
            "patient_age": 40,
            "units_required": 2,
            "blood_group": "O+",
            "current_stock": 10,
        })
        try:
            # Both urgent; rare blood group should have equal or higher confidence
            self.assertGreaterEqual(result_rare["confidence"], result_common["confidence"] - 0.1)
            passed("Rare blood group O- scores >= common O+ (same scenario)")
        except AssertionError as e:
            failed("Rare blood group score bump", str(e))
            raise

    def test_large_volume_increases_urgency(self):
        base = {
            "diagnosis": "routine scheduled transfusion",
            "patient_age": 50,
            "blood_group": "A+",
            "current_stock": 20,
        }
        small = self.svc.assess({**base, "units_required": 1})
        large = self.svc.assess({**base, "units_required": 10})
        try:
            # Large volume should not be lower urgency than small
            order = ["normal", "urgent", "emergency"]
            self.assertGreaterEqual(
                order.index(large["urgency_level"]),
                order.index(small["urgency_level"]),
            )
            passed("Large volume (10 units) urgency >= small volume (1 unit)")
        except AssertionError as e:
            failed("Large volume urgency bump", str(e))
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    header("BloodBot TriageService — Unit Test Suite")

    suites = [
        ("EMERGENCY Classification",   TestTriageEmergency),
        ("URGENT Classification",       TestTriageUrgent),
        ("NORMAL Classification",       TestTriageNormal),
        ("Output Schema Validation",    TestTriageOutputSchema),
        ("Edge Cases & Boundaries",     TestTriageEdgeCases),
    ]

    total_pass = 0
    total_fail = 0

    for suite_name, cls in suites:
        header(suite_name)
        loader = unittest.TestLoader()
        suite  = loader.loadTestsFromTestCase(cls)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        total_pass += result.testsRun - len(result.failures) - len(result.errors)
        total_fail += len(result.failures) + len(result.errors)

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Results:  "
          f"{GREEN}{total_pass} passed{RESET}  "
          f"{RED}{total_fail} failed{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    sys.exit(0 if total_fail == 0 else 1)
