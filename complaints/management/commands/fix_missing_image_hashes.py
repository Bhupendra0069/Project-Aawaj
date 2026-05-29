"""
Management command to fix missing image hashes.
Recalculates hashes for images that don't have them yet.
"""

from django.core.management.base import BaseCommand
from complaints.models import ComplaintImage
from complaints.image_utils import calculate_image_hash


class Command(BaseCommand):
    help = 'Fix missing image hashes for all ComplaintImage records'

    def handle(self, *args, **options):
        # Find images without hashes
        missing_hash_images = ComplaintImage.objects.filter(image_hash='')
        count = missing_hash_images.count()
        
        self.stdout.write(f"Found {count} images without hashes")
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("All images have hashes!"))
            return
        
        # Calculate hashes
        fixed = 0
        errors = 0
        
        for img in missing_hash_images:
            try:
                if img.image:
                    img.image.seek(0)
                    image_hash = calculate_image_hash(img.image)
                    if image_hash:
                        img.image_hash = image_hash
                        img.save(update_fields=['image_hash'])
                        fixed += 1
                        self.stdout.write(f"✓ Fixed {img.complaint.complaint_code}: {image_hash}")
                    else:
                        errors += 1
                        self.stdout.write(self.style.WARNING(f"✗ Could not calculate hash for {img.complaint.complaint_code}"))
                else:
                    errors += 1
                    self.stdout.write(self.style.WARNING(f"✗ Image file missing for {img.complaint.complaint_code}"))
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"✗ Error processing {img.complaint.complaint_code}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ Fixed {fixed} images with missing hashes"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠ {errors} errors encountered"))
