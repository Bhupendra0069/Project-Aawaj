"""
Management command to compute analytics: clustering, hotspots, duplicates, ward assignment.

Usage: python manage.py compute_analytics
       python manage.py compute_analytics --skip-duplicates
"""

from django.core.management.base import BaseCommand

from complaints.models import Complaint, AnalyticsConfig
from complaints.services import (
    clustering_service, hotspot_service, duplicate_service,
    spam_service, geo_service
)


class Command(BaseCommand):
    help = 'Run analytics computation: DBSCAN clustering, hotspot scoring, duplicate detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-duplicates', action='store_true',
            help='Skip duplicate detection (faster)'
        )
        parser.add_argument(
            '--skip-spam', action='store_true',
            help='Skip spam/trust score recalculation'
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('AAWAJ Analytics Computation')
        self.stdout.write('=' * 50)

        # Ensure config exists
        config = AnalyticsConfig.get_config()
        self.stdout.write(f'  Config: eps={config.dbscan_eps_meters}m, min_samples={config.dbscan_min_samples}')

        # Step 1: Assign wards to complaints missing ward info
        self.stdout.write('\n[1] Ward Assignment...')
        unassigned = Complaint.objects.filter(ward='', status__in=['published', 'pending_review', 'resolved'])
        assigned = 0
        for c in unassigned:
            ward = geo_service.detect_ward(c.latitude, c.longitude)
            if ward:
                c.ward = ward
                c.save(update_fields=['ward'])
                assigned += 1
        self.stdout.write(self.style.SUCCESS(f'  [OK] Assigned ward to {assigned} complaints'))

        # Step 2: Run DBSCAN clustering
        self.stdout.write('\n[2] DBSCAN Clustering...')
        clusters = clustering_service.run_dbscan_clustering()
        saved = clustering_service.save_clusters(clusters)
        self.stdout.write(self.style.SUCCESS(f'  [OK] Found {len(clusters)} clusters, saved {saved}'))

        for c in clusters[:5]:
            self.stdout.write(
                f'    Cluster #{c["cluster_id"]}: {c["complaint_count"]} complaints, '
                f'severity={c["severity_average"]:.1f}, ward={c["ward_name"]}'
            )

        # Step 3: Compute hotspot scores
        self.stdout.write('\n[3] Hotspot Scoring...')
        hotspots = hotspot_service.compute_hotspot_scores()
        snapshots = hotspot_service.save_hotspot_snapshot()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Scored {len(hotspots)} hotspots, saved {snapshots} snapshots'))

        for h in hotspots[:5]:
            self.stdout.write(
                f'    >> {h["ward_name"]}: score={h["priority_score"]:.1f}, '
                f'{h["complaint_count"]} complaints, {h["unresolved_count"]} unresolved'
            )

        # Step 4: Duplicate detection
        if not options['skip_duplicates']:
            self.stdout.write('\n[4] Duplicate Detection...')
            dup_count = duplicate_service.detect_duplicates()
            groups = duplicate_service.get_duplicate_groups()
            self.stdout.write(self.style.SUCCESS(
                f'  [OK] Found {dup_count} similarity pairs, {len(groups)} duplicate groups'
            ))
        else:
            self.stdout.write('\n[4] Duplicate detection skipped')

        # Step 5: Spam/trust scoring
        if not options['skip_spam']:
            self.stdout.write('\n[5] Trust Score Update...')
            updated = spam_service.update_all_trust_scores()
            self.stdout.write(self.style.SUCCESS(f'  [OK] Updated trust scores for {updated} complaints'))
        else:
            self.stdout.write('\n[5] Spam detection skipped')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Analytics computation complete!'))
        self.stdout.write('=' * 50)
