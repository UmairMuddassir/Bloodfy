# 🩸 Bloodify — Project Demo Guide
## Step-by-Step Presentation for Your Teacher

---

## 📋 BEFORE THE PRESENTATION (Preparation)

Make sure these are installed on the laptop:
- **Python 3.13+** (already installed)
- **Any browser** (Chrome recommended)
- **PowerShell** (built-in on Windows)

---

## 🚀 STEP 1: Start the Backend Server

Open **PowerShell** (Terminal 1) and run these commands one by one:

```powershell
cd C:\Users\Umair\Desktop\Bloodify\Bloodfy\bloodfy
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

**What to tell your teacher:**
> "This starts our Django REST API server at port 8000. It handles authentication, blood requests, donor management, AI triage, and the chatbot."

✅ You should see: `Starting development server at http://127.0.0.1:8000/`

**⚠️ Keep this terminal open the entire time. Don't close it.**

---

## 🚀 STEP 2: Start the Frontend Server

Open a **second PowerShell** (Terminal 2) and run:

```powershell
cd C:\Users\Umair\Desktop\Bloodify\Bloodfy\frontend2
python -m http.server 5500
```

**What to tell your teacher:**
> "This serves our frontend — the HTML, CSS, and JavaScript user interface that communicates with the backend API."

✅ You should see: `Serving HTTP on :: port 5500`

**⚠️ Keep this terminal open too. Don't close it.**

---

## 🌐 STEP 3: Show the API (Backend Demo)

Open your browser and go to:

```
http://127.0.0.1:8000/api/
```

**What to tell your teacher:**
> "This is our REST API root. It shows all available endpoints — authentication, donors, recipients, blood requests, blood stock management, AI engine, notifications, and chatbot."

You'll see a JSON response like:
```json
{
  "success": true,
  "message": "Welcome to Bloodfy API",
  "version": "1.0.0",
  "endpoints": {
    "auth": "/api/auth/",
    "users": "/api/users/",
    "donors": "/api/donors/",
    "recipients": "/api/recipients/",
    "blood_requests": "/api/blood-requests/",
    "blood_stock": "/api/blood-stock/",
    "ai_engine": "/api/ai/",
    "notifications": "/api/notifications/",
    "chatbot": "/api/chatbot/"
  }
}
```

---

## 🖥️ STEP 4: Show the Frontend (User Interface)

### 4a. Login Page
Open your browser and go to:
```
http://127.0.0.1:5500/auth/user-login.html
```

**What to tell your teacher:**
> "This is our user login page. Users can register as donors or recipients and log in with JWT authentication."

Login with:
- **Email:** `umairmuddassir1@hmail.com`
- **Password:** *(the password you set during createsuperuser)*

### 4b. User Dashboard
After login, or go directly to:
```
http://127.0.0.1:5500/user/pages/dashboard.html
```

**What to tell your teacher:**
> "This is the patient/user dashboard. They can see their blood requests, find available donors, and monitor request status."

### 4c. Admin Dashboard
```
http://127.0.0.1:5500/admin/pages/dashboard.html
```

**What to tell your teacher:**
> "The admin dashboard gives a complete overview — total donors, pending requests, blood stock levels, and AI analytics."

### 4d. Other Pages to Show

| Page | URL | What It Shows |
|------|-----|---------------|
| **Emergency Requests** | `http://127.0.0.1:5500/user/pages/emergency.html` | Emergency blood request form |
| **Available Donors** | `http://127.0.0.1:5500/user/pages/available-donors.html` | Search/filter donors |
| **Blood Requests** | `http://127.0.0.1:5500/user/pages/requests.html` | Create & track blood requests |
| **Chatbot** | `http://127.0.0.1:5500/user/pages/chatbot.html` | AI-powered blood bank assistant |
| **Donor Registration** | `http://127.0.0.1:5500/user/pages/donor-registration.html` | Donor signup form |
| **Notifications** | `http://127.0.0.1:5500/user/pages/notifications.html` | Real-time notifications |
| **Settings** | `http://127.0.0.1:5500/user/pages/settings.html` | Profile settings |
| **Admin: Blood Stock** | `http://127.0.0.1:5500/admin/pages/bloodstock.html` | Manage blood inventory |
| **Admin: Donors** | `http://127.0.0.1:5500/admin/pages/donor.html` | Manage all donors |
| **Admin: Patients** | `http://127.0.0.1:5500/admin/pages/patient.html` | Manage all patients |
| **Admin: Emergency** | `http://127.0.0.1:5500/admin/pages/emergency.html` | Emergency management |
| **Admin: Analytics** | `http://127.0.0.1:5500/admin/pages/analytics.html` | AI model metrics |
| **Admin: Staff** | `http://127.0.0.1:5500/admin/pages/staff.html` | Staff management |
| **Django Admin** | `http://127.0.0.1:8000/admin/` | Django built-in admin panel |

---

## 🤖 STEP 5: Demo the AI Triage System (Key Feature!)

This is the **most impressive** part. Open a **third PowerShell** (Terminal 3) and run:

```powershell
cd C:\Users\Umair\Desktop\Bloodify\Bloodfy\bloodfy
.\venv\Scripts\Activate.ps1
python test_triage.py
```

**What to tell your teacher:**
> "This is our AI-powered Medical Urgency Triage system. It automatically classifies blood requests into EMERGENCY, URGENT, or NORMAL based on the patient's diagnosis, age, blood group, units needed, and current stock levels."

> "It uses a rule-based engine with an optional LLM upgrade path — Google Gemini or OpenAI. If the AI service is down, it falls back gracefully to deterministic rules, ensuring the system never fails."

You'll see output like:
```
============================================================
  EMERGENCY Classification
============================================================
  ✓ PASS  Hemorrhage + units > stock → EMERGENCY
  ✓ PASS  Zero stock → EMERGENCY regardless of condition
  ✓ PASS  PPH keyword → EMERGENCY
  ✓ PASS  Trauma + elderly (>75) → EMERGENCY
  ✓ PASS  GI bleed + pediatric (<5) → EMERGENCY

============================================================
  URGENT Classification
============================================================
  ✓ PASS  Thalassemia regular transfusion → URGENT
  ✓ PASS  Severe anaemia Hb<7 → URGENT
  ✓ PASS  Dengue + transfusion needed → URGENT

============================================================
  NORMAL Classification
============================================================
  ✓ PASS  Routine pre-op with ample stock → NORMAL
  ✓ PASS  Prophylactic scheduled → NORMAL

============================================================
  Results:  27 passed  0 failed
============================================================
```

**Key talking points for the AI system:**
- 🔴 **EMERGENCY**: Hemorrhage, trauma, zero stock, DIC, blast injuries → auto-escalates
- 🟡 **URGENT**: Thalassemia, surgery, severe anemia, dengue, leukemia
- 🟢 **NORMAL**: Routine pre-op, chronic stable conditions, prophylactic
- Uses **word-boundary regex matching** so "stable" doesn't false-match "stab"
- Every assessment is **audit-logged** in the TriageLog table
- Admins can **override** AI decisions with documented reasons
- Designed for the **Pakistan healthcare context**

---

## 🔒 STEP 6: Show Django Admin Panel

Go to:
```
http://127.0.0.1:8000/admin/
```

Login with:
- **Email:** `umairmuddassir1@hmail.com`
- **Password:** *(your superuser password)*

**What to tell your teacher:**
> "This is the Django admin panel where administrators can directly manage all database records — users, donors, blood requests, triage logs, AI rankings, and blood stock."

Show these models inside the admin:
- **AI Engine** → Triage Logs, AI Rankings, AI Model Metrics
- **Users** → All registered users
- **Donors** → Donor profiles
- **Blood Stock** → Blood inventory

---

## 📊 STEP 7: Explain the Architecture (Talking Points)

**What to tell your teacher:**

> "Bloodify has a modular architecture with 8 Django apps:"

| App | Purpose |
|-----|---------|
| `users` | Custom user model with JWT authentication (donor/recipient/admin roles) |
| `donors` | Donor profiles, eligibility tracking, donation history |
| `recipients` | Recipient/patient profiles |
| `requests_management` | Blood request lifecycle (create → approve → assign → complete) |
| `blood_stock` | Blood inventory management with statistics |
| `ai_engine` | AI donor ranking, medical urgency triage, LLM integration |
| `notifications` | Real-time notification system |
| `chatbot` | AI-powered conversational assistant |

> "The frontend is vanilla HTML/CSS/JavaScript communicating with the Django REST Framework API via JWT-authenticated HTTP requests."

> "The AI Engine supports dual-path processing — LLM-based assessment (Google Gemini or OpenAI) with automatic rule-based fallback if the AI service is unavailable."

**Tech Stack:**
- **Backend:** Python, Django 4.2, Django REST Framework
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Auth:** JWT (JSON Web Tokens) via SimpleJWT
- **AI:** Rule-based engine + LLM integration (Gemini/OpenAI)

---

## 🛑 STEP 8: Stop Everything (After Presentation)

- **Terminal 1** (backend): Press `Ctrl + C`
- **Terminal 2** (frontend): Press `Ctrl + C`  
- **Terminal 3** (tests): Already finished

---

## 💡 TROUBLESHOOTING — Quick Fixes

| Problem | Solution |
|---------|----------|
| Server not starting | Run `python manage.py migrate` first |
| "Port already in use" | Use `python manage.py runserver 8001` |
| Frontend not loading | Make sure Terminal 2 is running |
| CORS errors in browser | Port 5500 is pre-whitelisted — it should work |
| Login not working | Create new user: `python manage.py createsuperuser` |
| Tests failing | Run `python test_triage.py` to check |
| "Module not found" error | Make sure you activated venv: `.\venv\Scripts\Activate.ps1` |

---

## 📁 Project Structure

```
Bloodify/
└── Bloodfy/
    ├── bloodfy/                    ← Django Backend
    │   ├── manage.py               ← Django entry point
    │   ├── bloodfy_project/        ← Settings & root URL config
    │   ├── users/                  ← Authentication & user management
    │   ├── donors/                 ← Donor management
    │   ├── recipients/             ← Recipient management
    │   ├── requests_management/    ← Blood request workflow
    │   ├── blood_stock/            ← Blood inventory
    │   ├── ai_engine/              ← 🤖 AI Triage + Donor Ranking
    │   │   ├── triage_service.py   ← Medical urgency classification
    │   │   ├── llm_provider.py     ← Gemini/OpenAI integration
    │   │   ├── ranking_engine.py   ← AI donor matching algorithm
    │   │   ├── models.py           ← TriageLog, AIRanking, Metrics
    │   │   ├── views.py            ← REST API endpoints
    │   │   └── serializers.py      ← Request/response validation
    │   ├── notifications/          ← Notification system
    │   ├── chatbot/                ← AI chatbot
    │   ├── utils/                  ← Shared utilities
    │   ├── test_triage.py          ← AI triage unit tests (27 tests)
    │   ├── test_api.py             ← API integration tests
    │   ├── venv/                   ← Python virtual environment
    │   └── db.sqlite3              ← SQLite database
    │
    └── frontend2/                  ← Frontend (HTML/CSS/JS)
        ├── auth/                   ← Login pages (user + admin)
        ├── user/pages/             ← User-facing pages (8 pages)
        ├── admin/pages/            ← Admin pages (12 pages)
        ├── config/api-config.js    ← API client configuration
        ├── css/                    ← Stylesheets
        └── js/                     ← JavaScript logic
```

---

## ⏱️ Suggested Demo Order (10–15 minutes)

| Step | Time | What to Show |
|------|------|-------------|
| 1 | 1 min | Start backend + frontend (Terminals 1 & 2) |
| 2 | 1 min | Show API root at `/api/` |
| 3 | 2 min | Walk through login page + user dashboard |
| 4 | 2 min | Show admin dashboard + blood stock |
| 5 | 3 min | **Run AI triage tests** ← Most impressive part |
| 6 | 2 min | Show Django admin panel & database |
| 7 | 2 min | Explain architecture + tech stack |
| 8 | 1 min | Q&A |

---

**Good luck with your presentation, Umair! 🎓**
