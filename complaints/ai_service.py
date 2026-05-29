"""
AAWAJ AI Service - Strict AI Validation Implementation
Uses Groq API (Llama Vision) for real image analysis AND category detection.
Validates civic issues in images and matches descriptions to detected content.
"""

import random
import hashlib
import json
import base64
import requests
from datetime import datetime


# Category keywords for fallback text-based classification
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

# Valid category keys (must match model CATEGORY_CHOICES)
VALID_CATEGORIES = ['roads', 'garbage', 'water', 'electricity', 'health', 'education', 'corruption', 'infrastructure', 'other']

# Severity indicators
HIGH_SEVERITY_KEYWORDS = [
    'danger', 'emergency', 'urgent', 'accident', 'collapse', 'fire', 'flood',
    'death', 'injury', 'toxic', 'explosion', 'fallen', 'broken', 'severe',
    'critical', 'risk', 'hazardous', 'khatarnak', 'aapatkaalin'
]

# Groq API settings
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TEXT_MODEL = "llama-3.3-70b-versatile"


def _call_groq_vision(api_key, prompt, image_base64, mime_type="image/jpeg"):
    """Call Groq API with image for vision analysis."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 600,
        "temperature": 0.1,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_groq_text(api_key, prompt):
    """Call Groq API for text-only analysis."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_TEXT_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.1,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def classify_category(text):
    """Fallback: Classify complaint text into a category using keyword matching."""
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
    Analyze image using Groq Vision API (Llama 4 Scout) to detect civic issues
    AND determine the correct complaint category from the image.

    Returns: (is_civic_issue_detected, confidence_score, detected_issues, description, detected_category)
    """
    if not image_file:
        return False, 0.0, [], "", "other"

    from django.conf import settings

    try:
        # Read image
        image_data = image_file.read()
        image_file.seek(0)
        image_b64 = base64.standard_b64encode(image_data).decode('utf-8')

        api_key = settings.GROQ_API_KEY
        if not api_key:
            return None, 0.2, [], "Groq API key not configured", "unknown"

        # Create prompt for vision analysis — includes CATEGORY detection
        prompt = """STRICT VALIDATION - Analyze this image carefully:
1. Is this a REAL OUTDOOR PHOTOGRAPH of an actual civic/public issue?
2. If ABSOLUTELY YES, what specific category does it belong to?

CRITICAL FILTERS (Answer NO if ANY apply):
✗ Is it a screenshot, form, document, website, app interface? → Answer NO
✗ Is it a photo of a phone/laptop/tablet screen? → Answer NO
✗ Is it a drawing, meme, poster, or artwork? → Answer NO
✗ Is it an indoor photo without outdoor context? → Answer NO
✗ Is it a random photo (selfie, food, object) without civic issue? → Answer NO
✗ Is it blurry or unclear what the issue is? → Answer NO
✗ Does it show ONLY text/numbers without physical evidence? → Answer NO

VALID YES CONDITIONS (ALL must be true):
✓ Real outdoor photograph taken with a camera
✓ Shows an ACTUAL physical civic problem
✓ Problem is CLEARLY VISIBLE and identifiable
✓ Location is public/outdoor space
✓ Image quality is good enough to identify the issue type

CATEGORY MAPPING (Be precise - only pick if issue is CLEARLY visible):
- roads: CLEAR potholes, VISIBLE road damage, OBVIOUS cracked pavement, broken asphalt surface
- garbage: Piles of VISIBLE trash, overflowing garbage bins, waste dumps
- water: CLEAR water leaks, visible flooding, broken water pipes, drainage issues
- electricity: Broken power lines, fallen poles, electrical hazards, no streetlights
- health: Open sewers, contaminated water, unsanitary conditions, disease hazards
- education: Damaged school buildings, broken classrooms, facility damage
- corruption: Illegal construction evidence, unauthorized structures
- infrastructure: Damaged public toilets, broken bridges, broken public buildings
- other: Genuine civic issue but doesn't fit above categories

Respond in this EXACT format:
IS_CIVIC_ISSUE: [YES/NO]
CONFIDENCE: [0.0-1.0]
CATEGORY: [one of: roads, garbage, water, electricity, health, education, corruption, infrastructure, other]
DETECTED_ISSUES: [specific visible issues or "None"]
DETAILED_DESCRIPTION: [what is physically visible in the photo]

EXTREMELY STRICT: If unsure, answer NO. If image quality is poor, answer NO. If it could be a screenshot, answer NO."""

        # Call Groq Vision API
        print(f"[AAWAJ AI] Calling Groq Vision API with image ({len(image_data)} bytes)...")
        response_text = _call_groq_vision(api_key, prompt, image_b64)
        print(f"[AAWAJ AI] Raw Groq response:\n{response_text}")

        # Parse response
        is_civic = False
        confidence = 0.0
        detected_issues = []
        description = ""
        detected_category = "other"

        for line in response_text.split('\n'):
            line_stripped = line.strip()
            if 'IS_CIVIC_ISSUE:' in line_stripped:
                is_civic = 'YES' in line_stripped.upper()
            elif 'CONFIDENCE:' in line_stripped:
                try:
                    conf_str = line_stripped.split(':')[1].strip()
                    conf_str = conf_str.split()[0].strip()
                    confidence = float(conf_str)
                    confidence = max(0.0, min(1.0, confidence))
                except:
                    confidence = 0.5 if is_civic else 0.1
            elif 'CATEGORY:' in line_stripped:
                cat = line_stripped.split(':', 1)[1].strip().lower()
                cat = cat.split()[0].strip() if cat else 'other'
                if cat in VALID_CATEGORIES:
                    detected_category = cat
                else:
                    detected_category = 'other'
            elif 'DETECTED_ISSUES:' in line_stripped:
                issues_str = line_stripped.split(':', 1)[1].strip()
                if issues_str.upper() != 'NONE' and issues_str.strip('"') != 'None':
                    detected_issues = [x.strip() for x in issues_str.split(',') if x.strip()]
            elif 'DETAILED_DESCRIPTION:' in line_stripped:
                description = line_stripped.split(':', 1)[1].strip()

        print(f"[AAWAJ AI] Parsed: civic={is_civic}, conf={confidence}, cat={detected_category}, issues={detected_issues}")

        # EXTRA VALIDATION: Reject if confidence is too low even if Groq says civic
        # (catches screenshots, poor quality, unclear issues)
        if is_civic and confidence < 0.6:
            print(f"[AAWAJ AI] ⚠️ Confidence too low ({confidence}) despite is_civic=True")
            print(f"[AAWAJ AI] → Likely screenshot or poor quality image, rejecting")
            is_civic = False
            confidence = max(0.05, confidence * 0.3)
            detected_category = 'other'

        # If AI says NO, lower confidence significantly
        if not is_civic:
            confidence = max(0.05, confidence * 0.2)
            detected_category = 'other'

        return is_civic, confidence, detected_issues, description, detected_category

    except Exception as e:
        # Fallback: if API fails, return special marker so process_complaint
        # knows to use text-based classification instead of forcing 'other'
        return None, 0.2, [], f"API Error: {str(e)}", "unknown"


def validate_description_matches_image(user_description, detected_issues, detected_description):
    """
    Check if user's text description matches what AI detected in image.
    Uses Groq text model for comparison.
    Returns: match_score (0.0-1.0)
    """
    if not user_description or not detected_issues:
        return 0.0

    from django.conf import settings

    try:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            return 0.5

        prompt = f"""Evaluate if the user's complaint description matches the civic issues detected in an image.

USER DESCRIPTION: "{user_description}"

IMAGE DETECTED: {', '.join(detected_issues)}
IMAGE DESCRIPTION: {detected_description}

Tasks:
1. Check if user mentions the issues detected in the image
2. Verify the description is about the same problem
3. Ensure location and context align

Respond in format:
MATCH_SCORE: [0.0-1.0]
REASONING: [brief explanation]

Scoring guide:
- 0.0-0.3: Description doesn't match image at all
- 0.4-0.6: Some overlap but significant differences
- 0.7-0.85: Good match with minor differences
- 0.86-1.0: Excellent match, user describes exactly what's in image"""

        response_text = _call_groq_text(api_key, prompt)

        match_score = 0.5

        for line in response_text.split('\n'):
            if 'MATCH_SCORE:' in line:
                try:
                    score_str = line.split(':')[1].strip().split()[0]
                    match_score = float(score_str)
                    match_score = max(0.0, min(1.0, match_score))
                except:
                    match_score = 0.5

        return match_score

    except Exception as e:
        return 0.5


def generate_report(complaint_data):
    """
    Generate a structured AI report for government dashboard.
    Enhanced with AI image analysis results.
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

    # Build AI image analysis section
    detected_info = complaint_data.get('detected_issues', [])
    if detected_info:
        detected_str = ', '.join(detected_info)
        ai_analysis = f"AI detected the following issues in the uploaded image: {detected_str}"
    else:
        ai_analysis = "AI analysis of image: No specific civic issues detected in the uploaded image."

    image_desc = complaint_data.get('image_description', '')
    if image_desc:
        ai_analysis += f"\nImage Description: {image_desc}"

    report = f"""━━━ AAWAJ COMPLAINT REPORT ━━━

📋 CATEGORY: {category_labels.get(category, 'General Issue')}
📍 LOCATION: {location}
⚠️ SEVERITY: {severity}/10
🔴 PRIORITY: {priority.upper()}

📝 CITIZEN REPORT:
{description}

📸 AI IMAGE ANALYSIS:
{ai_analysis}

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
    Implements STRICT validation:
    1. Image must be a REAL photo (not screenshot/fake)
    2. Image must show a civic issue
    3. Category is determined by what AI sees in the image
    4. Description must match detected content for auto-publish

    Returns dict with all AI analysis results.
    """
    description = complaint.description or ''

    # 1. Fallback text-based category (used only if image analysis fails)
    text_category, text_confidence = classify_category(description)
    print(f"[AAWAJ AI] Text-based category: {text_category} (confidence: {text_confidence})")

    # 2. Analyze severity from text
    severity, is_urgent = analyze_severity(description)

    # 3. Analyze image with Groq Vision API (STRICT CHECK)
    image_is_civic = False
    image_confidence = 0.0
    detected_issues = []
    image_description = ""
    image_category = "other"
    api_failed = False
    images = complaint.images.all()

    if images.exists():
        first_image = images.first()
        print(f"[AAWAJ AI] Analyzing image: {first_image.image.name}")
        try:
            result = analyze_image(first_image.image)
            image_is_civic, image_confidence, detected_issues, image_description, image_category = result
            print(f"[AAWAJ AI] Vision API result: is_civic={image_is_civic}, confidence={image_confidence}, category={image_category}")
            print(f"[AAWAJ AI] Detected issues: {detected_issues}")
            print(f"[AAWAJ AI] Image description: {image_description}")
            # Check if API failed (returns None for is_civic)
            if image_is_civic is None:
                api_failed = True
                image_is_civic = False
                print(f"[AAWAJ AI] ⚠️ API FAILED — falling back to text category: {text_category}")
        except Exception as e:
            api_failed = True
            image_is_civic = False
            image_confidence = 0.1
            detected_issues = []
            image_description = f"Analysis failed: {str(e)}"
            image_category = "other"
            print(f"[AAWAJ AI] ❌ EXCEPTION in image analysis: {str(e)}")
    else:
        # No image = low confidence
        image_is_civic = False
        image_confidence = 0.0
        print("[AAWAJ AI] No images attached to complaint")

    # 4. Determine final category:
    #    PRIORITY: Image > API Fallback > Force 'other'
    #    KEY FIX: If image is civic, ALWAYS use image category (no text override)
    if image_is_civic:
        # IMAGE detected civic issue → USE image category (even if generic 'other')
        # DO NOT fall back to text when image is civic
        category = image_category
        if category == 'other':
            print(f"[AAWAJ AI] ✅ Using IMAGE category (generic): {category}")
        else:
            print(f"[AAWAJ AI] ✅ Using IMAGE category: {category}")
    elif api_failed:
        # API completely failed (network/timeout/quota) → use text as fallback
        # This is acceptable because we couldn't validate image
        category = text_category
        print(f"[AAWAJ AI] ⚠️ API failed, using TEXT category: {category}")
    else:
        # Image is NOT civic (screenshot, random photo, fake)
        # DON'T assign real category — force 'other' regardless of text
        category = 'other'
        print(f"[AAWAJ AI] ❌ Image not civic, forcing category: other")

    # 5. Validate description matches detected image content
    description_match_score = 0.0
    if image_is_civic and description and detected_issues:
        description_match_score = validate_description_matches_image(
            description,
            detected_issues,
            image_description
        )
    elif image_is_civic and detected_issues:
        description_match_score = validate_description_matches_image(
            description if description else '',
            detected_issues,
            image_description
        )

    # 6. Calculate strict overall confidence (BOTH validations required)
    if image_is_civic:
        overall_confidence = (image_confidence * 0.6) + (description_match_score * 0.4)
    else:
        # Image doesn't show civic issue → confidence is very low
        overall_confidence = min(0.3, (text_confidence * 0.3))

    # 7. Determine AI verdict and routing (STRICTER THRESHOLDS)
    if api_failed:
        # API failed — can't validate, send to moderator with text-based assessment
        verdict = 'medium'
        status = 'pending_review'
        priority = 'medium' if severity >= 5 else 'low'
        overall_confidence = text_confidence * 0.5
    elif overall_confidence >= 0.75 and image_is_civic and description_match_score >= 0.65:
        # HIGH confidence: real photo + civic issue + description matches
        verdict = 'high'
        status = 'published'
        priority = 'high' if severity >= 7 else 'medium'
    elif overall_confidence >= 0.50 and image_is_civic:
        # MEDIUM confidence: real civic photo but description match uncertain
        verdict = 'medium'
        status = 'pending_review'
        priority = 'medium'
    else:
        # LOW confidence: screenshot, random photo, no civic issue, or poor match
        verdict = 'low'
        status = 'pending_review'
        priority = 'low'

    if is_urgent:
        priority = 'critical'

    if severity >= 8:
        priority = 'critical' if priority != 'critical' else priority

    # 8. Generate government report (with image analysis data)
    report_data = {
        'category': category,
        'location_text': complaint.location_text,
        'description': description,
        'ai_severity_score': severity,
        'priority': priority,
        'detected_issues': detected_issues,
        'image_description': image_description,
    }
    ai_report = generate_report(report_data)

    return {
        'category': category,
        'ai_verdict': verdict,
        'ai_confidence_score': round(overall_confidence, 2),
        'ai_is_fake': not image_is_civic,
        'ai_urgency': is_urgent,
        'ai_severity_score': severity,
        'ai_category_detected': category,
        'priority': priority,
        'status': status,
        'ai_generated_report': ai_report,
        'description_match_score': round(description_match_score, 2),
        'image_description': image_description,
        'detected_issues': detected_issues,
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
