from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "subscription_tier", "credits_balance", "total_tokens_used")
    list_filter = ("subscription_tier",)
    search_fields = ("user__username",)