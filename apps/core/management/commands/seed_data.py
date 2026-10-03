"""GHDI development seed data command.

Creates realistic sample data (fictional entities only) so every dashboard
and module can be experienced end-to-end. Run::

    python manage.py seed_data [--flush]
"""
from datetime import timedelta
from random import randint

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


def rand_range(lo, hi):
    return randint(int(lo), int(hi))


class Command(BaseCommand):
    help = "Seed the database with realistic GHDI sample data."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing sample data first.")

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()
        self.seed()
        self.stdout.write(self.style.SUCCESS("GHDI seed data created."))

    def _flush(self):
        from apps.assets.models import Asset
        from apps.beneficiaries.models import Beneficiary
        from apps.cms.models import Event, ImpactStat, NewsArticle, Page, TeamMember
        from apps.collaboration.models import Meeting, Task
        from apps.communications.models import Announcement, InternalMessage
        from apps.documents.models import Document
        from apps.finance.models import (Account, Advance, Budget, ExpenseRequest, Transaction)
        from apps.hr.models import Department, Employee, LeaveRequest, Training, Vacancy
        from apps.monitoring.models import Indicator, MEALReport
        from apps.partners.models import Donor, Grant, Partner
        from apps.procurement.models import (ProcurementRequest, PurchaseOrder, Quotation, Vendor)
        from apps.programs.models import Activity, Program, Project
        from apps.risk.models import Incident, Risk

        for klass in [Incident, Risk, InternalMessage, Announcement, Task, Meeting,
                      Document, PurchaseOrder, Quotation, ProcurementRequest, Vendor,
                      Grant, Partner, Donor, MEALReport, Indicator, Activity, Project,
                      Program, Training, Vacancy, LeaveRequest, Employee, Department,
                      Account, Budget, Transaction, ExpenseRequest, Advance,
                      Event, NewsArticle, Page, ImpactStat, TeamMember,
                      Beneficiary, Asset]:
            klass.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("Flushed existing sample data.")

    # SEED-START

    def seed(self):
        today = timezone.localdate()

        # ---- Organisation settings -----------------------------------
        from apps.core.models import Location, OrganizationSetting, SystemSetting

        OrganizationSetting.objects.get_or_create(pk=1)
        OrganizationSetting.load().save()
        SystemSetting.set("session_timeout_minutes", "480")
        SystemSetting.set("notification_poll_seconds", "60")

        loc_objs = []
        for name, lga, state in [
            ("Damaturu Central", "Damaturu", "Yobe"), ("Gashua", "Bade", "Yobe"),
            ("Potiskum", "Fika", "Yobe"), ("Ngelzarma", "Fune", "Yobe"),
            ("Geidam", "Geidam", "Yobe"), ("Goniri", "Gujba", "Yobe")]:
            loc, _ = Location.objects.get_or_create(name=name, lga=lga, state=state)
            loc_objs.append(loc)

        # ---- Users (one per role) -------------------------------------
        creds = {
            "admin": ("Super Administrator", "admin"), "execdir": ("Executive Director", "exec"),
            "hrofficer": ("HR Officer", "hr"), "progmanager": ("Program Manager", "pm"),
            "finofficer": ("Finance Officer", "fin"), "meal": ("MEAL Officer", "meal"),
            "procurement": ("Procurement Officer", "proc"), "staff": ("Staff Member", "staff"),
            "viewer": ("Viewer", "viewer"), "content": ("Content Manager", "content"),
        }
        users = {}
        password = "Ghdi@2026pass"  # dev-only sample credential
        for username, (name, role) in creds.items():
            u, created = User.objects.get_or_create(
                username=username,
                defaults=dict(email=f"{username}@ghdi.local", first_name=name.split()[0],
                              last_name=" ".join(name.split()[1:]) or name, role=role,
                              is_staff=True, is_active=True))
            if created:
                u.set_password(password)
                u.save()
            users[role] = u

        # ---- HR --------------------------------------------------------
        from apps.hr.models import (Department, Employee, LeaveRequest, LeaveType,
                                    Training, Vacancy)

        depts = {}
        for d in [("Programs", "PRG"), ("Protection", "PRT"), ("Education", "EDU"),
                  ("Finance", "FIN"), ("HR & Admin", "HRA"), ("MEAL", "MEL"), ("Operations", "OPS")]:
            dept, _ = Department.objects.get_or_create(name=d[0], defaults={"code": d[1]})
            depts[d[0]] = dept

        staff_rows = [
            ("Aisha", "Mohammed", "Executive Director", "exec", "HR & Admin"),
            ("Ibrahim", "Usman", "Director of Programs", "pm", "Programs"),
            ("Fatima", "Bello", "HR Officer", "hr", "HR & Admin"),
            ("Saidu", "Adamu", "Finance Officer", "fin", "Finance"),
            ("Maryam", "Garba", "MEAL Officer", "meal", "MEAL"),
            ("Daniel", "Yusuf", "Protection Officer", "staff", "Protection"),
            ("Hafsatu", "Ibrahim", "Education Officer", "staff", "Education"),
            ("Musa", "Dauda", "Field Officer", "staff", "Programs"),
            ("Rukayya", "Sani", "Operations Assistant", "staff", "Operations"),
            ("Amina", "Kachallah", "Communications Officer", "content", "HR & Admin"),
        ]
        employees = {}
        for i, (first, last, position, role, dkey) in enumerate(staff_rows):
            emp, _ = Employee.objects.get_or_create(user=users[role], defaults=dict(
                first_name=first, last_name=last, position=position,
                department=depts[dkey], email=users[role].email,
                gender="F" if i % 2 == 0 else "M",
                hire_date=today - timedelta(days=1200 - i * 60),
                contract_start=today - timedelta(days=800 - i * 40),
                contract_end=today + timedelta(days=500 - i * 25),
                employment_type="full_time", status="active",
                emergency_contact_name="GHDI HR", emergency_contact_phone="+234 800 000 0001",
                salary=1200000 + i * 150000, bank_name="First Bank of GHDI",
                bank_account_number=f"200000000{i:02d}",
                qualifications="B.Sc. Development Studies"))
            employees[role] = emp

        leave_type, _ = LeaveType.objects.get_or_create(name="Annual", defaults={"annual_days": 20})
        LeaveRequest.objects.get_or_create(
            employee=employees["hr"], leave_type=leave_type,
            start_date=today + timedelta(days=10), end_date=today + timedelta(days=15),
            days=6, reason="Family commitment", status="submitted", submitted_by=users["hr"])
        LeaveRequest.objects.get_or_create(
            employee=employees["staff"], leave_type=leave_type,
            start_date=today - timedelta(days=2), end_date=today + timedelta(days=3),
            days=5, reason="Medical leave", status="approved",
            submitted_by=users["staff"], approved_by=users["hr"])
        Vacancy.objects.get_or_create(
            title="Field Officer — Yobe",
            defaults=dict(department=depts["Programs"], location="Damaturu, Yobe", status="open",
                          is_public=True, description="Support GHDI field teams in Yobe State.",
                          closing_date=today + timedelta(days=30), created_by=users["hr"]))
        Training.objects.get_or_create(
            title="Safeguarding Essentials",
            defaults=dict(category="Safeguarding", provider="GHDI Academy", status="planned",
                          start_date=today + timedelta(days=7), end_date=today + timedelta(days=9),
                          location="GHDI Office, Damaturu",
                          description="Introductory safeguarding training.", created_by=users["hr"]))
        # END-SEED-AREA-A

        # ---- Area B: admin superuser + partners ---------------------------
        # The "admin" sample user doubles as the site superuser for /admin/.
        if not users["admin"].is_superuser:
            users["admin"].is_superuser = True
            users["admin"].save(update_fields=["is_superuser"])

        locs = {l.name: l for l in loc_objs}
        log = self.stdout.write

        from apps.partners.models import Donor, Grant, Partner

        donor_rows = [
            ("European Union Humanitarian Aid", "bilateral", "EU Aid Desk", "https://europa.eu"),
            ("UK FCDO", "bilateral", "FCDO Programme Team", "https://www.gov.uk/fcdo"),
            ("UNICEF", "multilateral", "Child Protection Unit", "https://www.unicef.org"),
            ("Open Society Foundations", "foundation", "Grants Manager", "https://www.opensocietyfoundations.org"),
            ("MacArthur Foundation", "foundation", "Program Officer", "https://www.macfound.org"),
            ("Global Fund for Community Foundations", "foundation", "Community Relations", "https://globalfundcommunityfoundations.org"),
            ("GHDI Friends of Damaturu Trust", "individual", "Trust Secretary", ""),
        ]
        donors = {}
        for name, dtype, contact, website in donor_rows:
            donor, _ = Donor.objects.get_or_create(
                name=name,
                defaults={"donor_type": dtype, "contact_name": contact, "website": website,
                          "notes": "Seed donor (fictional) for demonstration."},
            )
            donors[name] = donor

        grant_rows = [
            ("EU Humanitarian Aid for North-East Nigeria", "EU-YOBE-2024", "European Union Humanitarian Aid",
             480_000_000, 400, 400),
            ("FCDO Education in Emergencies", "FCDO-EDU-2024", "UK FCDO", 320_000_000, 300, 500),
            ("UNICEF Child Protection Window", "UNICEF-CP-2025", "UNICEF", 240_000_000, 240, 300),
            ("OSF Resilience Fund", "OSF-RES-2025", "Open Society Foundations", 120_000_000, 180, 420),
            ("MacArthur Climate & Livelihoods", "MAC-LIV-2025", "MacArthur Foundation", 90_000_000, 120, 480),
            ("Friends of Damaturu Community Pool", "FOD-COM-2025", "GHDI Friends of Damaturu Trust",
             30_000_000, 90, 270),
        ]
        grants = {}
        for name, code, donor_name, amount, start_ago, end_ahead in grant_rows:
            grant, _ = Grant.objects.get_or_create(
                code=code,
                defaults={
                    "donor": donors[donor_name], "name": name, "amount": amount,
                    "start_date": today - timedelta(days=start_ago),
                    "end_date": today + timedelta(days=end_ahead),
                    "reporting_frequency": "Quarterly", "next_report_due": today + timedelta(days=30),
                    "description": "Seed grant funding GHDI programmes.", "is_active": True,
                },
            )
            grants[code] = grant

        partner_rows = [
            ("Yobe State Ministry of Humanitarian Affairs", "government", "Permanent Secretary", "Coordination", True),
            ("Borno Yobe Development CBO", "cbo", "Community Chair", "Community Mobilisation", True),
            ("Damaturu Education Quality Network", "cso", "Network Coordinator", "Education Technical", True),
            ("Save the Children International", "ingo", "Area Manager", "Technical Assistance", True),
            ("Mercy Corps", "ingo", "Programme Lead", "Implementation", True),
            ("SISA College of Education", "academic", "Registrar", "Teacher Training", False),
        ]
        partner_objs = []
        for name, ptype, contact, pdesc, on_web in partner_rows:
            partner, _ = Partner.objects.get_or_create(
                name=name,
                defaults={
                    "partner_type": ptype, "contact_person": contact, "state": "Yobe",
                    "geographic_area": "North-East Nigeria", "partnership_type": pdesc,
                    "status": "active", "show_on_website": on_web,
                    "description": "Seed implementation partner.", "created_by": users["pm"],
                },
            )
            partner_objs.append(partner)
        log("  partners seeded")

        # ---- Area C: programmes, projects and activities --------------------
        from apps.programs.models import Activity, Program, Project

        program_rows = [
            ("Protection of Vulnerable Children and Adults", "PRG-PROT", "protection",
             "Strengthen community-based protection and case management for vulnerable groups in Yobe.",
             "EU Humanitarian Aid", 180_000_000, 25000),
            ("Education in Emergencies", "PRG-EDU", "education",
             "Ensure crisis-affected children and youth access safe, quality learning opportunities.",
             "UK FCDO", 150_000_000, 20000),
            ("Community Resilience and Livelihoods", "PRG-RES", "resilience",
             "Build resilient communities through climate-smart livelihoods and social cohesion.",
             "Open Society Foundations", 140_000_000, 22000),
            ("Locally Led Solutions Accelerator", "PRG-LLS", "locally_led",
             "Support local organisations and leaders to design and run humanitarian responses.",
             "Global Fund for Community Foundations", 60_000_000, 12000),
        ]
        programs = {}
        for title, code, area, objective, source, budget, target in program_rows:
            prg, _ = Program.objects.get_or_create(
                code=code,
                defaults={
                    "title": title, "description": objective, "objective": objective,
                    "thematic_area": area, "manager": users["pm"], "funding_source": source,
                    "budget": budget, "target_beneficiaries": target,
                    "start_date": today - timedelta(days=300), "end_date": today + timedelta(days=500),
                    "status": "active", "created_by": users["pm"],
                },
            )
            prg.locations.set(loc_objs[:4])
            programs[code] = prg

        project_rows = [
            ("Community Child Protection Case Management", "PRJ-CP-001", "PRG-PROT", "EU-YOBE-2024",
             "European Union Humanitarian Aid", 62_000_000, 6000, 280),
            ("Schools Reopening and Safe Spaces", "PRJ-EDU-001", "PRG-EDU", "FCDO-EDU-2024",
             "UK FCDO", 78_000_000, 8000, 260),
            ("Emergency Cash for Displaced Families", "PRJ-PROT-002", "PRG-PROT", "UNICEF-CP-2025",
             "UNICEF", 45_000_000, 5000, 240),
            ("Climate-Resilient Farming Support", "PRJ-RES-001", "PRG-RES", "MAC-LIV-2025",
             "MacArthur Foundation", 52_000_000, 7000, 210),
            ("Women's Livelihoods and Savings Groups", "PRJ-RES-002", "PRG-RES", "OSF-RES-2025",
             "Open Society Foundations", 41_000_000, 4500, 190),
            ("Local Partner Capacity Strengthening", "PRJ-LLS-001", "PRG-LLS", "FOD-COM-2025",
             "GHDI Friends of Damaturu Trust", 22_000_000, 3000, 170),
        ]
        projects = {}
        for name, code, prg_code, grant_code, donor_name, budget, target, start_ago in project_rows:
            prj, _ = Project.objects.get_or_create(
                code=code,
                defaults={
                    "program": programs[prg_code], "name": name,
                    "donor": donors[donor_name], "grant": grants[grant_code],
                    "manager": users["pm"], "budget": budget,
                    "objectives": f"Deliver {name} for vulnerable communities in Yobe State.",
                    "outcomes": "Improved protection, learning and resilient livelihoods.",
                    "outputs": "Services delivered to target beneficiaries under the grant agreement.",
                    "stakeholders": "GHDI, community leaders, government line ministries.",
                    "target_beneficiaries": target,
                    "start_date": today - timedelta(days=start_ago),
                    "end_date": today + timedelta(days=420),
                    "status": "active",
                    "submitted_at": timezone.now() - timedelta(days=start_ago),
                    "submitted_by": users["pm"],
                    "approved_at": timezone.now() - timedelta(days=start_ago - 7),
                    "approved_by": users["exec"],
                    "created_by": users["pm"],
                },
            )
            prj.locations.set(loc_objs[:3])
            projects[code] = prj

        activity_rows = [
            # (project code, name, location, expected, actual, status, start_ago, end_offset)
            ("PRJ-CP-001", "Community case management profiling", "Damaturu Central", 450, 412, "completed", 260, -30),
            ("PRJ-CP-001", "Child-friendly space sessions", "Gashua", 300, 318, "completed", 200, -25),
            ("PRJ-CP-001", "Caregiver counselling workshops", "Potiskum", 250, 197, "in_progress", 120, 40),
            ("PRJ-CP-001", "Referral desk setup", "Ngelzarma", 200, 0, "planned", 15, 90),
            ("PRJ-EDU-001", "Teacher training bootcamp", "Damaturu Central", 120, 118, "completed", 240, -20),
            ("PRJ-EDU-001", "Learning materials distribution", "Gashua", 800, 764, "completed", 180, -10),
            ("PRJ-EDU-001", "Back-to-learning campaigns", "Geidam", 500, 431, "in_progress", 100, 35),
            ("PRJ-PROT-002", "Emergency cash transfer cycles", "Goniri", 900, 873, "completed", 150, -15),
            ("PRJ-PROT-002", "Protection desk at host community", "Geidam", 400, 355, "in_progress", 90, 45),
            ("PRJ-RES-001", "Climate-smart demonstration farms", "Ngelzarma", 300, 262, "in_progress", 130, 60),
            ("PRJ-RES-001", "Seeds and tools distribution", "Damaturu Central", 500, 489, "completed", 200, -12),
            ("PRJ-RES-002", "Village savings group formation", "Gashua", 180, 0, "planned", 20, 80),
            ("PRJ-RES-002", "Women's entrepreneurship training", "Potiskum", 160, 143, "in_progress", 110, 30),
            ("PRJ-LLS-001", "Local partner capacity assessment", "Goniri", 60, 54, "completed", 210, -22),
            ("PRJ-LLS-001", "Small grants workshop series", "Gashua", 90, 0, "planned", 25, 70),
        ]
        acts = {}
        for project_code, name, loc_name, expected, actual, status, start_ago, end_offset in activity_rows:
            act, _ = Activity.objects.get_or_create(
                project=projects[project_code], name=name,
                defaults={
                    "description": f"Field activity for {projects[project_code].name}.",
                    "location": locs[loc_name], "responsible": users["staff"],
                    "start_date": today - timedelta(days=start_ago),
                    "end_date": today + timedelta(days=end_offset),
                    "budget": rand_range(8_000_000, 25_000_000),
                    "expected_participants": expected, "actual_participants": actual,
                    "status": status, "notes": "Seed activity record.", "created_by": users["pm"],
                },
            )
            acts[act.name] = act
        log("  programmes seeded")

        # ---- Area D: beneficiaries ------------------------------------------
        from apps.beneficiaries.models import AssistanceRecord, Beneficiary

        ben_rows = [
            # (full_name, gender, age_group, vuln, community, location, disability, household, project, program)
            ("Aisha Abubakar", "F", "adult", "idp", "Gonu Ward", "Goniri", False, 6, "PRJ-PROT-002", "PRG-PROT"),
            ("Bukar Kolomi", "M", "youth", "idp", "Sabon Gari", "Geidam", False, 4, "PRJ-PROT-002", "PRG-PROT"),
            ("Fatima Damagum", "F", "adult", "fhh", "Maiduguri Road", "Damaturu Central", False, 7, "PRJ-PROT-002", "PRG-PROT"),
            ("Ibrahim Grema", "M", "adult", "returnee", "Shagari Lowcost", "Damaturu Central", False, 5, "PRJ-CP-001", "PRG-PROT"),
            ("Hadiza Kyari", "F", "child", "orphan", "Gamboru Ward", "Gashua", False, 3, "PRJ-CP-001", "PRG-PROT"),
            ("Musa Daura", "M", "child", "orphan", "Kasuwa Ward", "Potiskum", False, 2, "PRJ-CP-001", "PRG-PROT"),
            ("Zainab Lawan", "F", "youth", "pwd", "Balle Ward", "Gashua", True, 4, "PRJ-CP-001", "PRG-PROT"),
            ("Umar Abdullahi", "M", "older", "elderly", "Jaji Maji", "Potiskum", False, 3, "PRJ-CP-001", "PRG-PROT"),
            ("Kaltume Sale", "F", "adult", "host", "Ngelzarma", "Ngelzarma", False, 8, "PRJ-EDU-001", "PRG-EDU"),
            ("Adamu Yakubu", "M", "youth", "idp", "Ngelzarma", "Ngelzarma", False, 5, "PRJ-EDU-001", "PRG-EDU"),
            ("Hafsat Babagana", "F", "child", "idp", "Garage Ward", "Geidam", False, 6, "PRJ-EDU-001", "PRG-EDU"),
            ("Tijjani Abba", "M", "child", "returnee", "Karasuwa", "Gashua", False, 4, "PRJ-EDU-001", "PRG-EDU"),
            ("Maryam Gana", "F", "youth", "fhh", "Central Market", "Potiskum", False, 5, "PRJ-EDU-001", "PRG-EDU"),
            ("Bala Maina", "M", "adult", "host", "Goniri", "Goniri", False, 6, "PRJ-EDU-001", "PRG-EDU"),
            ("Ladi Bukar", "F", "adult", "fhh", "Sabuwar Kasuwa", "Geidam", False, 7, "PRJ-RES-001", "PRG-RES"),
            ("Yagana Bello", "F", "youth", "host", "Allajiri", "Ngelzarma", False, 5, "PRJ-RES-001", "PRG-RES"),
            ("Suleiman Gwio", "M", "adult", "returnee", "Gwio", "Ngelzarma", False, 6, "PRJ-RES-001", "PRG-RES"),
            ("Amina Kaku", "F", "child", "orphan", "Kukareta", "Damaturu Central", False, 4, "PRJ-RES-001", "PRG-RES"),
            ("Abubakar Nuhu", "M", "youth", "idp", "Kukareta", "Damaturu Central", False, 3, "PRJ-RES-001", "PRG-RES"),
            ("Hamsatu Mai", "F", "older", "elderly", "Gambir", "Potiskum", False, 2, "PRJ-RES-002", "PRG-RES"),
            ("Nana Shehu", "F", "adult", "fhh", "Biriri", "Gashua", False, 5, "PRJ-RES-002", "PRG-RES"),
            ("Kaka Modu", "F", "youth", "host", "Blangu", "Gashua", False, 4, "PRJ-RES-002", "PRG-RES"),
            ("Ali Baba", "M", "adult", "other", "Kumari", "Geidam", False, 6, "PRJ-RES-002", "PRG-RES"),
            ("Zara Garba", "F", "child", "idp", "Goniri", "Goniri", False, 5, "PRJ-RES-002", "PRG-RES"),
            ("Modu Kime", "M", "youth", "pwd", "Alhaji Jalo", "Potiskum", True, 3, "PRJ-LLS-001", "PRG-LLS"),
            ("Aishatu Sadiq", "F", "adult", "host", "Bogga", "Ngelzarma", False, 6, "PRJ-LLS-001", "PRG-LLS"),
            ("Grema Waziri", "M", "older", "elderly", "Gambir", "Potiskum", False, 4, "PRJ-LLS-001", "PRG-LLS"),
            ("Falmata Daura", "F", "adult", "fhh", "Kasuwa Ward", "Potiskum", False, 7, "PRJ-CP-001", "PRG-PROT"),
            ("Bintu Bukar", "F", "child", "orphan", "Sabon Gari", "Geidam", False, 3, "PRJ-CP-001", "PRG-PROT"),
            ("Yusuf Baba", "M", "adult", "returnee", "Blangu", "Gashua", False, 5, "PRJ-EDU-001", "PRG-EDU"),
            ("Rakiya Ali", "F", "youth", "idp", "Allajiri", "Ngelzarma", False, 4, "PRJ-RES-002", "PRG-RES"),
            ("Bashir Kachallah", "M", "youth", "other", "Alhaji Jalo", "Potiskum", False, 5, "PRJ-LLS-001", "PRG-LLS"),
        ]
        ben_objs = []
        for (full_name, gender, age_group, vuln, community, loc_name, disability,
             household, project_code, program_code) in ben_rows:
            b, _ = Beneficiary.objects.get_or_create(
                full_name=full_name, community=community,
                defaults={
                    "gender": gender, "age_group": age_group,
                    "vulnerability_category": vuln, "location": locs[loc_name],
                    "has_disability": disability, "household_size": household,
                    "project": projects[project_code], "program": programs[program_code],
                    "registration_date": today - timedelta(days=randint(20, 350)),
                    "is_active": True, "notes": "Seed beneficiary record.", "created_by": users["staff"],
                },
            )
            ben_objs.append(b)

        assistance_types = ["cash", "food", "nfi", "shelter", "education", "protection", "training", "health", "wash"]
        for idx, b in enumerate(ben_objs[:24]):
            for a in range(1, 2 + (idx % 3)):
                atype = assistance_types[(idx + a) % len(assistance_types)]
                amount = rand_range(5_000, 40_000) if atype == "cash" else rand_range(500, 3_000)
                AssistanceRecord.objects.get_or_create(
                    beneficiary=b, assistance_type=atype,
                    description=f"{atype.replace('_', ' ').title()} support - seed",
                    defaults={
                        "project": b.project, "date": today - timedelta(days=randint(5, 180)),
                        "value": amount,
                    },
                )
        log("  beneficiaries seeded")

        # ---- Area E: MEAL ----------------------------------------------------
        from apps.monitoring.models import Indicator, IndicatorUpdate, MEALReport

        indicator_rows = [
            ("IND-P1", "Vulnerable children receiving protection services", "PRG-PROT", "PRJ-CP-001",
             0, 15000, 9300, "children", "monthly", "Case management database"),
            ("IND-P2", "Cases closed with safe outcome", "PRG-PROT", "PRJ-CP-001",
             0, 80, 61, "%", "quarterly", "Case closure reviews"),
            ("IND-E1", "Children accessing learning opportunities", "PRG-EDU", "PRJ-EDU-001",
             0, 20000, 11800, "learners", "monthly", "EMIS school returns"),
            ("IND-E2", "Teachers trained with improved practice", "PRG-EDU", "PRJ-EDU-001",
             0, 500, 318, "teachers", "quarterly", "Training registers"),
            ("IND-R1", "Households adopting climate-smart practices", "PRG-RES", "PRJ-RES-001",
             0, 9000, 4200, "households", "monthly", "Field agent registers"),
            ("IND-R2", "Women in active savings groups", "PRG-RES", "PRJ-RES-002",
             0, 4500, 1430, "members", "monthly", "Savings group records"),
            ("IND-L1", "Local partners with strengthened capacity", "PRG-LLS", "PRJ-LLS-001",
             0, 25, 8, "partners", "biannual", "Capacity assessment tools"),
        ]
        indicators = {}
        for code, name, prg_code, proj_code, baseline, target, current, unit, freq, source in indicator_rows:
            ind, _ = Indicator.objects.get_or_create(
                code=code,
                defaults={
                    "name": name, "definition": name,
                    "program": programs[prg_code], "project": projects[proj_code],
                    "baseline": baseline, "target": target, "current": current,
                    "unit": unit, "frequency": freq, "data_source": source,
                    "responsible": users["meal"], "created_by": users["meal"],
                },
            )
            indicators[code] = ind
            for m in range(3, 0, -1):
                period = today.replace(day=1) - timedelta(days=m * 31)
                step_value = max(int(float(current) * (0.5 + (3 - m) * 0.2)), 1)
                IndicatorUpdate.objects.get_or_create(
                    indicator=ind, period=period,
                    defaults={"value": step_value, "notes": "Seed monthly update.",
                              "recorded_by": users["meal"]},
                )

        meal_rows = [
            ("Monthly MEAL Report", "monthly", "PRG-PROT", "PRJ-CP-001", "submitted",
             35, "Programme delivered ahead of schedule this month.",
             "Ach", "challenges text", "Lesson learned text"),
            ("Quarterly MEAL Report", "quarterly", "PRG-EDU", "PRJ-EDU-001", "approved",
             40, "Quarterly achievements summary.", "Achievements", "Challenges", "Lessons"),
            ("Protection Project Baseline Report", "project", "PRG-PROT", "PRJ-CP-001", "under_review",
             25, "Baseline assessment findings for the protection project.",
             "Baseline complete", "Security constraints", "Targeting refinement"),
        ]
        for title, rtype, prg_code, proj_code, status, days_ago, summary, ach, ch, les in meal_rows:
            rep, _ = MEALReport.objects.get_or_create(
                title=title,
                defaults={
                    "report_type": rtype, "program": programs[prg_code],
                    "project": projects[proj_code],
                    "period_start": today - timedelta(days=days_ago),
                    "period_end": today - timedelta(days=days_ago - 30),
                    "summary": summary, "achievements": ach, "challenges": ch, "lessons": les,
                    "status": status, "submitted_at": timezone.now() - timedelta(days=days_ago),
                    "submitted_by": users["meal"], "created_by": users["meal"],
                    "approved_at": timezone.now() - timedelta(days=days_ago - 2) if status == "approved" else None,
                    "approved_by": users["exec"] if status == "approved" else None,
                },
            )
        log("  MEAL seeded")

        # ---- Area F: finance -------------------------------------------------
        from apps.finance.models import (Account, Advance, Budget, BudgetLine,
                                         ExpenseRequest, Transaction)

        account_rows = [
            ("4001", "Donor Grants - Core", "income"), ("4002", "Institutional Funding", "income"),
            ("4003", "Individual Contributions", "income"),
            ("5001", "Staff Costs", "expense"), ("5002", "Travel & Transport", "expense"),
            ("5003", "Activity / Program", "expense"), ("5004", "Equipment", "expense"),
            ("5005", "Rent & Utilities", "expense"), ("5006", "Training", "expense"),
            ("5007", "Administration", "expense"), ("6001", "Cash at Bank", "asset"),
        ]
        accounts = {}
        for code, name, cat in account_rows:
            acc, _ = Account.objects.get_or_create(code=code, defaults={"name": name, "category": cat})
            accounts[code] = acc

        budget_rows = [
            ("Annual Programme Budget", "PRG-PROT", "PRJ-CP-001", "EU-YOBE-2024", "approved",
             [("5001", "Staff Costs", 24_000_000), ("5003", "Activity / Program", 20_000_000),
              ("5002", "Travel & Transport", 6_000_000), ("5005", "Rent & Utilities", 4_000_000)]),
            ("Operations Budget", None, None, "UNICEF-CP-2025", "under_review",
             [("5001", "Staff Costs", 18_000_000), ("5007", "Administration", 6_000_000),
              ("5004", "Equipment", 3_000_000)]),
            ("Resilience Project Budget", "PRG-RES", "PRJ-RES-001", "MAC-LIV-2025", "approved",
             [("5003", "Activity / Program", 22_000_000), ("5006", "Training", 8_000_000),
              ("5002", "Travel & Transport", 5_000_000)]),
        ]
        for name, prg_code, proj_code, grant_code, status, lines in budget_rows:
            budget, _ = Budget.objects.get_or_create(
                name=name, fiscal_year=today.year,
                defaults={
                    "program": programs.get(prg_code), "project": projects.get(proj_code),
                    "donor": (grants[grant_code].donor if grant_code else None),
                    "status": status,
                    "submitted_at": timezone.now() - timedelta(days=25),
                    "submitted_by": users["fin"],
                    "approved_at": timezone.now() - timedelta(days=18) if status == "approved" else None,
                    "approved_by": users["exec"] if status == "approved" else None,
                    "created_by": users["fin"], "notes": "Seed budget.",
                },
            )
            for acc_code, desc, amt in lines:
                BudgetLine.objects.get_or_create(
                    budget=budget, account=accounts[acc_code],
                    defaults={"description": desc, "amount": amt},
                )

        def approved_txn(ref, **kw):
            tx, _ = Transaction.objects.get_or_create(
                reference=ref,
                defaults={
                    "status": Transaction.Status.APPROVED,
                    "submitted_at": timezone.now() - timedelta(days=5),
                    "submitted_by": users["fin"],
                    "approved_at": timezone.now() - timedelta(days=2),
                    "approved_by": users["exec"], **kw,
                },
            )
            return tx

        # Donor income receipts (one per grant, within the current window).
        for code, grant in grants.items():
            approved_txn(
                f"SEED-IN-{code}",
                date=today - timedelta(days=randint(2, 25)),
                description=f"Grant disbursement - {grant.name}",
                account=accounts["4001"], direction="income", donor=grant.donor,
                program=programs["PRG-PROT"], amount=grant.amount, currency="NGN",
                payment_method="bank_transfer",
            )

        # Monthly operating expenses across the last six months (drives trend charts).
        exp_desc = [
            ("Staff salaries - {m}", "5001", "staff", 9_000_000),
            ("Field visit fuel and transport - {m}", "5002", "travel", 1_600_000),
            ("Activity supplies - {m}", "5003", "activity", 2_400_000),
            ("Office rent and utilities - {m}", "5005", "rent", 1_100_000),
            ("Staff training - {m}", "5006", "training", 700_000),
            ("IT and office equipment upkeep - {m}", "5004", "equipment", 850_000),
            ("Administrative running costs - {m}", "5007", "admin", 650_000),
        ]
        serial = 1
        for i in range(6, 0, -1):
            d = today - timedelta(days=i * 30, seconds=1)
            month_label = d.strftime("%b %Y")
            for desc_tpl, acc_code, cat, amount in exp_desc:
                approved_txn(
                    f"SEED-EX-{serial:04d}",
                    date=d, description=desc_tpl.replace("{m}", month_label),
                    account=accounts[acc_code], direction="expense", category=cat,
                    amount=amount, currency="NGN", payment_method="bank_transfer",
                )
                serial += 1
        log("  finance seeded")

        expense_rows = [
            ("Workshop refreshments - caregiver forum", "5003", "PRJ-CP-001", "PRG-PROT",
             250_000, "approved"),
            ("Laptop for monitoring officer", "5004", "PRJ-EDU-001", "PRG-EDU",
             950_000, "submitted"),
            ("Community dialogue venue hire", "5003", "PRJ-RES-002", "PRG-RES",
             180_000, "under_review"),
        ]
        for purpose, acc_code, proj_code, prg_code, amount, status in expense_rows:
            ExpenseRequest.objects.get_or_create(
                purpose=purpose, amount=amount,
                defaults={
                    "requested_by": users["staff"], "account": accounts[acc_code],
                    "program": programs[prg_code], "project": projects[proj_code],
                    "date_needed": today + timedelta(days=7), "payment_method": "bank_transfer",
                    "status": status,
                    "submitted_at": timezone.now() - timedelta(days=3),
                    "submitted_by": users["staff"],
                    "approved_at": timezone.now() - timedelta(days=1) if status == "approved" else None,
                    "approved_by": users["exec"] if status == "approved" else None,
                    "created_by": users["staff"],
                },
            )

        adv_rows = [
            ("Field activity advance", 600_000, 600_000, "Field trips Gashua", "PRJ-CP-001"),
            ("Workshop logistics advance", 300_000, 120_000, "Caregiver workshop", "PRJ-EDU-001"),
        ]
        for purpose, amount, retired, note, proj_code in adv_rows:
            adv, _ = Advance.objects.get_or_create(
                employee=employees["fin"], purpose=purpose, amount=amount, date_issued=today - timedelta(days=20),
                defaults={"retired_amount": retired, "project": projects[proj_code]},
            )
            if retired > 0:
                from apps.finance.models import AdvanceRetirement

                AdvanceRetirement.objects.get_or_create(
                    advance=adv, amount=retired,
                    defaults={"date": today - timedelta(days=3),
                              "note": note, "recorded_by": users["fin"]},
                )

        from apps.finance.models import BankReconciliation

        BankReconciliation.objects.get_or_create(
            account_name="GHDI First Bank - Operations", period_end=today - timedelta(days=30),
            defaults={"book_balance": 12_400_000, "bank_balance": 12_450_000,
                      "notes": "Seed reconciliation; small timing difference cleared on 1st of month.",
                      "reconciled_by": users["fin"]},
        )

        # ---- Area G: procurement, assets, documents ---------------------------
        from apps.procurement.models import (ProcurementRequest, PurchaseOrder,
                                             Quotation, Vendor)

        vendor_rows = [
            ("Damaturu Stationery Hub", "Musa Ali", "Stationery", 4),
            ("Yobe Office Furniture Ltd", "Khadija Sule", "Furniture", 5),
            ("North-East IT Solutions", "Ibrahim Gana", "IT", 4),
            ("Gashua Logistics Services", "Bello Audu", "Logistics", 3),
            ("Abuja Agro Seeds & Tools", "Nafisa Bala", "Agriculture", 5),
        ]
        vendors = {}
        for name, contact, cat, rating in vendor_rows:
            v, _ = Vendor.objects.get_or_create(
                name=name,
                defaults={"contact_person": contact, "phone": "+234 800 000 00" + str(rating),
                          "email": name.lower().split()[0] + "@ghdi.local",
                          "address": "Damaturu, Yobe State", "category": cat, "rating": rating},
            )
            vendors[name] = v

        pr_rows = [
            ("Office furniture for Damaturu office", "PRJ-LLS-001", 12, 3_500_000, "approved", "high",
             "Yobe Office Furniture Ltd"),
            ("Laptops for field teams", "PRJ-EDU-001", 8, 7_600_000, "under_review", "medium", None),
            ("Seed packs - batch 2", "PRJ-RES-001", 500, 9_000_000, "submitted", "medium", None),
        ]
        pr_objs = {}
        for title, proj_code, qty, cost, status, priority, selected in pr_rows:
            pr, _ = ProcurementRequest.objects.get_or_create(
                title=title,
                defaults={
                    "description": f"Covers {title.lower()}.",
                    "requested_by": users["proc"], "project": projects[proj_code],
                    "quantity": qty, "estimated_cost": cost, "needed_by": today + timedelta(days=21),
                    "priority": priority, "status": status,
                    "submitted_at": timezone.now() - timedelta(days=8),
                    "submitted_by": users["proc"],
                    "approved_at": timezone.now() - timedelta(days=4) if status == "approved" else None,
                    "approved_by": users["exec"] if status == "approved" else None,
                    "selected_vendor": vendors[selected] if selected else None,
                    "created_by": users["proc"],
                },
            )
            pr_objs[title] = pr

        quote_rows = [
            ("Office furniture for Damaturu office", "Yobe Office Furniture Ltd", 3_420_000, True),
            ("Office furniture for Damaturu office", "Damaturu Stationery Hub", 3_610_000, False),
            ("Office furniture for Damaturu office", "Abuja Agro Seeds & Tools", 3_750_000, False),
        ]
        for req_title, vendor_name, amount, selected in quote_rows:
            Quotation.objects.get_or_create(
                request=pr_objs[req_title], vendor=vendors[vendor_name],
                defaults={"amount": amount, "is_selected": selected,
                          "notes": "Seed quotation."},
            )

        po, _ = PurchaseOrder.objects.get_or_create(
            request=pr_objs["Office furniture for Damaturu office"],
            vendor=vendors["Yobe Office Furniture Ltd"], amount=3_420_000,
            defaults={"expected_delivery": today + timedelta(days=14),
                      "status": "open", "notes": "Seed purchase order."},
        )
        log("  procurement seeded")

        from apps.assets.models import Asset, AssetAssignment

        asset_rows = [
            ("Toyota Hilux Field Vehicle", "vehicle", "VHL-27-001", "Gashua", "exec", 18_500_000, "good"),
            ("HP EliteBook Laptop", "it", "ITD-1001", "Damaturu Central", "fin", 950_000, "good"),
            ("HP EliteBook Laptop", "it", "ITD-1002", "Potiskum", "pm", 950_000, "good"),
            ("Dell Latitude Laptop", "it", "ITD-1003", "Damaturu Central", "meal", 920_000, "fair"),
            ("Canon Photocopier", "office", "OFC-2001", "Damaturu Central", "hr", 1_400_000, "good"),
            ("Yamaha Generator 7.5kVA", "office", "OFC-2002", "Ngelzarma", "staff", 2_100_000, "fair"),
        ]
        for name, cat, serial, loc_name, emp_role, value, cond in asset_rows:
            asset, created = Asset.objects.get_or_create(
                name=name, serial_number=serial,
                defaults={
                    "category": cat, "purchase_date": today - timedelta(days=400),
                    "purchase_value": value, "current_value": value * 0.8,
                    "location": locs[loc_name], "assigned_to": employees[emp_role],
                    "condition": cond, "status": "in_use", "created_by": users["admin"],
                },
            )
            if created:
                AssetAssignment.objects.create(
                    asset=asset, employee=employees[emp_role],
                    condition_out=cond, notes="Seed assignment.", recorded_by=users["admin"],
                )
        log("  assets seeded")

        from apps.documents.models import Document, DocumentCategory

        def save_private_placeholder(document, filename):
            from django.core.files.base import ContentFile

            document.file.save(
                filename,
                ContentFile(b"GHDI seed placeholder file.\n"),
                save=False,
            )
            document.save(update_fields=["file"])

        doc_cats = {}
        for name, slug in [("Policies", "policies"), ("Financial", "financial"),
                           ("HR", "hr"), ("Reports", "reports")]:
            cat, _ = DocumentCategory.objects.get_or_create(
                name=name, defaults={"slug": slug, "description": f"Seed {name.lower()} documents."})
            doc_cats[name] = cat

        doc_rows = [
            ("GHDI HR Policy Handbook", "Policies", "staff", "hr,policy,handbook", 180),
            ("Child Safeguarding Policy", "Policies", "staff", "safeguarding,child", 240),
            ("Finance Manual", "Financial", "staff", "finance,manual", 120),
            ("Procurement Policy", "Financial", "staff", "procurement,policy", 90),
            ("Quarterly MEAL Report", "Reports", "restricted", "meal,report", 30),
        ]
        for title, cat_name, access, tags, expiry in doc_rows:
            doc, created = Document.objects.get_or_create(
                title=title,
                defaults={
                    "description": "Seed document placeholder.",
                    "category": doc_cats[cat_name], "owner": users["staff"],
                    "access_level": access, "tags": tags,
                    "expires_at": today + timedelta(days=expiry),
                    "created_by": users["staff"],
                },
            )
            if created:
                save_private_placeholder(doc, f"{title.replace(' ', '-')}.txt")
        log("  documents seeded")

        # ---- Area H: collaboration, communications, risk ----------------------
        from apps.collaboration.models import ActionPoint, Meeting, Task

        task_rows = [
            ("Draft Q2 beneficiary report", "meal", "high", 7, "in_progress", "PRJ-CP-001", "PRG-PROT"),
            ("Coordinate field monitoring visits", "staff", "medium", 5, "todo", "PRJ-EDU-001", "PRG-EDU"),
            ("Prepare procurement evaluation notes", "proc", "medium", 3, "in_progress", "PRJ-RES-001", "PRG-RES"),
            ("Update risk register", "pm", "high", 10, "todo", None, "PRG-PROT"),
            ("Renew vehicle insurance", "fin", "low", 14, "todo", None, None),
        ]
        for title, role, priority, due, status, proj_code, prg_code in task_rows:
            Task.objects.get_or_create(
                title=title, assigned_to=users[role],
                defaults={
                    "priority": priority, "due_date": today + timedelta(days=due),
                    "status": status, "project": projects.get(proj_code),
                    "program": programs.get(prg_code), "created_by": users["pm"],
                },
            )

        meeting, _ = Meeting.objects.get_or_create(
            title="Monthly Programme Coordination Meeting",
            defaults={
                "date": today - timedelta(days=4), "start_time": "10:00", "end_time": "12:00",
                "location": "GHDI Conference Room", "organizer": users["pm"],
                "agenda": "Programme updates, finance status, MEAL findings, risks.",
                "minutes": "Agreed to expedite field monitoring and resolve procurement delays.",
                "decisions": "Approve subcontract for learning materials; escalate protection desk staffing.",
                "status": "held", "created_by": users["pm"],
            },
        )
        meeting.participants.set([users["pm"], users["fin"], users["meal"], users["proc"]])
        ActionPoint.objects.get_or_create(
            meeting=meeting, description="Share draft Q2 report by Friday",
            defaults={"assignee": users["meal"], "due_date": today + timedelta(days=2), "is_done": False},
        )
        ActionPoint.objects.get_or_create(
            meeting=meeting, description="Confirm vendor delivery schedule",
            defaults={"assignee": users["proc"], "due_date": today + timedelta(days=4), "is_done": False},
        )
        ActionPoint.objects.get_or_create(
            meeting=meeting, description="Circulate budget utilisation summary",
            defaults={"assignee": users["fin"], "due_date": today + timedelta(days=1), "is_done": True},
        )
        log("  collaboration seeded")

        from apps.communications.models import Announcement, InternalMessage

        Announcement.objects.get_or_create(
            title="Welcome to the new GHDI Information System",
            defaults={
                "body": "Staff can now view dashboards, approve workflows and manage records from /app/. "
                        "Please familiarise yourselves with the modules relevant to your role.",
                "audience": "all", "status": "published", "is_pinned": True,
                "publish_at": today - timedelta(days=2), "created_by": users["admin"],
            },
        )
        Announcement.objects.get_or_create(
            title="Security reminder - lock your workstations",
            defaults={
                "body": "Always lock your workstation when away from your desk. Report security "
                        "incidents via the Risk module.",
                "audience": "all", "status": "published", "is_pinned": False,
                "publish_at": today - timedelta(days=10), "created_by": users["hr"],
            },
        )

        msg_rows = [
            (users["exec"], users["fin"], "Budget approval complete",
             "The programme budget has been approved. Please proceed with the planned activities."),
            (users["hr"], users["staff"], "Leave request approved",
             "Your medical leave has been approved. Kindly confirm the return date."),
            (users["meal"], users["pm"], "Indicator update due",
             "Please flag any gaps before the end-of-month indicator refresh."),
        ]
        for sender, recipient, subject, body in msg_rows:
            InternalMessage.objects.get_or_create(
                sender=sender, recipient=recipient, subject=subject, defaults={"body": body},
            )
        log("  communications seeded")

        from apps.risk.models import Incident, Risk

        risk_rows = [
            ("Delay in donor disbursements", "financial", 4, 4, "mitigating",
             "Maintain a six-week cash buffer and quarterly disbursement tracking."),
            ("Security deterioration in Geidam", "security", 3, 5, "escalated",
             "Restrict field movements; adopt convoy protocol and daily security checks."),
            ("Children dropping out of education programmes", "programmatic", 4, 3, "open",
             "Strengthen community engagement and referral to case management."),
            ("Fraud in cash transfers", "fraud", 2, 5, "mitigating",
             "Biometric verification and post-distribution monitoring audits."),
            ("High staff turnover", "hr", 3, 3, "open",
             "Review compensation, retention incentives and staff welfare packages."),
        ]
        for title, cat, prob, impact, status, mitigation in risk_rows:
            Risk.objects.get_or_create(
                title=title,
                defaults={
                    "category": cat, "probability": prob, "impact": impact,
                    "mitigation": mitigation, "responsible": users["pm"],
                    "review_date": today + timedelta(days=14), "status": status,
                    "created_by": users["pm"],
                },
            )

        Incident.objects.get_or_create(
            title="Lost GHDI field laptop",
            defaults={
                "category": "it", "date": today - timedelta(days=12), "location": "Potiskum",
                "description": "A field laptop was reported missing after a community session.",
                "severity": "medium", "reported_by": users["staff"], "assigned_to": users["admin"],
                "actions_taken": "Remote wipe initiated; incident logged for asset recovery.",
                "status": "investigating", "follow_up_date": today + timedelta(days=7),
                "created_by": users["staff"],
            },
        )
        Incident.objects.get_or_create(
            title="Road accident on Gashua field route",
            defaults={
                "category": "safety", "date": today - timedelta(days=30), "location": "Gashua",
                "description": "Minor road accident involving the project vehicle; no injuries.",
                "severity": "low", "reported_by": users["staff"], "assigned_to": users["admin"],
                "actions_taken": "Vehicle sent for inspection; driver debriefed on road safety.",
                "status": "resolved", "follow_up_date": today - timedelta(days=5),
                "created_by": users["staff"],
            },
        )
        log("  risk seeded")

        # ---- Area I: CMS / public website content -----------------------------
        from apps.cms.models import Event, ImpactStat, NewsArticle, Page, PageSection, TeamMember

        pages_rows = [
            ("About Us", "about-us", "standard", True, 1,
             "The Garkuwa Humanitarian and Development Initiative (GHDI) is a Nigerian NGO "
             "working to protect, educate and empower vulnerable communities in Yobe State."),
            ("Governance", "governance", "governance", True, 2,
             "GHDI is governed by a Board of Trustees and an Executive Director, supported by "
             "professional management."),
            ("Protection", "protection", "thematic", False, 3,
             "Protecting children, women and adults at risk through community-based case management."),
            ("Transparency & Accountability", "transparency-accountability", "legal", False, 4,
             "GHDI commitments to transparency and accountability."),
            ("Privacy Policy", "privacy-policy", "legal", False, 5,
             "How GHDI handles personal data."),
            ("Terms of Use", "terms-of-use", "legal", False, 6,
             "Terms governing use of this website."),
        ]
        for title, slug, ptype, show_nav, order, summary in pages_rows:
            page, _ = Page.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title, "page_type": ptype, "summary": summary,
                    "status": "published", "publish_at": timezone.now() - timedelta(days=30),
                    "author": users["content"], "is_featured": slug == "about-us",
                    "show_in_nav": show_nav, "nav_order": order,
                    "seo_title": title, "seo_description": summary[:160],
                    "created_by": users["content"],
                },
            )
            if slug == "protection":
                for i, (heading, body) in enumerate([
                    ("Why Protection Matters", "Every person has the right to safety and dignity.\n\n"
                     "In Yobe State, conflict and displacement expose children, women and persons "
                     "with disabilities to heightened risk."),
                    ("Our Approach", "We support community-based child protection networks, "
                     "case management, psychosocial support and referral to essential services."),
                    ("Working Together", "We work with government ministries, community leaders "
                     "and local organisations to strengthen protective environments."),
                    ("Donate", "Support our protection work by partnering with us or "
                     "contacting our field team."),
                ]):
                    PageSection.objects.get_or_create(
                        page=page, heading=heading,
                        defaults={"body": body, "sort_order": i},
                    )

        news_rows = [
            ("GHDI Reaches 9,000 Children with Learning Support", "news", True,
             "A new milestone in education support across Yobe's host and displacement communities. "
             "Teachers trained and learning materials distributed across Damaturu, Gashua and Potiskum."),
            ("Child Protection Case Management Expands to Three LGAs", "news", False,
             "Community case workers are now identifying and supporting vulnerable children in more "
             "locations with referrals to health, education and legal services."),
            ("Emergency Cash Reaches Displaced Families in Geidam", "news", False,
             "Over 800 households received multipurpose cash assistance, improving food security and "
             "reducing negative coping."),
            ("From Displacement to the Classroom: Halima's Story", "story", True,
             "After months out of school, Halima returned to learning through GHDI's back-to-learning "
             "campaign and now dreams of becoming a teacher."),
            ("Women Save Together: Savings Groups Take Root in Gashua", "story", False,
             "Village savings groups are helping women build resilient livelihoods and mutual support "
             "networks."),
            ("A Community-Led Response to Floods in Ngelzarma", "story", False,
             "Local volunteers and GHDI field teams worked side by side to respond after heavy rains "
             "flooded homes and farmlands."),
        ]
        from django.utils.text import slugify

        for title, cat, featured, summary in news_rows:
            article, _ = NewsArticle.objects.get_or_create(
                slug=slugify(title),
                defaults={
                    "category": cat, "summary": summary, "content": summary + "\n\n"
                    "Delivered in partnership with community structures and government authorities, "
                    "this intervention is part of GHDI's wider programme of work in Yobe State. "
                    "Every beneficiary is reached with dignity, and safeguarding measures are applied "
                    "throughout.",
                    "author": users["content"], "publish_at": timezone.now() - timedelta(days=randint(1, 25)),
                    "tags": "seed,ghdi", "status": "published", "is_featured": featured,
                    "seo_title": title, "created_by": users["content"],
                },
            )
            if featured:
                article.is_featured = True
                article.save(update_fields=["is_featured"])

        event_rows = [
            ("Community Dialogue on Child Protection", "community-dialogue-protection", "upcoming",
             True, 12, "GHDI Training Hall", "9:00", "13:00"),
            ("Education Stakeholders Forum", "stakeholders-forum-2026", "upcoming",
             False, 28, "Damaturu Federal College Hall", "10:00", "14:00"),
            ("Annual General Meeting & Open Day", "agm-open-day-2026", "upcoming",
             True, 45, "GHDI Office Premises", "10:00", "15:00"),
            ("Women's Livelihoods Exhibition", "women-livelihoods-exhibition", "completed",
             False, -12, "Potiskum Market Square", "11:00", "16:00"),
            ("Flood Response Volunteer Training", "flood-response-training", "completed",
             True, -40, "Ngelzarma Community Hall", "9:00", "13:00"),
        ]
        for name, slug, status, featured, day_offset, venue, start, end in event_rows:
            Event.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name, "status": status, "is_featured": featured,
                    "date": today + timedelta(days=day_offset), "venue": venue, "city": "Damaturu",
                    "start_time": start, "end_time": end, "organizer": "GHDI",
                    "description": f"Public {name.lower()} organised by GHDI.",
                },
            )

        stat_rows = [
            ("Lives Reached", 120000, "+", "users", 1),
            ("Communities Reached", 280, "", "map-pin", 2),
            ("Children in Learning", 11800, "+", "book-open", 3),
            ("Projects Delivered", 45, "", "briefcase", 4),
            ("Partners Engaged", 36, "", "handshake", 5),
            ("Years of Service", 12, "+", "award", 6),
        ]
        for label, value, suffix, icon, order in stat_rows:
            ImpactStat.objects.get_or_create(
                label=label, defaults={"value": value, "suffix": suffix, "icon": icon,
                                       "order": order, "is_active": True},
            )

        team_rows = [
            ("Dr. Aishatu Garkuwa", "Executive Director", "leadership", 1),
            ("Alhaji Modu Wakil", "Chair, Board of Trustees", "board", 2),
            ("Hajiya Binta Mala", "Vice Chair, Board of Trustees", "board", 3),
            ("Ibrahim Usman", "Director of Programs", "management", 4),
            ("Fatima Bello", "Head of HR & Administration", "management", 5),
            ("Saidu Adamu", "Head of Finance", "management", 6),
        ]
        for name, role, cat, order in team_rows:
            TeamMember.objects.get_or_create(
                name=name, role=role,
                defaults={"category": cat, "order": order,
                          "bio": f"{role} contributing to GHDI's mission in Yobe State."},
            )

        # Link implementation partners to programmes.
        for partner in partner_objs:
            partner.programs.set(list(programs.values())[:2])
            partner.projects.set(list(projects.values())[:2])
        log("  website content seeded")
