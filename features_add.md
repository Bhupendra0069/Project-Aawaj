You are continuing development of an EXISTING Django-based AI civic complaint platform called AAWAJ (आवाज).

IMPORTANT:

* DO NOT rebuild the project from scratch.
* DO NOT replace existing frontend pages.
* EXTEND the current architecture and integrate new intelligent analytics features cleanly into the existing codebase.

Existing stack:

* Django backend
* Django templates frontend
* SQLite database
* Tailwind CDN UI
* Leaflet maps
* REST APIs
* OpenAI integration
* Complaint moderation system
* Government dashboard
* Public dashboard
* Heatmap map system
* AI complaint classification

Your task is to UPGRADE the platform into a SMART GOVERNANCE ANALYTICS SYSTEM.

==================================================
PHASE 2 OBJECTIVE
=================

Implement advanced:

* complaint intelligence,
* hotspot detection,
* clustering algorithms,
* population-normalized prioritization,
* geospatial analytics,
* smart ranking systems,
* duplicate complaint intelligence,
* and government decision-support features.

The platform must intelligently determine:
"Which area should government prioritize first?"

NOT based only on raw complaint count.

==================================================
EXISTING SYSTEM CONTEXT
=======================

Current complaint model already includes:

* location
* image
* AI classification
* priority
* status
* timestamps

Existing pages:

* public dashboard
* government dashboard
* moderation panel
* map page

You must EXTEND these pages and APIs.

==================================================
FEATURE 1 — POPULATION NORMALIZED PRIORITY ENGINE
=================================================

Problem:
Areas with higher population naturally generate more complaints.

Example:

* Maitidevi: 30 complaints, population 100
* Baneshwor: 20 complaints, population 50

Baneshwor should rank higher because complaint density is higher.

Implement a SMART PRIORITY SCORE system.

Priority formula idea:

PriorityScore =
(
ComplaintCount × SeverityWeight × UrgencyWeight × RecurringFactor × VerificationScore × RecencyFactor
)
/ PopulationDensity

Requirements:

* Normalize complaints by population
* Prevent large population bias
* Recent unresolved complaints increase score
* Verified complaints have higher weight
* Critical infrastructure issues rank higher
* Duplicate complaints strengthen hotspot importance

Add configurable weights stored in database or settings model.

==================================================
FEATURE 2 — GEOSPATIAL HOTSPOT DETECTION
========================================

Implement clustering algorithms for geographic complaint hotspot analysis.

Preferred algorithm:

* DBSCAN

Requirements:

* Cluster complaints using latitude + longitude
* Detect dense complaint regions automatically
* Ignore isolated noise complaints
* Generate hotspot clusters dynamically
* Assign hotspot severity score
* Rank hotspots by urgency

Cluster outputs should include:

* cluster_id
* complaint_count
* severity_average
* density_score
* center_latitude
* center_longitude
* hotspot_priority_score

==================================================
FEATURE 3 — REAL-TIME HEATMAP ANALYTICS
=======================================

Upgrade existing map.html and dashboard map systems.

Add:

* real-time heatmaps
* hotspot circles
* severity-based coloring
* animated hotspot pulsing
* complaint density visualization
* ward-wise issue aggregation
* date range filters
* category filters

Use:

* Leaflet heatmap plugins
* GeoJSON support
* optimized API responses

==================================================
FEATURE 4 — DUPLICATE COMPLAINT INTELLIGENCE
============================================

Detect multiple complaints about the same issue.

Use:

* text similarity
* GPS proximity
* time proximity
* AI semantic similarity

Example:
20 pothole complaints within 100 meters
→ merge into infrastructure hotspot event.

Requirements:

* avoid clutter
* improve priority scoring
* increase hotspot confidence

==================================================
FEATURE 5 — GOVERNMENT DECISION INTELLIGENCE DASHBOARD
======================================================

Upgrade government dashboard with:

1. HOTSPOT ANALYTICS PANEL

* highest priority areas
* complaint density rankings
* unresolved hotspot zones
* category-based regional breakdowns

2. PERFORMANCE ANALYTICS

* avg response time
* avg resolution time
* department efficiency
* unresolved complaint trends

3. TEMPORAL ANALYTICS

* complaints per day/week/month
* trend forecasting
* recurring issue regions

4. SEVERITY ANALYTICS

* critical issue concentration
* infrastructure failure risk map

Use charts and visual analytics.

==================================================
FEATURE 6 — ADVANCED DATABASE & GEO SUPPORT
===========================================

Upgrade models for geospatial analytics.

Add models if needed:

* RegionPopulation
* ComplaintCluster
* HotspotAnalytics
* ComplaintSimilarity

Store:

* ward population
* area population density
* cluster metadata
* hotspot historical data

Optimize:

* geospatial queries
* clustering computations
* indexing

==================================================
FEATURE 7 — AI-READY MODULAR ARCHITECTURE
=========================================

Refactor backend architecture for future AI integrations:

Future-ready modules:

* road damage image detection
* AI corruption detection
* predictive infrastructure failure
* anomaly detection
* traffic issue prediction
* citizen sentiment analysis

Create modular services:

* clustering_service.py
* hotspot_service.py
* analytics_service.py
* priority_engine.py
* geo_service.py

==================================================
FEATURE 8 — PUBLIC TRANSPARENCY FEATURES
========================================

Add:

* top unresolved areas
* public hotspot map
* resolution progress tracker
* transparency metrics
* ward-level complaint statistics

==================================================
FEATURE 9 — SMART SPAM / FAKE DETECTION
=======================================

Implement:

* repeated spam detection
* suspicious complaint frequency detection
* fake image detection hooks
* anomaly scoring
* complaint trust score

==================================================
FEATURE 10 — API EXPANSION
==========================

Create new APIs:

GET /api/hotspots/
GET /api/analytics/priority-zones/
GET /api/analytics/heatmap/
GET /api/analytics/trends/
GET /api/analytics/ward-stats/
GET /api/analytics/severity/
GET /api/clusters/
GET /api/government/performance/

Responses must be optimized for frontend visualization.

==================================================
TECHNICAL REQUIREMENTS
======================

* Maintain clean Django architecture
* Keep compatibility with existing system
* Modular scalable services
* Production-ready code
* Well-commented code
* Efficient clustering calculations
* Optimized geospatial queries
* Async-ready architecture if possible

==================================================
OUTPUT REQUIREMENTS
===================

Generate:

1. Updated models
2. Migration changes
3. New services
4. Clustering implementation
5. DBSCAN integration
6. Updated APIs
7. Dashboard frontend upgrades
8. Heatmap frontend logic
9. Government analytics UI
10. Example datasets
11. Population-normalized ranking logic
12. Production-ready architecture

DO NOT overwrite existing functionality.
Only extend and improve the current AAWAJ platform intelligently.
