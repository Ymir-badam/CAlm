from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

SUBSCRIPTION_CHOICES = [
    ("free", "Free"),
    ("pro", "Pro"),
    ("enterprise", "Enterprise"),
]

STREAM_CHOICES = [
    ("CA", "CA (Chartered Accountancy)"),
    ("CLAT", "CLAT (Common Law Admission Test)"),
]
DESIGNATION_CHOICES = [
    ("Foundation", "Foundation"),
    ("Intermediate", "Intermediate"),
    ("Articleship", "Articleship"),
]



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credits_balance = models.FloatField(default=10000)
    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default="free"
    )
    total_tokens_used = models.IntegerField(default=0)
    
    # New fields
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        null=True,
        blank=True
    )
    stream = models.CharField(
        max_length=10,
        choices=STREAM_CHOICES,
        null=True,
        blank=True
    )
    designation=models.CharField(
        max_length=50,
        choices=DESIGNATION_CHOICES,
        default="Foundation",
        null=True,
        blank=True
    )
    education=models.CharField(max_length=100,null=True,blank=True)

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True
    )
    financial_reporting=models.FloatField(default=0)
    financial_reporting_count=models.IntegerField(default=0)


    direct_taxation=models.FloatField(default=0)
    direct_taxation_count=models.IntegerField(default=0)

    gst_and_indirect_tax=models.FloatField(default=0)
    gst_and_indirect_tax_count=models.IntegerField(default=0)

    audit_and_assurance=models.FloatField(default=0)
    audit_and_assurance_count=models.IntegerField(default=0)


    coporate_law=models.FloatField(default=0)
    coporate_law_count=models.IntegerField(default=0)


    financial_management=models.FloatField(default=0)
    financial_management_count=models.IntegerField(default=0)


    ethics_and_prof=models.FloatField(default=0)
    ethics_and_prof_count=models.IntegerField(default=0)




    def __str__(self):
        return self.user.username
SKILL_TYPES=[
    ("financial_reporting", "Financial Reporting"),
    ("direct_taxation",   "Direct Taxatation"),
    ("gst_and_indirect_tax",    "Gst and Indirect Tax"),
    ("audit_and_assurance",      "Audit and Assurance"),
    ("coporate_law",      "Corporate Law"),
    ("cost_accounting",      "Cost Accounting"),
    ("financial_management",      "Financial Management"),
    ("ethics_and_prof",      "Ethics and Prof"),
]
from django.db import models
from django.contrib.auth.models import User

ACTIVITY_TYPES = [
    ("question_solved", "Question Solved"),
    ("study_session",   "Study Session"),
    ("note_created",    "Note Created"),
    ("quiz_taken",      "Quiz Taken"),
]


class UserActivity(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    date          = models.DateField()                        # date of the activity (not datetime)
    count         = models.PositiveIntegerField(default=1)    # how many times on that day
    metadata      = models.JSONField(default=dict, blank=True) # e.g. {"topic": "Tax", "score": 80}
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "activity_type", "date")   # one row per user/type/day
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.user.username} — {self.activity_type} on {self.date}"


class DailyActivitySummary(models.Model):
    """Denormalized daily rollup for fast heatmap queries."""
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_summaries")
    date        = models.DateField()
    total_count = models.PositiveIntegerField(default=0)      

    class Meta:
        unique_together = ("user", "date")
        indexes = [models.Index(fields=["user", "date"])] 
# models.py
class CaseActivityLog(models.Model):
    CATEGORY_CHOICES = [
        ("study",       "Study Session"),
        ("case_note",   "Case Note"),
        ("revision",    "Revision"),
        ("mock_test",   "Mock Test"),
        ("research",    "Research"),
        ("other",       "Other"),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="case_logs")
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="study")
    tags        = models.CharField(max_length=200, blank=True)  # comma-separated
    is_pinned   = models.BooleanField(default=False)
    date        = models.DateField(default=timezone.now)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-date", "-created_at"]

    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]
    

# class SkillLog(models.Model):
#     user= models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_logs")