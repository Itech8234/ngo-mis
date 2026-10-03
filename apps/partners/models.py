"""Donor and partner management."""
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel


class Donor(models.Model):
    """Funding partner (grant maker)."""

    class DonorType(models.TextChoices):
        BILATERAL = "bilateral", "Bilateral"
        MULTILATERAL = "multilateral", "Multilateral"
        FOUNDATION = "foundation", "Foundation"
        INGO = "ingo", "International NGO"
        GOVERNMENT = "government", "Government"
        CORPORATE = "corporate", "Corporate"
        INDIVIDUAL = "individual", "Individual"

    name = models.CharField(max_length=200, unique=True)
    donor_type = models.CharField(max_length=15, choices=DonorType.choices, db_index=True)
    contact_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    @property
    def total_funding(self):
        return sum(g.amount for g in self.grants.all())

    @property
    def funds_received(self):
        from apps.finance.models import Transaction

        total = Transaction.objects.filter(donor=self, direction=Transaction.Direction.INCOME).aggregate(t=models.Sum("amount"))["t"]
        return total or 0

    @property
    def funds_spent(self):
        from apps.finance.models import Transaction

        total = Transaction.objects.filter(donor=self, direction=Transaction.Direction.EXPENSE).aggregate(t=models.Sum("amount"))["t"]
        return total or 0

    def get_absolute_url(self):
        return reverse("partners:donor_detail", args=[self.pk])

    def __str__(self):
        return self.name


class Grant(models.Model):
    """A funding agreement with a donor, funding programs and projects."""

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="grants")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="NGN")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    reporting_frequency = models.CharField(max_length=40, blank=True, default="Quarterly")
    next_report_due = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    @property
    def utilisation(self):
        if not self.amount:
            return 0
        projects = self.projects.all()
        spent = sum(p.spent for p in projects)
        return min(100.0, float(spent) / float(self.amount) * 100)

    def get_absolute_url(self):
        return reverse("partners:grant_detail", args=[self.pk])

    def __str__(self):
        return f"{self.name} ({self.code})"


class Partner(OwnedModel):
    """Implementation / coordination partner (govt, NGO, CSO, CBO, private)."""

    class PartnerType(models.TextChoices):
        GOVERNMENT = "government", "Government Agency"
        NGO = "ngo", "National NGO"
        CSO = "cso", "Civil Society Organisation"
        CBO = "cbo", "Community Organisation"
        INGO = "ingo", "International Organisation"
        PRIVATE = "private", "Private Sector"
        ACADEMIC = "academic", "Academic Institution"

    class Status(models.TextChoices):
        PROSPECT = "prospect", "Prospective"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    name = models.CharField(max_length=200, unique=True)
    partner_type = models.CharField(max_length=15, choices=PartnerType.choices, db_index=True)
    contact_person = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=60, default="Yobe")
    geographic_area = models.CharField(max_length=200, blank=True)
    partnership_type = models.CharField(max_length=160, blank=True, help_text="e.g. Implementation, Technical Assistance")
    programs = models.ManyToManyField("programs.Program", blank=True, related_name="partners")
    projects = models.ManyToManyField("programs.Project", blank=True, related_name="partners")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    show_on_website = models.BooleanField(default=False, help_text="Display on the public partners page")
    logo = models.ImageField(upload_to="partners/", blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def get_absolute_url(self):
        return reverse("partners:partner_detail", args=[self.pk])

    @property
    def is_cms_partner(self):
        return True

    def __str__(self):
        return self.name

