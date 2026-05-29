"""
Image utility functions for duplicate detection and analysis.
"""

import imagehash
from PIL import Image
from io import BytesIO
from math import radians, sin, cos, sqrt, atan2


def calculate_image_hash(image_file):
    """
    Calculate perceptual hash of image for duplicate detection.
    Returns: hash string representation or None if error
    """
    try:
        # Read image
        image_file.seek(0)
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate perceptual hash
        img_hash = imagehash.phash(img)
        
        # Store as string (imagehash objects have a string representation)
        return str(img_hash)
    except Exception as e:
        print(f"Error calculating image hash: {e}")
        return None


def hamming_distance(hash1_str, hash2_str):
    """
    Calculate Hamming distance between two hash strings.
    Uses bit-level XOR comparison.
    Returns: integer distance (0 = identical, inf = invalid)
    """
    if not hash1_str or not hash2_str:
        return float('inf')
    
    if len(hash1_str) != len(hash2_str):
        return float('inf')
    
    try:
        # Convert hex strings to integers and XOR
        val1 = int(hash1_str, 16)
        val2 = int(hash2_str, 16)
        xor_result = val1 ^ val2
        # Count the number of 1 bits (Hamming distance)
        distance = bin(xor_result).count('1')
        return distance
    except (ValueError, TypeError) as e:
        print(f"Error computing Hamming distance: {e}")
        return float('inf')


def get_similar_images_by_hash(image_hash, exclude_complaint_id=None, hamming_threshold=5):
    """
    Find existing images with same or similar hash (within Hamming threshold).
    Returns: QuerySet of ComplaintImage objects
    
    Args:
        image_hash: hash string of new image
        exclude_complaint_id: complaint ID to exclude from results
        hamming_threshold: max Hamming distance for match (default 5 out of 64 bits)
    """
    from .models import ComplaintImage
    
    if not image_hash:
        return ComplaintImage.objects.none()
    
    # Get ALL images (even those without hashes - we'll compute them on demand)
    all_images = ComplaintImage.objects.all()
    
    if exclude_complaint_id:
        all_images = all_images.exclude(complaint_id=exclude_complaint_id)
    
    # Filter by Hamming distance  
    matching_image_ids = []
    for img in all_images:
        try:
            # If image doesn't have hash, calculate it now
            img_hash = img.image_hash
            if not img_hash or img_hash == '':
                if img.image:
                    img.image.seek(0)
                    img_hash = calculate_image_hash(img.image)
                    if img_hash:
                        # Save the computed hash for future use
                        img.image_hash = img_hash
                        img.save(update_fields=['image_hash'])
                else:
                    continue
            
            if not img_hash:
                continue
            
            distance = hamming_distance(image_hash, img_hash)
            # Accept if distance is valid (not inf) and within threshold
            if distance != float('inf') and distance <= hamming_threshold:
                matching_image_ids.append(img.id)
                print(f"[DUPLICATE_DETECTION] Found similar image ID {img.id} for complaint {img.complaint_id} with Hamming distance: {distance}")
        except Exception as e:
            print(f"[DUPLICATE_DETECTION] Error comparing hashes for image {img.id}: {e}")
            continue
    
    return ComplaintImage.objects.filter(id__in=matching_image_ids)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in meters between two GPS coordinates.
    Using Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def check_duplicate_by_location(image_file, latitude, longitude, category, radius_meters=500, hamming_threshold=5):
    """
    Check if image is duplicate (same image, different location).
    
    Uses perceptual hash with Hamming distance for robust image comparison.
    Detects when the same image is uploaded from different GPS locations.
    
    Args:
        image_file: uploaded image file
        latitude: GPS latitude of report
        longitude: GPS longitude of report
        category: complaint category (must match to be considered duplicate)
        radius_meters: distance threshold (default 500m = "same location")
        hamming_threshold: max Hamming distance to consider images identical (default 5)
    
    Returns dict:
        - is_duplicate: True if same image from different location
        - duplicate_complaint: Original Complaint object if duplicate, else None
        - duplicate_location: Location text of original complaint
        - distance_meters: Distance between locations if duplicate
        - message: Human-readable message
        - image_hash: Calculated hash of this image
    """
    from .models import ComplaintImage, Complaint
    
    # Calculate image hash for the new image
    image_hash = calculate_image_hash(image_file)
    if not image_hash:
        print(f"[DUPLICATE_CHECK] Could not calculate hash for new image")
        return {
            'is_duplicate': False,
            'duplicate_complaint': None,
            'duplicate_location': None,
            'message': 'Could not analyze image',
            'image_hash': None
        }
    
    print(f"[DUPLICATE_CHECK] New image hash: {image_hash}")
    
    # Find existing images with similar hash
    similar_images = get_similar_images_by_hash(image_hash, hamming_threshold=hamming_threshold)
    
    if not similar_images.exists():
        print(f"[DUPLICATE_CHECK] No similar images found")
        return {
            'is_duplicate': False,
            'duplicate_complaint': None,
            'duplicate_location': None,
            'message': 'Image is unique',
            'image_hash': image_hash
        }
    
    print(f"[DUPLICATE_CHECK] Found {similar_images.count()} similar images")
    
    # Get complaints from similar images, filtered by category
    similar_complaint_ids = set(similar_images.values_list('complaint_id', flat=True))
    same_category_complaints = Complaint.objects.filter(
        id__in=similar_complaint_ids,
        category=category
    ).distinct()
    
    if not same_category_complaints.exists():
        print(f"[DUPLICATE_CHECK] No complaints found with same category: {category}")
        return {
            'is_duplicate': False,
            'duplicate_complaint': None,
            'duplicate_location': None,
            'message': 'Image is unique',
            'image_hash': image_hash
        }
    
    print(f"[DUPLICATE_CHECK] Found {same_category_complaints.count()} complaints with matching category")
    
    # Check each matching complaint's location
    for complaint in same_category_complaints:
        distance = calculate_distance(
            latitude, longitude,
            complaint.latitude, complaint.longitude
        )
        
        print(f"[DUPLICATE_CHECK] Checking against {complaint.complaint_code}: distance={distance:.2f}m, threshold={radius_meters}m")
        
        # Different location = duplicate report
        if distance > radius_meters:
            print(f"[DUPLICATE_CHECK] ⚠️ DUPLICATE DETECTED: Same image from different location!")
            return {
                'is_duplicate': True,
                'duplicate_complaint': complaint,
                'duplicate_location': complaint.location_text,
                'distance_meters': distance,
                'message': f"This image was already reported at '{complaint.location_text}' ({distance:.0f}m away). You cannot report the same issue from different locations.",
                'image_hash': image_hash
            }
    
    # Same location (or close enough) = valid new report
    print(f"[DUPLICATE_CHECK] ✓ Image location is valid - not a duplicate")
    return {
        'is_duplicate': False,
        'duplicate_complaint': None,
        'duplicate_location': None,
        'message': 'Image location is valid',
        'image_hash': image_hash
    }
