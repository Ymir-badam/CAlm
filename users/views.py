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
    ######skills average
    user_data=UserProfile.objects.get(user=user)
    financial_reporting=user_data.financial_reporting
    financial_reporting_count=user_data.financial_reporting_count
    financial_reporting_skill_avg=financial_reporting/financial_reporting_count if financial_reporting_count>0 else 0

    direct_taxation=user_data.direct_taxation_count
    direct_taxation_count=user_data.direct_taxation_count
    direct_taxation_skill_avg=direct_taxation/direct_taxation_count if direct_taxation_count>0 else 0

    gst_and_indirect_tax=user_data.gst_and_indirect_tax
    gst_and_indirect_tax_count=user_data.gst_and_indirect_tax_count
    gst_and_indirect_tax_skill_avg=gst_and_indirect_tax/gst_and_indirect_tax_count if gst_and_indirect_tax_count>0 else 0

    audit_and_assurance=user_data.audit_and_assurance
    audit_and_assurance_count=user_data.audit_and_assurance_count
    audit_and_assurance_skill_avg=audit_and_assurance/audit_and_assurance_count if audit_and_assurance_count>0 else 0

    coporate_law=user_data.coporate_law
    coporate_law_count=user_data.coporate_law_count
    coporate_law_skill_avg=coporate_law/coporate_law_count if coporate_law_count>0 else 0

    financial_management=user_data.financial_management
    financial_management_count=user_data.financial_management_count
    financial_management_skill_avg=financial_management/financial_management_count if financial_management_count>0 else 0

    ethics_and_prof=user_data.ethics_and_prof
    ethics_and_prof_count=user_data.ethics_and_prof_count
    ethics_and_prof_skill_avg=ethics_and_prof/ethics_and_prof_count if ethics_and_prof_count>0 else 0

    type_totals = {r["activity_type"].replace("chat_", ""): r["total"] for r in chat_counts}

    return render(request, "profile.html", {
        "profile":     profile,
        "logs":        logs,
        "type_totals": json.dumps(type_totals),
        "skills_avg": {
            "financial_reporting": financial_reporting_skill_avg,
            "direct_taxation": direct_taxation_skill_avg,
            "gst_and_indirect_tax": gst_and_indirect_tax_skill_avg,
            "audit_and_assurance": audit_and_assurance_skill_avg,
            "coporate_law": coporate_law_skill_avg,
            "financial_management": financial_management_skill_avg,
            "ethics_and_prof": ethics_and_prof_skill_avg,
        }
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


def institute_view(request):
    return render(request, "institute_analytics.html")
def parents_view(request):
    return render(request, "parents.html")
def performance_view(request):
    return render(request, "performance.html")