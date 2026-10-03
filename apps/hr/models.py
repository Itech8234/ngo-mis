"""HR module models: departments, employees, leave, recruitment, training."""
from datetime import date
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import OwnedModel, WorkflowMixin
from apps.core.validators import FileSizeValidator, FileTypeValidator
from .storage import PrivateHRStorage


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    head = models.ForeignKey("Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="led_departments")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Employee(OwnedModel):
    """Complete employee profile. Sensitive fields require hr.view_sensitive."""

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERN = "intern", "Intern"
        VOLUNTEER = "volunteer", "Volunteer"
        CONSULTANT = "consultant", "Consultant"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On Leave"
        SUSPENDED = "suspended", "Suspended"
        EXITED = "exited", "Exited"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee_profile")
    employee_id = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    photo = models.ImageField(upload_to="employees/", blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=120)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="employees")
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff")
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    hire_date = models.DateField(null=True, blank=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True, db_index=True)
    # Sensitive HR information
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    # Profile
    qualifications = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    previous_experience = models.TextField(blank=True)
    job_description = models.TextField(blank=True)
    supervisor = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="direct_reports")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ("first_name", "last_name")
        permissions = [("view_sensitive", "Can view sensitive HR information (salary, bank details)")]

    def save(self, *args, **kwargs):
        if not self.employee_id:
            prefix = "GHDI-EMP-"
            last = Employee.objects.order_by("-pk").first()
            next_num = (int(last.employee_id.split("-")[-1]) + 1) if last and last.employee_id.startswith(prefix) else 1
            self.employee_id = f"{prefix}{next_num:04d}"
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def contract_expiring(self):
        return bool(self.contract_end) and self.contract_end <= timezone.localdate() + timezone.timedelta(days=60)

    def get_absolute_url(self):
        return reverse("hr:employee_detail", args=[self.pk])

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"


class LeaveType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    annual_days = models.PositiveSmallIntegerField(default=20)
    is_paid = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    """Per-employee annual entitlement and HR-approved carry-forward."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveSmallIntegerField(default=timezone.localdate().year, db_index=True)
    entitled_days = models.PositiveSmallIntegerField(default=0)
    carry_forward_days = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("employee__last_name", "leave_type__name", "year")
        constraints = [models.UniqueConstraint(fields=("employee", "leave_type", "year"), name="hr_unique_employee_leave_year")]

    @property
    def days_used(self):
        total = 0
        for request in self.employee.leave_requests.filter(
            leave_type=self.leave_type,
            status__in=("approved", "completed"),
            start_date__lte=date(self.year, 12, 31),
            end_date__gte=date(self.year, 1, 1),
        ).only("start_date", "end_date"):
            start = max(request.start_date, date(self.year, 1, 1))
            end = min(request.end_date, date(self.year, 12, 31))
            total += (end - start).days + 1
        return total

    @property
    def days_remaining(self):
        return self.entitled_days + self.carry_forward_days - self.days_used

    def __str__(self):
        return f"{self.employee.full_name} — {self.leave_type.name} ({self.year})"


class HRDocument(OwnedModel):
    """Private employee file; stored outside MEDIA_ROOT and download-gated."""

    class DocumentType(models.TextChoices):
        CONTRACT = "contract", "Employment Contract"
        IDENTIFICATION = "identification", "Identity Document"
        CERTIFICATE = "certificate", "Certificate / Qualification"
        CV = "cv", "CV / Resume"
        PAYSLIP = "payslip", "Payslip"
        OTHER = "other", "Other"

    class Verification(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="hr_documents")
    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER, db_index=True)
    file = models.FileField(
        upload_to="employees/documents/%Y/%m/", storage=PrivateHRStorage(),
        validators=[FileSizeValidator(), FileTypeValidator({"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"})],
    )
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    verification = models.CharField(max_length=10, choices=Verification.choices, default=Verification.PENDING, db_index=True)
    is_confidential = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="uploaded_hr_documents")

    class Meta:
        ordering = ("-created_at",)
        permissions = [("view_sensitive_hrdocument", "Can view confidential HR documents")]

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.localdate())

    def __str__(self):
        return f"{self.employee.full_name}: {self.title}"


class LeaveRequest(WorkflowMixin, OwnedModel):
    """Leave request: employee -> supervisor -> HR -> (final) authorised approver."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveSmallIntegerField(default=0)
    reason = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="leave/", blank=True, storage=PrivateHRStorage(),
        validators=[FileSizeValidator(), FileTypeValidator({"pdf", "jpg", "jpeg", "png"})],
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leave_to_review"
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        permissions = [("approve_leave", "Can approve/reject leave requests")]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Leave end date cannot be before the start date.")

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.days = max((self.end_date - self.start_date).days + 1, 0)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("hr:leave_detail", args=[self.pk])

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.days}d)"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        REMOTE = "remote", "Remote"
        LEAVE = "leave", "On Leave"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.localdate, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PRESENT)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-date",)
        unique_together = ("employee", "date")
        permissions = [("clock_attendance", "Can clock in and out for own attendance")]

    def clean(self):
        if self.check_in and self.check_out and self.check_out < self.check_in:
            raise ValidationError({"check_out": "Check-out must be later than check-in for the same workday."})

    def __str__(self):
        return f"{self.employee.full_name} {self.date} {self.status}"


class TimesheetEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="timesheets")
    date = models.DateField(default=timezone.localdate)
    hours = models.DecimalField(max_digits=4, decimal_places=1, default=8)
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="timesheets")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-date",)

    def __str__(self):
        return f"{self.employee.full_name} {self.date} ({self.hours}h)"


class Vacancy(OwnedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        FILLED = "filled", "Filled"

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(max_length=20, choices=Employee.EmploymentType.choices, default=Employee.EmploymentType.FULL_TIME)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    closing_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)
    is_public = models.BooleanField(default=True, help_text="Show on the public careers page")

    class Meta:
        ordering = ("-created_at",)

    def get_absolute_url(self):
        return reverse("hr:vacancy_detail", args=[self.pk])

    def __str__(self):
        return self.title


class JobApplication(OwnedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="applications")
    full_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    cover_letter = models.TextField(blank=True)
    cv = models.FileField(
        upload_to="applications/",
        validators=[FileSizeValidator(), FileTypeValidator({"pdf", "doc", "docx"})],
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.NEW, db_index=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.full_name} -> {self.vacancy.title}"


class Training(OwnedModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    provider = models.CharField(max_length=160, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    participants = models.ManyToManyField(Employee, blank=True, related_name="trainings")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)

    class Meta:
        ordering = ("-start_date",)

    def get_absolute_url(self):
        return reverse("hr:training_detail", args=[self.pk])

    def __str__(self):
        return self.title


class PerformanceReview(OwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        COMPLETED = "completed", "Completed"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="performance_reviews")
    period = models.CharField(max_length=40)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    goals = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1 (poor) - 5 (outstanding)")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.employee.full_name} - {self.period}"


class DisciplinaryRecord(OwnedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="disciplinary_records")
    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=80)
    description = models.TextField()
    action_taken = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ("-date",)

    def __str__(self):
        return f"{self.employee.full_name} - {self.category}"


