"""
AAWAJ Demo Setup Command
Creates demo users, groups, and sample complaint data for demonstration.
Usage: python manage.py setup_demo
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from complaints.models import Complaint, ComplaintImage, ComplaintAudio, ModerationLog, GovernmentAction


# Realistic Kathmandu Valley locations
LOCATIONS = [
    {"text": "Ratnapark, Kathmandu", "lat": 27.7060, "lng": 85.3148},
    {"text": "Kalanki Chowk, Kathmandu", "lat": 27.6937, "lng": 85.2812},
    {"text": "Thamel, Kathmandu", "lat": 27.7153, "lng": 85.3126},
    {"text": "Balaju, Kathmandu", "lat": 27.7258, "lng": 85.3044},
    {"text": "Swayambhunath, Kathmandu", "lat": 27.7149, "lng": 85.2903},
    {"text": "Patan Durbar Square, Lalitpur", "lat": 27.6727, "lng": 85.3255},
    {"text": "Bhaktapur Durbar Square, Bhaktapur", "lat": 27.6722, "lng": 85.4279},
    {"text": "Baneshwor, Kathmandu", "lat": 27.6917, "lng": 85.3406},
    {"text": "Chabahil, Kathmandu", "lat": 27.7178, "lng": 85.3410},
    {"text": "Jorpati, Kathmandu", "lat": 27.7257, "lng": 85.3635},
    {"text": "Kirtipur, Kathmandu", "lat": 27.6814, "lng": 85.2783},
    {"text": "New Road, Kathmandu", "lat": 27.7042, "lng": 85.3117},
    {"text": "Lazimpat, Kathmandu", "lat": 27.7207, "lng": 85.3247},
    {"text": "Maitighar, Kathmandu", "lat": 27.6946, "lng": 85.3252},
    {"text": "Sundhara, Kathmandu", "lat": 27.7016, "lng": 85.3114},
    {"text": "Jawalakhel, Lalitpur", "lat": 27.6703, "lng": 85.3148},
    {"text": "Koteshwor, Kathmandu", "lat": 27.6785, "lng": 85.3495},
    {"text": "Satdobato, Lalitpur", "lat": 27.6568, "lng": 85.3280},
    {"text": "Gongabu Bus Park, Kathmandu", "lat": 27.7309, "lng": 85.3127},
    {"text": "Budhanilkantha, Kathmandu", "lat": 27.7711, "lng": 85.3643},
]

# Sample complaint descriptions per category
COMPLAINT_DATA = {
    'roads': [
        "Large pothole near the main junction causing traffic and multiple vehicle damage. The hole is about 2 feet wide and getting worse with each rain.",
        "Road surface completely destroyed near the bridge. Trucks and buses are struggling to pass through. Urgent repair needed.",
        "Footpath tiles broken and dangerous for pedestrians. Several elderly people have slipped and fallen in the past week.",
    ],
    'garbage': [
        "Garbage pile has been accumulating for over a week near the market area. The stench is unbearable and causing health concerns for nearby residents.",
        "Illegal dumping of construction waste on the riverside. This is polluting the water and creating environmental hazard.",
        "No garbage collection for 10 days in our ward. Bins are overflowing and stray dogs are spreading the waste everywhere.",
    ],
    'water': [
        "Major water pipe leak flooding the road near the intersection. Water has been flowing non-stop for 3 days wasting thousands of liters.",
        "Drainage system completely blocked causing severe waterlogging during rain. The entire area becomes inaccessible.",
        "Contaminated water supply in our area. Residents are falling sick with stomach ailments. Need immediate water quality check.",
    ],
    'electricity': [
        "Street lights not working in our area for the past month. The road is extremely dark at night making it unsafe for pedestrians.",
        "Exposed electric wires hanging dangerously low near the school. Children are at serious risk. Immediate action needed.",
        "Frequent power outages lasting 6-8 hours daily despite load shedding schedule showing only 2 hours. Transformer needs replacement.",
    ],
    'health': [
        "Open sewage near the school causing foul smell and health hazards. Children are constantly getting sick.",
        "Dead animal carcass left on the road for days. Nobody from the municipality has come to remove it despite multiple calls.",
        "Stagnant water breeding mosquitoes in empty plots. Dengue cases increasing in the neighborhood.",
    ],
    'education': [
        "Government school building has cracks in the walls and leaking roof. Classrooms are unsafe during monsoon season.",
        "School in our area has no proper toilet facilities. Girl students are especially affected and attendance is dropping.",
    ],
    'corruption': [
        "Ward office demanding extra fees for birth certificate that should be free. This has been happening for months.",
        "Government tender irregularities in road construction project. Same contractor awarded repeatedly despite poor quality work.",
    ],
    'infrastructure': [
        "Public park completely neglected. Broken benches, no lights, overgrown vegetation. Used to be a beautiful community space.",
        "Bus stop shelter collapsed two months ago and not rebuilt. Commuters wait in sun and rain with no protection.",
        "Public toilet near the temple area is in extremely poor condition. No water, broken doors, health hazard for tourists and locals.",
    ],
}


class Command(BaseCommand):
    help = 'Set up demo users, groups, and sample complaint data for AAWAJ platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete all existing complaints before creating new ones',
        )

    def _print(self, msg, style=None):
        """Safe print that handles Windows encoding issues with emojis."""
        try:
            if style:
                self.stdout.write(style(msg))
            else:
                self.stdout.write(msg)
        except UnicodeEncodeError:
            # Fallback: strip non-ASCII chars
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            if style:
                self.stdout.write(style(safe_msg))
            else:
                self.stdout.write(safe_msg)

    def handle(self, *args, **options):
        self._print('\n=== AAWAJ Demo Setup ===\n', self.style.MIGRATE_HEADING)

        # 1. Create Groups
        self._print('  Creating auth groups...')
        mod_group, _ = Group.objects.get_or_create(name='moderator')
        gov_group, _ = Group.objects.get_or_create(name='government')
        self._print('  [OK] Groups created: moderator, government', self.style.SUCCESS)

        # 2. Create Superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@aawaj.org.np', 'admin123')
            self._print('  [OK] Superuser created: admin / admin123', self.style.SUCCESS)
        else:
            self._print('  -> Superuser "admin" already exists')

        # 3. Create Moderator User
        mod_user, created = User.objects.get_or_create(
            username='moderator',
            defaults={'first_name': 'Aarav', 'last_name': 'Sharma', 'email': 'moderator@aawaj.org.np'}
        )
        if created:
            mod_user.set_password('mod123')
            mod_user.is_staff = True
            mod_user.save()
        mod_user.groups.add(mod_group)
        self._print('  [OK] Moderator user: moderator / mod123', self.style.SUCCESS)

        # 4. Create Government User
        gov_user, created = User.objects.get_or_create(
            username='government',
            defaults={'first_name': 'Ram', 'last_name': 'Adhikari', 'email': 'gov@aawaj.org.np'}
        )
        if created:
            gov_user.set_password('gov123')
            gov_user.is_staff = True
            gov_user.save()
        gov_user.groups.add(gov_group)
        self._print('  [OK] Government user: government / gov123', self.style.SUCCESS)

        # 5. Optionally reset
        if options['reset']:
            count = Complaint.objects.count()
            Complaint.objects.all().delete()
            self._print(f'  [!] Deleted {count} existing complaints', self.style.WARNING)

        # 6. Create Sample Complaints
        self._print('\n  Creating sample complaints...')
        created_complaints = []

        for category, descriptions in COMPLAINT_DATA.items():
            for desc in descriptions:
                loc = random.choice(LOCATIONS)

                # Vary the AI results for realism
                confidence = round(random.uniform(0.35, 0.95), 2)
                severity = random.randint(3, 10)
                is_urgent = severity >= 8

                if confidence >= 0.7:
                    verdict = 'high'
                    status = 'published'
                    priority = 'high' if severity >= 7 else 'medium'
                elif confidence >= 0.45:
                    verdict = 'medium'
                    status = 'pending_review'
                    priority = 'medium'
                else:
                    verdict = 'low'
                    status = 'rejected'
                    priority = 'low'

                if is_urgent:
                    priority = 'critical'

                complaint = Complaint.objects.create(
                    description=desc,
                    location_text=loc['text'],
                    latitude=loc['lat'] + random.uniform(-0.005, 0.005),
                    longitude=loc['lng'] + random.uniform(-0.005, 0.005),
                    status=status,
                    category=category,
                    priority=priority,
                    ai_verdict=verdict,
                    ai_confidence_score=confidence,
                    ai_category_detected=category,
                    ai_is_fake=False,
                    ai_urgency=is_urgent,
                    ai_severity_score=severity,
                    ai_generated_report=self._generate_report(category, loc['text'], desc, severity, priority),
                )
                created_complaints.append(complaint)
                self._print(f'    + {complaint.complaint_code} [{category}] -> {status}')

        # 7. Add moderation logs for some published complaints
        self._print('\n  Adding moderation logs...')
        published = [c for c in created_complaints if c.status == 'published']
        for complaint in published[:5]:
            ModerationLog.objects.create(
                complaint=complaint,
                moderator=mod_user,
                action='approve',
                notes='Evidence verified. Forwarding to government dashboard.'
            )

        rejected = [c for c in created_complaints if c.status == 'rejected']
        for complaint in rejected:
            ModerationLog.objects.create(
                complaint=complaint,
                moderator=mod_user,
                action='reject',
                notes='Low quality evidence. Image unclear or irrelevant.'
            )
        self._print('  [OK] Moderation logs added', self.style.SUCCESS)

        # 8. Add government actions for some published complaints
        self._print('  Adding government actions...')
        departments = [
            'Department of Roads, KMC',
            'Solid Waste Management Division, KMC',
            'Nepal Water Supply Corporation',
            'Nepal Electricity Authority',
            'Department of Health Services',
        ]

        for complaint in published[:3]:
            GovernmentAction.objects.create(
                complaint=complaint,
                action_type='acknowledged',
                notes='Complaint received and forwarded to field team.',
                officer_name=f'{gov_user.first_name} {gov_user.last_name}',
                department=random.choice(departments)
            )

        # Resolve 2 complaints
        for complaint in published[:2]:
            GovernmentAction.objects.create(
                complaint=complaint,
                action_type='resolved',
                notes='Issue has been resolved. Field team confirmed fix.',
                officer_name=f'{gov_user.first_name} {gov_user.last_name}',
                department=random.choice(departments)
            )
            complaint.status = 'resolved'
            complaint.save()

        self._print('  [OK] Government actions added', self.style.SUCCESS)

        # Summary
        total = len(created_complaints)
        pub = sum(1 for c in created_complaints if c.status == 'published')
        rev = sum(1 for c in created_complaints if c.status == 'pending_review')
        rej = sum(1 for c in created_complaints if c.status == 'rejected')
        res = Complaint.objects.filter(status='resolved').count()

        self._print(f'\n--- Summary ---', self.style.MIGRATE_HEADING)
        self._print(f'  Total complaints: {total}')
        self._print(f'  Published: {pub} | Pending Review: {rev} | Rejected: {rej} | Resolved: {res}')
        self._print(f'\n  [OK] Demo setup complete!', self.style.SUCCESS)
        self._print(f'\n  Login credentials:')
        self._print(f'  +==============+==============+==========+')
        self._print(f'  | Role         | Username     | Password |')
        self._print(f'  +==============+==============+==========+')
        self._print(f'  | Admin        | admin        | admin123 |')
        self._print(f'  | Moderator    | moderator    | mod123   |')
        self._print(f'  | Government   | government   | gov123   |')
        self._print(f'  +==============+==============+==========+')
        self._print(f'\n  Start server: python manage.py runserver\n')

    def _generate_report(self, category, location, description, severity, priority):
        """Generate a structured AI report for a complaint."""
        category_labels = {
            'roads': 'Roads & Transportation',
            'garbage': 'Waste Management',
            'water': 'Water Supply & Drainage',
            'electricity': 'Electricity & Power Supply',
            'health': 'Public Health',
            'education': 'Education Infrastructure',
            'corruption': 'Governance & Transparency',
            'infrastructure': 'Public Infrastructure',
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
        }

        return f"""=== AAWAJ COMPLAINT REPORT ===

CATEGORY: {category_labels.get(category, 'General Issue')}
LOCATION: {location}
SEVERITY: {severity}/10
PRIORITY: {priority.upper()}

CITIZEN REPORT:
{description}

RECOMMENDED DEPARTMENT:
{dept_map.get(category, 'Kathmandu Metropolitan City Office')}

AI ANALYSIS SUMMARY:
This complaint has been automatically classified as a {category_labels.get(category, 'general').lower()} issue.
The AI system has assessed the severity as {severity}/10 based on the provided evidence.
{'URGENT: This issue requires immediate attention.' if severity >= 8 else 'Standard processing timeline recommended.'}

Generated by AAWAJ AI System
=============================="""
