from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
import json

from .models import CaseActivityLog, UserActivity, DailyActivitySummary

@login_required
def profile_dashboard(request):
    user    = request.user
    profile = user.userprofile
    logs    = CaseActivityLog.objects.filter(user=user)

    # last 30 days stats
    today = timezone.localdate()
    start = today - timedelta(days=29)
    chat_counts = (
        UserActivity.objects
        .filter(user=user, activity_type__startswith="chat_", date__gte=start)
        .values("activity_type")
        .annotate(total=Sum("count"))
    )
    type_totals = {r["activity_type"].replace("chat_", ""): r["total"] for r in chat_counts}

    return render(request, "profile.html", {
        "profile":     profile,
        "logs":        logs,
        "type_totals": json.dumps(type_totals),
    })


@login_required
@require_POST
def save_case_log(request):
    data  = json.loads(request.body)
    log_id = data.get("id")

    if log_id:
        log = get_object_or_404(CaseActivityLog, id=log_id, user=request.user)
    else:
        log = CaseActivityLog(user=request.user)

    log.title       = data.get("title", "").strip()
    log.description = data.get("description", "").strip()
    log.category    = data.get("category", "study")
    log.tags        = data.get("tags", "")
    log.date        = data.get("date", timezone.localdate())
    log.save()

    # record as activity
    from .services.activity_tracker import record_activity
    record_activity(request.user, "case_log", {"log_id": log.id})

    return JsonResponse({
        "status": "ok",
        "id":          log.id,
        "title":       log.title,
        "category":    log.category,
        "tags":        log.tags_list(),
        "date":        log.date.isoformat(),
        "is_pinned":   log.is_pinned,
        "description": log.description,
    })


@login_required
@require_POST
def delete_case_log(request, log_id):
    log = get_object_or_404(CaseActivityLog, id=log_id, user=request.user)
    log.delete()
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def pin_case_log(request, log_id):
    log = get_object_or_404(CaseActivityLog, id=log_id, user=request.user)
    log.is_pinned = not log.is_pinned
    log.save(update_fields=["is_pinned"])
    return JsonResponse({"status": "ok", "is_pinned": log.is_pinned})


@login_required
def heatmap_data(request):
    today = timezone.localdate()
    start = today - timedelta(days=364)

    summaries = DailyActivitySummary.objects.filter(
        user=request.user, date__gte=start
    ).values("date", "total_count")

    data = {s["date"].isoformat(): s["total_count"] for s in summaries}
    result, streak, cur = [], 0, 0

    for i in range(365):
        d = (start + timedelta(days=i)).isoformat()
        result.append({"date": d, "count": data.get(d, 0)})

    for i in range(364, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        if data.get(d, 0) > 0: cur += 1
        else: cur = 0
    streak = cur

    return JsonResponse({
        "heatmap":          result,
        "current_streak":   streak,
        "total_activities": sum(data.values()),
        "active_days":      len(data),
    })

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create profile with default tier + credits
        UserProfile.objects.create(
            user=user,
            subscription_tier="free",
            credits_balance=1000
        )

        messages.success(request, "Account created successfully")
        return redirect("login")

    return render(request, "register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def subscription_view(request):
    profile = request.user.userprofile
    return render(request, "subscription.html", {"profile": profile})