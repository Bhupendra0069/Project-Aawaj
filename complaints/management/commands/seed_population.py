"""
Management command to seed Kathmandu Valley ward population data.
Uses realistic estimates from Nepal Census 2021.

Usage: python manage.py seed_population
"""

from django.core.management.base import BaseCommand
from complaints.models import RegionPopulation


# Kathmandu Metropolitan City wards with approximate population and center coordinates
KMC_WARDS = [
    {"ward": 1, "name": "Naxal", "pop": 22500, "area": 1.2, "lat": 27.7150, "lng": 85.3250},
    {"ward": 2, "name": "Durbarmarg", "pop": 18200, "area": 0.9, "lat": 27.7130, "lng": 85.3180},
    {"ward": 3, "name": "Bhotahity", "pop": 25800, "area": 1.1, "lat": 27.7050, "lng": 85.3100},
    {"ward": 4, "name": "Thamel", "pop": 20100, "area": 0.8, "lat": 27.7155, "lng": 85.3120},
    {"ward": 5, "name": "Asan", "pop": 28500, "area": 0.7, "lat": 27.7070, "lng": 85.3130},
    {"ward": 6, "name": "Boudha", "pop": 35200, "area": 2.5, "lat": 27.7215, "lng": 85.3615},
    {"ward": 7, "name": "Chabahil", "pop": 32100, "area": 2.0, "lat": 27.7185, "lng": 85.3430},
    {"ward": 8, "name": "Gaushala", "pop": 27400, "area": 1.8, "lat": 27.7100, "lng": 85.3370},
    {"ward": 9, "name": "Sinamangal", "pop": 33600, "area": 2.2, "lat": 27.6950, "lng": 85.3470},
    {"ward": 10, "name": "Baneshwor", "pop": 38500, "area": 2.1, "lat": 27.6900, "lng": 85.3350},
    {"ward": 11, "name": "Minbhawan", "pop": 30200, "area": 1.9, "lat": 27.6850, "lng": 85.3400},
    {"ward": 12, "name": "Tripureshwor", "pop": 24300, "area": 1.3, "lat": 27.6950, "lng": 85.3100},
    {"ward": 13, "name": "Kalimati", "pop": 29700, "area": 1.5, "lat": 27.6970, "lng": 85.3000},
    {"ward": 14, "name": "Teku", "pop": 26100, "area": 1.4, "lat": 27.6920, "lng": 85.3050},
    {"ward": 15, "name": "Balaju", "pop": 42300, "area": 3.5, "lat": 27.7300, "lng": 85.3000},
    {"ward": 16, "name": "Gongabu", "pop": 48700, "area": 3.2, "lat": 27.7350, "lng": 85.3150},
    {"ward": 17, "name": "Tokha", "pop": 35800, "area": 4.5, "lat": 27.7500, "lng": 85.3200},
    {"ward": 18, "name": "Budhanilkantha", "pop": 28900, "area": 5.0, "lat": 27.7700, "lng": 85.3350},
    {"ward": 19, "name": "Kapan", "pop": 39200, "area": 3.8, "lat": 27.7450, "lng": 85.3450},
    {"ward": 20, "name": "Jorpati", "pop": 31500, "area": 3.0, "lat": 27.7380, "lng": 85.3650},
    {"ward": 21, "name": "Maitidevi", "pop": 27600, "area": 1.6, "lat": 27.7100, "lng": 85.3300},
    {"ward": 22, "name": "Maharajgunj", "pop": 23400, "area": 2.0, "lat": 27.7250, "lng": 85.3300},
    {"ward": 23, "name": "Lazimpat", "pop": 19800, "area": 1.1, "lat": 27.7200, "lng": 85.3200},
    {"ward": 24, "name": "Swayambhu", "pop": 34500, "area": 3.2, "lat": 27.7150, "lng": 85.2900},
    {"ward": 25, "name": "Kalanki", "pop": 37800, "area": 2.8, "lat": 27.6930, "lng": 85.2820},
    {"ward": 26, "name": "Kirtipur", "pop": 31200, "area": 3.5, "lat": 27.6800, "lng": 85.2750},
    {"ward": 27, "name": "Dahachowk", "pop": 22800, "area": 4.2, "lat": 27.6700, "lng": 85.2850},
    {"ward": 28, "name": "Thankot", "pop": 18500, "area": 5.5, "lat": 27.6600, "lng": 85.2600},
    {"ward": 29, "name": "Satdobato", "pop": 41200, "area": 3.0, "lat": 27.6650, "lng": 85.3200},
    {"ward": 30, "name": "Koteshwor", "pop": 36500, "area": 2.4, "lat": 27.6780, "lng": 85.3450},
    {"ward": 31, "name": "Jadibuti", "pop": 33800, "area": 2.6, "lat": 27.6740, "lng": 85.3550},
    {"ward": 32, "name": "Gothatar", "pop": 44200, "area": 3.4, "lat": 27.7050, "lng": 85.3700},
]

# Lalitpur Sub-Metropolitan City wards (selected)
LALITPUR_WARDS = [
    {"ward": 1, "name": "Pulchowk", "pop": 22000, "area": 1.5, "lat": 27.6800, "lng": 85.3180},
    {"ward": 2, "name": "Mangalbazar", "pop": 18500, "area": 1.0, "lat": 27.6720, "lng": 85.3250},
    {"ward": 3, "name": "Lagankhel", "pop": 25300, "area": 1.8, "lat": 27.6650, "lng": 85.3250},
    {"ward": 4, "name": "Jawalakhel", "pop": 19800, "area": 1.3, "lat": 27.6720, "lng": 85.3130},
    {"ward": 5, "name": "Kupondol", "pop": 21400, "area": 1.4, "lat": 27.6850, "lng": 85.3100},
    {"ward": 6, "name": "Imadol", "pop": 31200, "area": 2.5, "lat": 27.6550, "lng": 85.3350},
    {"ward": 7, "name": "Gwarko", "pop": 28900, "area": 2.2, "lat": 27.6600, "lng": 85.3300},
]

# Bhaktapur Municipality (selected)
BHAKTAPUR_WARDS = [
    {"ward": 1, "name": "Durbar Square", "pop": 15200, "area": 0.8, "lat": 27.6720, "lng": 85.4270},
    {"ward": 2, "name": "Dattatreya", "pop": 12800, "area": 0.7, "lat": 27.6750, "lng": 85.4320},
    {"ward": 3, "name": "Suryabinayak", "pop": 28500, "area": 3.0, "lat": 27.6650, "lng": 85.4350},
    {"ward": 4, "name": "Thimi", "pop": 32100, "area": 3.5, "lat": 27.6780, "lng": 85.3900},
]


class Command(BaseCommand):
    help = 'Seed Kathmandu Valley ward population data (KMC + Lalitpur + Bhaktapur)'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        datasets = [
            ('Kathmandu Metropolitan City', KMC_WARDS),
            ('Lalitpur Sub-Metropolitan City', LALITPUR_WARDS),
            ('Bhaktapur Municipality', BHAKTAPUR_WARDS),
        ]

        for municipality, wards in datasets:
            for w in wards:
                ward_name = f"{municipality} Ward {w['ward']} - {w['name']}"
                obj, created = RegionPopulation.objects.update_or_create(
                    ward_name=ward_name,
                    defaults={
                        'ward_number': w['ward'],
                        'municipality': municipality,
                        'population': w['pop'],
                        'area_km2': w['area'],
                        'center_latitude': w['lat'],
                        'center_longitude': w['lng'],
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        total = created_count + updated_count
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Population data loaded: {created_count} created, {updated_count} updated ({total} total wards)'
        ))
