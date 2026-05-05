"""
BloodBot — Live API Integration Tests
=======================================
Tests all AI Engine endpoints against the running Django server.

Pre-requisites:
  1. Server running:  python manage.py runserver
  2. A valid user in the DB (created via /api/auth/register/)

Usage:
  python test_api.py [--base-url http://127.0.0.1:8000] [--email admin@bloodify.pk] [--password admin123]
"""

import sys
import json
import argparse
import http.client
import urllib.parse

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*65}{RESET}")

def ok(label, extra=""):
    tag = f"{GREEN}✓ PASS{RESET}"
    print(f"  {tag}  {label}" + (f"  {YELLOW}({extra}){RESET}" if extra else ""))

def fail(label, extra=""):
    tag = f"{RED}✗ FAIL{RESET}"
    print(f"  {tag}  {label}" + (f"  {YELLOW}→ {extra}{RESET}" if extra else ""))

# ── HTTP helpers ──────────────────────────────────────────────────────────────

class APIClient:
    def __init__(self, base_url: str):
        parsed = urllib.parse.urlparse(base_url)
        self.host = parsed.hostname
        self.port = parsed.port or 8000
        self.token = None

    def _conn(self):
        return http.client.HTTPConnection(self.host, self.port, timeout=10)

    def _headers(self, extra=None):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def post(self, path, body=None):
        conn = self._conn()
        conn.request("POST", path, json.dumps(body or {}), self._headers())
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        return resp.status, data

    def get(self, path, params=None):
        url = path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        conn = self._conn()
        conn.request("GET", url, headers=self._headers())
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        return resp.status, data


PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        ok(label, detail)
        PASS += 1
    else:
        fail(label, detail)
        FAIL += 1


# ── Test blocks ───────────────────────────────────────────────────────────────

def test_auth(client: APIClient, email: str, password: str) -> bool:
    header("1. Authentication")
    status, data = client.post("/api/auth/login/", {"email": email, "password": password})
    check("POST /api/auth/login/ returns 200", status == 200, f"status={status}")
    if status != 200:
        print(f"\n  {RED}Cannot proceed without auth token. Check credentials.{RESET}")
        return False
    token = (data.get("data") or data).get("access") or (data.get("data") or {}).get("tokens", {}).get("access")
    check("Response contains access token", bool(token), str(token)[:20] + "..." if token else "missing")
    if token:
        client.token = token
        return True
    return False


def test_triage_emergency(client: APIClient) -> str | None:
    header("2. Triage — EMERGENCY Case")
    payload = {
        "diagnosis": "road accident with massive hemorrhage and hypovolemic shock",
        "patient_age": 32,
        "units_required": 5,
        "blood_group": "O-",
        "current_stock": 1,
    }
    status, data = client.post("/api/ai/triage/", payload)
    check("POST /api/ai/triage/ returns 201", status == 201, f"status={status}")

    body = data.get("data", data)
    urgency = body.get("urgency_level")
    check("urgency_level == 'emergency'", urgency == "emergency", f"got '{urgency}'")
    check("auto_escalate == True",        body.get("auto_escalate") is True)
    check("confidence >= 0.70",           (body.get("confidence") or 0) >= 0.70, f"got {body.get('confidence')}")
    check("reasoning is present",         bool(body.get("reasoning")))
    check("recommended_actions non-empty", len(body.get("recommended_actions", [])) > 0)
    check("triage_log_id present",        bool(body.get("triage_log_id")), body.get("triage_log_id"))
    check("method field present",         body.get("method") in ("rule_based", "llm"), f"got '{body.get('method')}'")

    print(f"\n  {CYAN}Reasoning:{RESET} {body.get('reasoning', '')[:120]}")
    print(f"  {CYAN}Actions:{RESET}")
    for a in body.get("recommended_actions", []):
        print(f"    → {a}")

    return body.get("triage_log_id")


def test_triage_urgent(client: APIClient):
    header("3. Triage — URGENT Case")
    payload = {
        "diagnosis": "thalassemia major, scheduled transfusion due within 8 hours",
        "patient_age": 14,
        "units_required": 2,
        "blood_group": "B+",
        "current_stock": 8,
    }
    status, data = client.post("/api/ai/triage/", payload)
    body = data.get("data", data)
    check("POST /api/ai/triage/ returns 201", status == 201, f"status={status}")
    check("urgency_level == 'urgent'", body.get("urgency_level") == "urgent",
          f"got '{body.get('urgency_level')}'")
    check("auto_escalate == False", body.get("auto_escalate") is False)


def test_triage_normal(client: APIClient):
    header("4. Triage — NORMAL Case")
    payload = {
        "diagnosis": "routine pre-operative blood arrangement for elective procedure scheduled in 3 days",
        "patient_age": 52,
        "units_required": 2,
        "blood_group": "A+",
        "current_stock": 15,
    }
    status, data = client.post("/api/ai/triage/", payload)
    body = data.get("data", data)
    check("POST /api/ai/triage/ returns 201", status == 201, f"status={status}")
    check("urgency_level == 'normal'", body.get("urgency_level") == "normal",
          f"got '{body.get('urgency_level')}'")


def test_triage_validation(client: APIClient):
    header("5. Triage — Input Validation")

    # Missing required diagnosis
    status, data = client.post("/api/ai/triage/", {
        "patient_age": 30, "units_required": 2, "blood_group": "A+", "current_stock": 5,
    })
    check("Missing 'diagnosis' → 400", status == 400, f"status={status}")

    # Invalid blood group
    status, data = client.post("/api/ai/triage/", {
        "diagnosis": "hemorrhage",
        "patient_age": 30,
        "units_required": 2,
        "blood_group": "Z+",
        "current_stock": 5,
    })
    check("Invalid blood_group 'Z+' → 400", status == 400, f"status={status}")

    # Missing blood_group
    status, data = client.post("/api/ai/triage/", {
        "diagnosis": "routine transfusion",
        "patient_age": 25,
        "units_required": 1,
        "current_stock": 5,
    })
    check("Missing 'blood_group' → 400", status == 400, f"status={status}")


def test_triage_logs(client: APIClient):
    header("6. Triage Logs — History (Admin)")
    status, data = client.get("/api/ai/triage/logs/")
    if status == 403:
        check("GET /api/ai/triage/logs/ (non-admin user → 403 expected)", True, "User is not admin — correct")
        return
    check("GET /api/ai/triage/logs/ returns 200", status == 200, f"status={status}")
    body = data.get("data", data)
    check("'triage_logs' key present", "triage_logs" in body)
    check("'count' key present",       "count" in body)
    count = body.get("count", 0)
    check(f"At least 1 log entry present (count={count})", count >= 1)

    # Filter by urgency
    status2, data2 = client.get("/api/ai/triage/logs/", {"urgency": "emergency"})
    check("Filter by urgency=emergency works", status2 == 200, f"status={status2}")


def test_triage_unauthenticated(client: APIClient):
    header("7. Triage — Unauthenticated Access Blocked")
    saved_token = client.token
    client.token = None

    status, _ = client.post("/api/ai/triage/", {
        "diagnosis": "hemorrhage",
        "patient_age": 30,
        "units_required": 2,
        "blood_group": "O-",
        "current_stock": 0,
    })
    check("Unauthenticated POST /api/ai/triage/ → 401", status == 401, f"status={status}")

    client.token = saved_token


def test_api_root(client: APIClient):
    header("0. API Sanity Check")
    status, data = client.get("/api/")
    check("GET /api/ returns 200", status == 200, f"status={status}")
    check("'ai_engine' listed in endpoints", "ai_engine" in str(data))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BloodBot Live API Tests")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Server base URL")
    parser.add_argument("--email",    default="admin@bloodify.pk",      help="Login email")
    parser.add_argument("--password", default="admin123",               help="Login password")
    args = parser.parse_args()

    print(f"\n{BOLD}BloodBot — Live API Integration Test Suite{RESET}")
    print(f"Target: {CYAN}{args.base_url}{RESET}")
    print(f"User:   {CYAN}{args.email}{RESET}")

    client = APIClient(args.base_url)

    try:
        test_api_root(client)

        authed = test_auth(client, args.email, args.password)
        if not authed:
            sys.exit(1)

        triage_log_id = test_triage_emergency(client)
        test_triage_urgent(client)
        test_triage_normal(client)
        test_triage_validation(client)
        test_triage_logs(client)
        test_triage_unauthenticated(client)

    except ConnectionRefusedError:
        print(f"\n{RED}✗ Cannot connect to {args.base_url}{RESET}")
        print(f"  Make sure the server is running:  python manage.py runserver")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        raise

    # ── Summary ──
    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  Results:  "
          f"{GREEN}{PASS} passed{RESET}  "
          f"{RED}{FAIL} failed{RESET}")
    print(f"{BOLD}{'='*65}{RESET}\n")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
