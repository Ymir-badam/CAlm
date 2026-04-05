# services/activity_tracker.py
from django.utils import timezone
from .models import UserActivity, DailyActivitySummary

def record_activity(user, activity_type: str, metadata: dict = None):
    """
    Call this wherever an action happensa
    e.g. record_activity(request.user, "question_solved", {"topic": "Tax"})
    """
    today = timezone.localdate()

    obj, created = UserActivity.objects.get_or_create(
        user=user,
        activity_type=activity_type,
        date=today,
        defaults={"count": 1, "metadata": metadata or {}},
    )
    if not created:
        obj.count += 1
        if metadata:
            obj.metadata.update(metadata)
        obj.save(update_fields=["count", "metadata"])

    # update daily rollup
    summary, _ = DailyActivitySummary.objects.get_or_create(user=user, date=today)
    summary.total_count = (
        UserActivity.objects
        .filter(user=user, date=today)
        .aggregate(total=models.Sum("count"))["total"] or 0
    )
    summary.save(update_fields=["total_count"])