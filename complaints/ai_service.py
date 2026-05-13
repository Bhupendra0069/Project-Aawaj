"""
AAWAJ AI Service - Mock Implementation
Simulates AI analysis for complaint processing.
Replace with real OpenAI/Google Vision API calls when API keys are available.
"""

import random
import hashlib
from datetime import datetime


# Category keywords for mock classification
CATEGORY_KEYWORDS = {
    'roads': ['road', 'pothole', 'crack', 'pavement', 'highway', 'street', 'bridge', 'footpath', 'sadak', 'bato'],
    'garbage': ['garbage', 'waste', 'trash', 'litter', 'dump', 'rubbish', 'dirty', 'fohor', 'maila'],
    'water': ['water', 'leak', 'flood', 'drainage', 'pipe', 'sewage', 'drain', 'tap', 'pani', 'dhara'],
    'electricity': ['electric', 'power', 'wire', 'pole', 'outage', 'blackout', 'light', 'bijuli'],
    'health': ['health', 'disease', 'hospital', 'clinic', 'sanitation', 'hazard', 'smell', 'swasthya'],
    'education': ['school', 'education', 'college', 'teacher', 'student', 'classroom', 'shiksha', 'bidyalaya'],
    'corruption': ['corruption', 'bribe', 'fraud', 'scam', 'illegal', 'bhrastachar', 'ghus'],
    'infrastructure': ['building', 'park', 'temple', 'public', 'bus stop', 'footbridge', 'infrastructure'],
}

# Severity indicators
HIGH_SEVERITY_KEYWORDS = [
    'danger', 'emergency', 'urgent', 'accident', 'collapse', 'fire', 'flood',
    'death', 'injury', 'toxic', 'explosion', 'fallen', 'broken', 'severe',
    'critical', 'risk', 'hazardous', 'khatarnak', 'aapatkaalin'
]


def classify_category(text):
    """Classify complaint text into a category using keyword matching."""
    if not text:
        return 'other', 0.3

    text_lower = text.lower()
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if scores:
        best_category = max(scores, key=scores.get)
        confidence = min(0.5 + (scores[best_category] * 0.15), 0.95)
        return best_category, confidence

    return 'other', 0.3


def analyze_severity(text):
    """Analyze the severity of a complaint (1-10 scale)."""
    if not text:
        return 5, False

    text_lower = text.lower()
    severity_count = sum(1 for kw in HIGH_SEVERITY_KEYWORDS if kw in text_lower)

    if severity_count >= 3:
        return min(9 + severity_count - 3, 10), True
    elif severity_count >= 1:
        return min(6 + severity_count, 8), False
    else:
        return random.randint(3, 6), False


def analyze_image(image_file):
    """
    Mock image analysis - simulates AI checking if image is genuine.
    In production, this would use OpenAI Vision API or Google Vision.

    Returns: (is_genuine, confidence, detected_issues)
    """
    # Use file hash for deterministic results per image
    if image_file:
        try:
            content = image_file.read()
            image_file.seek(0)  # Reset file pointer
            file_hash = hashlib.md5(content).hexdigest()
            # Use hash to generate deterministic but varied results
            hash_int = int(file_hash[:8], 16)
            confidence = 0.5 + (hash_int % 50) / 100.0  # 0.50 - 0.99
            is_genuine = confidence > 0.55
        except Exception:
            confidence = 0.7
            is_genuine = True
    else:
        confidence = 0.3
        is_genuine = False

    detected_issues = []
    if is_genuine:
        possible_issues = [
            'Infrastructure damage detected',
            'Environmental hazard visible',
            'Public safety concern identified',
            'Maintenance required',
            'Civic issue confirmed in image'
        ]
        detected_issues = [random.choice(possible_issues)]

    return is_genuine, confidence, detected_issues


def generate_report(complaint_data):
    """
    Generate a structured AI report for government dashboard.
    In production, this would use OpenAI GPT to generate a professional report.
    """
    category = complaint_data.get('category', 'other')
    location = complaint_data.get('location_text', 'Unknown Location')
    description = complaint_data.get('description', 'No description provided')
    severity = complaint_data.get('ai_severity_score', 5)
    priority = complaint_data.get('priority', 'medium')

    category_labels = {
        'roads': 'Roads & Transportation',
        'garbage': 'Waste Management',
        'water': 'Water Supply & Drainage',
        'electricity': 'Electricity & Power Supply',
        'health': 'Public Health',
        'education': 'Education Infrastructure',
        'corruption': 'Governance & Transparency',
        'infrastructure': 'Public Infrastructure',
        'other': 'General Civic Issue',
    }

    dept_map = {
        'roads': 'Department of Roads, Kathmandu Metropolitan City',
        'garbage': 'Solid Waste Management Division, KMC',
        'water': 'Nepal Water Supply Corporation (NWSC)',
        'electricity': 'Nepal Electricity Authority (NEA)',
        'health': 'Department of Health Services',
        'education': 'District Education Office, Kathmandu',
        'corruption': 'Commission for Investigation of Abuse of Authority (CIAA)',
        'infrastructure': 'Department of Urban Development',
        'other': 'Kathmandu Metropolitan City Office',
    }

    report = f"""━━━ AAWAJ COMPLAINT REPORT ━━━

📋 CATEGORY: {category_labels.get(category, 'General Issue')}
📍 LOCATION: {location}
⚠️ SEVERITY: {severity}/10
🔴 PRIORITY: {priority.upper()}

📝 CITIZEN REPORT:
{description}

🏛️ RECOMMENDED DEPARTMENT:
{dept_map.get(category, 'Kathmandu Metropolitan City Office')}

📊 AI ANALYSIS SUMMARY:
This complaint has been automatically classified as a {category_labels.get(category, 'general').lower()} issue.
The AI system has assessed the severity as {severity}/10 based on the provided evidence.
{'⚡ URGENT: This issue requires immediate attention.' if severity >= 8 else 'Standard processing timeline recommended.'}

Generated by AAWAJ AI System | {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return report


def process_complaint(complaint):
    """
    Main AI processing pipeline for a complaint.
    Analyzes image + text, classifies, scores, and decides routing.

    Returns dict with all AI analysis results.
    """
    description = complaint.description or ''

    # 1. Classify category
    category, text_confidence = classify_category(description)

    # 2. Analyze severity
    severity, is_urgent = analyze_severity(description)

    # 3. Analyze image (if available)
    image_genuine = True
    image_confidence = 0.5
    images = complaint.images.all()
    if images.exists():
        first_image = images.first()
        try:
            image_genuine, image_confidence, _ = analyze_image(first_image.image)
        except Exception:
            image_confidence = 0.6
            image_genuine = True

    # 4. Calculate overall confidence
    overall_confidence = (text_confidence * 0.4 + image_confidence * 0.6)

    # 5. Determine AI verdict and routing
    if overall_confidence >= 0.7 and image_genuine:
        verdict = 'high'
        status = 'published'  # Auto-publish to public + government
        priority = 'high' if severity >= 7 else 'medium'
    elif overall_confidence >= 0.45:
        verdict = 'medium'
        status = 'pending_review'  # Send to moderator
        priority = 'medium'
    else:
        verdict = 'low'
        status = 'rejected'  # Auto-reject
        priority = 'low'

    if is_urgent:
        priority = 'critical'

    if severity >= 8:
        priority = 'critical' if priority != 'critical' else priority

    # 6. Generate government report
    report_data = {
        'category': category,
        'location_text': complaint.location_text,
        'description': description,
        'ai_severity_score': severity,
        'priority': priority,
    }
    ai_report = generate_report(report_data)

    return {
        'category': category,
        'ai_verdict': verdict,
        'ai_confidence_score': round(overall_confidence, 2),
        'ai_is_fake': not image_genuine,
        'ai_urgency': is_urgent,
        'ai_severity_score': severity,
        'ai_category_detected': category,
        'priority': priority,
        'status': status,
        'ai_generated_report': ai_report,
    }


def transcribe_audio(audio_file):
    """
    Mock audio transcription.
    In production, this would use OpenAI Whisper API.
    """
    mock_transcriptions = [
        "There is a large pothole on the main road near Ratnapark. It has been there for weeks and is causing accidents.",
        "The garbage has not been collected in our area for the past 5 days. The smell is unbearable and it is a health hazard.",
        "There is a water pipe leak near Kalanki chowk. Water has been flowing on the road for 3 days.",
        "Street lights are not working in Balaju area. It is very dark at night and unsafe for pedestrians.",
        "There is illegal construction happening near Pashupatinath temple area. They are violating building codes.",
        "The drainage system is blocked near Thamel. During rain, the entire road gets flooded.",
        "Public toilet near bus park is in very bad condition. It needs immediate repair and cleaning.",
        "Road near Swayambhunath is completely damaged. Large vehicles cannot pass through.",
    ]
    return random.choice(mock_transcriptions)
