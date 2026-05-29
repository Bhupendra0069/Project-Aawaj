# AAWAJ (आवाज) — Project Report

## Smart Civic Complaint Reporting System for Kathmandu Valley, Nepal

---

## 1. Introduction

**AAWAJ** (meaning "Voice" in Nepali) is an AI-powered civic complaint platform designed to empower citizens of the Kathmandu Valley to report real-world public issues such as broken roads, garbage problems, water leakage, electricity failures, health hazards, and more. The platform leverages artificial intelligence for automated complaint analysis, classification, and report generation — bridging the gap between citizens and government authorities.

### 1.1 Problem Statement

Citizens in the Kathmandu Valley face difficulties reporting civic issues to the relevant government departments. Traditional complaint mechanisms are slow, lack transparency, and do not provide feedback to citizens. There is no centralized, intelligent system to prioritize and route complaints to the appropriate departments.

### 1.2 Objectives

- Give citizens a simple digital voice to report civic problems
- Automate complaint classification and report generation using AI
- Provide moderation to filter fake/irrelevant complaints
- Deliver structured, actionable reports to government dashboards
- Enable geographic hotspot detection and smart prioritization
- Increase transparency through public dashboards and complaint tracking

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | Django 5.x | Core web framework, ORM, authentication |
| **REST API** | Django REST Framework 3.15+ | Serialization, API endpoints |
| **Database** | SQLite 3 | Primary data storage (development) |
| **Frontend** | HTML5 / CSS3 / JavaScript | UI rendering, interactivity |
| **CSS Framework** | Vanilla CSS (custom design system) | Styling and layout |
| **AI - Image Analysis** | Google Gemini 2.0 Flash API | Image-based complaint description generation |
| **AI - Classification** | Custom keyword-based NLP | Complaint category and severity detection |
| **AI - Clustering** | scikit-learn (DBSCAN) | Geospatial hotspot detection |
| **Mapping** | Leaflet.js | Interactive maps, heatmaps, markers |
| **CORS** | django-cors-headers | Cross-origin request handling |
| **Image Processing** | Pillow 10+ | Image upload handling |
| **Math/Science** | NumPy 1.26+ | Numerical computations for analytics |
| **Environment** | python-dotenv | Environment variable management |

### 2.1 Why These Technologies?

- **Django**: Chosen for its batteries-included philosophy — built-in ORM, admin panel, authentication, and template engine reduce development time significantly.
- **SQLite**: Used during development for simplicity; the project is designed to migrate to PostgreSQL for production.
- **Google Gemini API**: Selected for AI image analysis due to its multimodal capabilities, allowing the system to analyze uploaded images and generate civic issue descriptions automatically.
- **DBSCAN Algorithm**: Chosen for geospatial clustering because it doesn't require a predefined number of clusters and handles noise effectively — ideal for detecting organic complaint hotspots.
- **Leaflet.js**: Open-source, lightweight mapping library perfect for heatmap visualization and complaint pin overlays.

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────┐
│                    FRONTEND                       │
│         HTML / CSS / JavaScript                   │
│   Public Portal │ Admin Panel │ Gov Dashboard     │
└─────────────────────┬────────────────────────────┘
                      │ HTTP / REST API
                      ▼
┌──────────────────────────────────────────────────┐
│                 DJANGO BACKEND                    │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐│
│  │ Auth/Roles  │  │ Complaints   │  │ Admin    ││
│  │ Login/RBAC  │  │ CRUD/Track   │  │ Moderate ││
│  └─────────────┘  └──────────────┘  └──────────┘│
│                                                   │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Public API  │  │ Government Resolution    │  │
│  │ Dashboard   │  │ Actions & Reports        │  │
│  └─────────────┘  └──────────────────────────┘  │
└─────────────────────┬────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────┐
│                   AI LAYER                        │
│                                                   │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Gemini Vision    │  │ NLP Classification   │  │
│  │ Image Analysis   │  │ Category Detection   │  │
│  └──────────────────┘  └──────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Severity Scorer  │  │ DBSCAN Clustering    │  │
│  │ Priority Engine  │  │ Hotspot Detection    │  │
│  └──────────────────┘  └──────────────────────┘  │
└─────────────────────┬────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────┐
│                DATABASE LAYER                     │
│                                                   │
│  SQLite (dev) → PostgreSQL (production)           │
│  Tables: Users, Complaints, Images, Audio,        │
│  ModerationLogs, GovernmentActions, Clusters,      │
│  RegionPopulation, Similarities, Analytics         │
│                                                   │
│  Media Storage: /media/complaints/images/          │
│                 /media/complaints/audio/            │
└──────────────────────────────────────────────────┘
```

---

## 4. Database Design

### 4.1 Database Engine

The project uses **SQLite 3** as the database engine during development. SQLite was chosen because:
- Zero configuration — no separate database server needed
- Single file storage (`db.sqlite3`) — easy to manage and backup
- Sufficient for development and moderate traffic
- Django ORM makes migration to PostgreSQL seamless for production

### 4.2 Entity Relationship Overview

The database consists of **10 models** organized into two phases:

#### Phase 1 — Core Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` (Django built-in) | Authentication & roles | username, password, groups |
| `Complaint` | Core complaint record | complaint_code, description, location, GPS coords, status, category, priority, AI scores, trust_score, ward |
| `ComplaintImage` | Images attached to complaints | complaint (FK), image file, uploaded_at |
| `ComplaintAudio` | Audio recordings for complaints | complaint (FK), audio file, transcription |
| `ModerationLog` | Admin moderation action log | complaint (FK), moderator (FK), action, notes |
| `GovernmentAction` | Government resolution records | complaint (FK), action_type, officer_name, department |
| `ContactMessage` | Contact form submissions | name, email, subject, message |

#### Phase 2 — Smart Governance Analytics Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `RegionPopulation` | Ward population data for normalization | ward_name, ward_number, municipality, population, area_km2, population_density |
| `ComplaintCluster` | DBSCAN-generated hotspot zones | cluster_id, complaint_count, severity_average, center coords, radius, hotspot_priority_score, dominant_category |
| `HotspotAnalytics` | Historical hotspot snapshots | cluster (FK), ward_name, complaint_count, priority_score, snapshot_date |
| `ComplaintSimilarity` | Duplicate complaint detection pairs | complaint_a (FK), complaint_b (FK), similarity_score, method, gps_distance, is_duplicate |
| `AnalyticsConfig` | Singleton configuration for analytics weights | severity_weight, urgency_weight, DBSCAN params, duplicate thresholds, spam limits |

### 4.3 Complaint Status Lifecycle

```
pending_ai → pending_review → published → resolved
                    ↓
                 rejected
```

- **pending_ai**: Just submitted, awaiting AI analysis
- **pending_review**: AI confidence is medium; needs human moderator review
- **published**: Verified and visible on public dashboard + government dashboard
- **rejected**: AI or moderator determined it's fake/irrelevant
- **resolved**: Government has taken action and marked it resolved

### 4.4 Complaint Categories

Roads & Potholes, Garbage & Waste, Water & Drainage, Electricity & Power, Health Hazards, Education & Schools, Corruption, Public Infrastructure, Other.

---

## 5. User Roles & Access Control

The system implements **Role-Based Access Control (RBAC)** using Django's built-in Groups:

| Role | Access | Description |
|------|--------|-------------|
| **Citizen** (Anonymous) | Public pages, submit complaints, track status | No login required |
| **Moderator** | Moderation panel, approve/reject complaints | Reviews AI-flagged complaints |
| **Government** | Government dashboard, analytics, take actions, export reports | Resolution workflow |
| **Admin** | Django admin panel, full system access | System management |

---

## 6. Core Features & Implementation

### 6.1 Complaint Submission Flow

1. Citizen opens the **Report** page
2. Uploads complaint **image** (mandatory)
3. System detects **GPS location** automatically (mobile) or user searches location
4. Citizen provides **text description** or **audio recording** (one mandatory)
5. Optional: Citizen clicks "AI Analyze" to auto-generate description from image using Gemini API
6. System submits complaint to backend

### 6.2 AI Processing Pipeline

When a complaint is submitted, the `ai_service.process_complaint()` function runs:

1. **Category Classification** — Keyword-based NLP matches description text against category keyword dictionaries (English + Nepali terms)
2. **Severity Analysis** — Scans for high-severity keywords (danger, emergency, collapse, etc.) and scores 1-10
3. **Image Verification** — Hash-based deterministic analysis to check image genuineness
4. **Confidence Scoring** — Combined score: 40% text confidence + 60% image confidence
5. **Routing Decision**:
   - Confidence ≥ 0.70 + genuine image → **Auto-publish** (high verdict)
   - Confidence 0.45–0.70 → **Send to moderator** (medium verdict)
   - Confidence < 0.45 → **Auto-reject** (low verdict)
6. **Report Generation** — Structured government report with category, severity, recommended department

### 6.3 Gemini AI Image Analysis

The platform integrates **Google Gemini 2.0 Flash** for real-time image analysis:
- User uploads an image on the report page
- Image is sent to Gemini API with a civic-issue-focused prompt
- Gemini returns a 2-3 sentence description identifying the civic problem
- User can edit or clear the AI-generated text before submitting

### 6.4 Moderation System

- Moderators log in and access the **Moderation Panel**
- They see complaints with medium AI confidence requiring human review
- Each complaint shows: images, description, AI verdict, location, severity
- Moderators can **Approve** (publishes to dashboards) or **Reject** with notes
- All actions are logged in `ModerationLog`

### 6.5 Government Dashboard

- Government users see all published/resolved complaints
- Filter by status, category, priority, search text
- View detailed case information with AI-generated reports
- Take actions: Acknowledge, In Progress, Resolved, Referred
- Download individual reports as text files
- Export all complaints as CSV

### 6.6 Public Dashboard

- Displays all published complaints to the public
- Filter by category, search by text/location/code
- Shows statistics: total, published, resolved, pending
- Category breakdown charts and daily trend data

### 6.7 Complaint Tracking

- Citizens receive a unique **complaint code** (e.g., `AAW-A3F2B1`)
- They can track status on the **Track** page using this code
- Shows current status, AI analysis results, government actions taken

### 6.8 Interactive Map

- Leaflet.js map centered on Kathmandu Valley
- Complaint pins with category-based colors
- Heatmap layer showing complaint density
- Cluster overlays showing DBSCAN-detected hotspots
- Click markers for complaint details

---

## 7. Phase 2 — Smart Governance Analytics

### 7.1 Service Architecture

The Phase 2 analytics are implemented as **modular service files**:

| Service | File | Functionality |
|---------|------|--------------|
| **Clustering** | `clustering_service.py` | DBSCAN algorithm for geographic hotspot detection |
| **Hotspot** | `hotspot_service.py` | Hotspot scoring and ranking |
| **Priority Engine** | `priority_engine.py` | Population-normalized priority scoring |
| **Analytics** | `analytics_service.py` | Temporal trends, severity distribution, performance metrics |
| **Geo Service** | `geo_service.py` | Ward detection from GPS, ward statistics |
| **Duplicate** | `duplicate_service.py` | Duplicate complaint detection via GPS + text similarity |
| **Spam** | `spam_service.py` | Trust scoring and spam detection |

### 7.2 DBSCAN Clustering

- Uses scikit-learn's DBSCAN algorithm
- Clusters complaints by latitude/longitude
- Configurable epsilon (default: 300m radius) and min_samples (default: 3)
- Outputs: cluster centers, radius, complaint count, severity averages
- Noise complaints (isolated) are labeled cluster_id = -1

### 7.3 Population-Normalized Priority Engine

**Formula:**
```
PriorityScore = (ComplaintCount × SeverityWeight × UrgencyWeight 
                 × RecurringFactor × VerificationScore × RecencyFactor)
                / PopulationDensity
```

This ensures areas with higher population don't automatically dominate the priority list. A ward with fewer people but proportionally more complaints ranks higher.

### 7.4 Duplicate Detection

Combines three methods:
- **GPS Proximity** — Complaints within configurable radius (default: 100m)
- **Text Similarity** — Cosine similarity on complaint descriptions
- **Combined Score** — Weighted combination of both

### 7.5 Government Analytics Dashboard

Advanced analytics page with:
- Hotspot rankings with priority scores
- Ward-level complaint statistics
- Temporal trend charts (daily/weekly/monthly)
- Severity distribution analysis
- Duplicate complaint groups
- Performance metrics (response time, resolution rate)
- One-click analytics refresh

---

## 8. API Endpoints

### 8.1 Public APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/complaints/submit/` | Submit a new complaint |
| GET | `/api/complaints/<code>/status/` | Track complaint by code |
| GET | `/api/complaints/public/` | Get published complaints |
| GET | `/api/dashboard/stats/` | Dashboard statistics |
| GET | `/api/map/data/` | Map markers and heatmap data |
| POST | `/api/contact/submit/` | Submit contact form |
| POST | `/api/ai/analyze-image/` | Gemini image analysis |

### 8.2 Moderation APIs (Requires moderator role)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/moderation/queue/` | Pending complaints queue |
| POST | `/api/moderation/<id>/action/` | Approve/reject complaint |
| GET | `/api/moderation/<id>/detail/` | Full complaint details |

### 8.3 Government APIs (Requires government role)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/government/complaints/` | Government complaint list |
| GET | `/api/government/<id>/detail/` | Complaint details |
| POST | `/api/government/<id>/action/` | Take action on complaint |
| GET | `/api/government/export/csv/` | Export complaints as CSV |
| GET | `/api/government/<id>/report/download/` | Download AI report |
| GET | `/api/government/performance/` | Performance metrics |

### 8.4 Analytics APIs (Phase 2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/hotspots/` | Ranked hotspot clusters |
| GET | `/api/analytics/priority-zones/` | Population-normalized zones |
| GET | `/api/analytics/heatmap/` | Enhanced heatmap data |
| GET | `/api/analytics/trends/` | Temporal trend data |
| GET | `/api/analytics/ward-stats/` | Per-ward statistics |
| GET | `/api/analytics/severity/` | Severity distribution |
| GET | `/api/analytics/duplicates/` | Duplicate complaint groups |
| GET | `/api/clusters/` | Raw cluster GeoJSON |
| POST | `/api/analytics/refresh/` | Re-compute all analytics |

---

## 9. Frontend Pages

| Page | Template | URL | Access |
|------|----------|-----|--------|
| Home / Landing | `home.html` | `/` | Public |
| Report Complaint | `report.html` | `/report/` | Public |
| Track Complaint | `track.html` | `/track/` | Public |
| Public Dashboard | `public_dashboard.html` | `/dashboard/` | Public |
| Interactive Map | `map.html` | `/map/` | Public |
| About | `about.html` | `/about/` | Public |
| Contact | `contact.html` | `/contact/` | Public |
| Login | `login.html` | `/login/` | Public |
| Moderation Panel | `moderation.html` | `/moderation/` | Moderator |
| Government Dashboard | `government_dashboard.html` | `/government/` | Government |
| Case Detail | `government_case_detail.html` | `/government/case/<id>/` | Government |
| Analytics Dashboard | `government_analytics.html` | `/government/analytics/` | Government |

---

## 10. Project File Structure

```
Project AAWAJ/
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── db.sqlite3                   # SQLite database file
├── .env                         # Environment variables (API keys)
├── .gitignore                   # Git ignore rules
├── README.md                    # Project readme
│
├── aawaj/                       # Django project config
│   ├── settings.py              # Project settings
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point
│
├── complaints/                  # Main Django app
│   ├── models.py                # Database models (10 models)
│   ├── views.py                 # Views & API endpoints (874 lines)
│   ├── urls.py                  # App URL patterns
│   ├── serializers.py           # DRF serializers
│   ├── admin.py                 # Admin panel configuration
│   ├── ai_service.py            # AI processing pipeline
│   ├── apps.py                  # App configuration
│   │
│   ├── services/                # Phase 2 analytics services
│   │   ├── analytics_service.py # Temporal trends, metrics
│   │   ├── clustering_service.py# DBSCAN clustering
│   │   ├── duplicate_service.py # Duplicate detection
│   │   ├── geo_service.py       # Ward detection, geo stats
│   │   ├── hotspot_service.py   # Hotspot scoring
│   │   ├── priority_engine.py   # Population-normalized priority
│   │   └── spam_service.py      # Trust/spam scoring
│   │
│   ├── migrations/              # Database migrations
│   └── management/              # Custom management commands
│
├── templates/                   # Django HTML templates (13 pages)
├── static/                      # CSS, JS, images
└── media/                       # User-uploaded files
    └── complaints/
        ├── images/              # Complaint photos
        └── audio/               # Audio recordings
```

---

## 11. Development Progress

### Phase 1 — Core Platform ✅ Completed

- [x] Django project setup with proper settings
- [x] Database models for complaints, images, audio, moderation, government actions
- [x] Complaint submission with image + text/audio + GPS location
- [x] AI analysis pipeline (classification, severity, routing)
- [x] Google Gemini API integration for image-based description generation
- [x] Moderation panel with approve/reject workflow
- [x] Government dashboard with action workflow
- [x] Public dashboard with filters and statistics
- [x] Complaint tracking by unique code
- [x] Interactive Leaflet.js map with heatmap
- [x] Contact form
- [x] Role-based access control (moderator, government)
- [x] REST API with DRF serializers
- [x] CSV export for government
- [x] AI report generation and download
- [x] Django admin panel configuration
- [x] Responsive frontend design

### Phase 2 — Smart Governance Analytics ✅ Completed

- [x] DBSCAN geospatial clustering for hotspot detection
- [x] Population-normalized priority scoring engine
- [x] Ward auto-detection from GPS coordinates
- [x] Duplicate complaint detection (GPS + text similarity)
- [x] Spam/trust scoring system
- [x] Government analytics dashboard with charts
- [x] Temporal trend analysis (daily/weekly/monthly)
- [x] Severity distribution analytics
- [x] Performance metrics (response time, resolution rate)
- [x] Analytics refresh endpoint
- [x] Modular service architecture (7 service files)
- [x] RegionPopulation, ComplaintCluster, HotspotAnalytics, ComplaintSimilarity models
- [x] Configurable analytics weights (AnalyticsConfig singleton)

### Phase 3 — UI Modernization ✅ Completed

- [x] Light-themed premium design
- [x] Blue-lavender accent color palette
- [x] Pill-shaped button design system
- [x] Hero section with smart-city image carousel

---

## 12. How to Run the Project

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Setup Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd "Project AAWAJ"

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
# Create .env file with:
# SECRET_KEY=your-secret-key
# DEBUG=True
# GEMINI_API_KEY=your-gemini-api-key

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Create user groups (in Django admin or shell)
# Groups needed: 'moderator', 'government'

# 8. Run development server
python manage.py runserver
```

### Access Points
- **Website**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/

---

## 13. Future Scope

- Nepali language support (multilingual UI)
- Mobile application (React Native / Flutter)
- SMS-based complaint submission
- WhatsApp bot integration
- Real-time push notifications
- PostgreSQL migration for production
- Cloud deployment (AWS/Render/Railway)
- Advanced AI: road damage detection from images
- Predictive infrastructure failure analysis
- Citizen sentiment analysis
- Auto department routing based on complaint category

---

## 14. Conclusion

AAWAJ demonstrates how modern web technologies combined with AI can transform civic governance. The platform successfully automates the complaint lifecycle — from citizen submission through AI analysis, moderation, and government resolution. The Phase 2 analytics layer adds data-driven intelligence with DBSCAN clustering, population-normalized prioritization, and duplicate detection, enabling government officials to make informed decisions about resource allocation.

The modular Django architecture ensures the system is maintainable and extensible, ready for future AI integrations and scale.

---

*AAWAJ — Built for Kathmandu. Powered by People. Driven by Technology.* 🇳🇵
