from django.contrib import admin
from .models import UserProfile,UserActivity,DailyActivitySummary,CaseActivityLog

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "subscription_tier", "credits_balance", "total_tokens_used")
    list_filter = ("subscription_tier",)
    search_fields = ("user__username",)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type")
    list_filter = ("activity_type",)
    search_fields = ("user__username",)


admin.site.register(DailyActivitySummary)

admin.site.register(CaseActivityLog)