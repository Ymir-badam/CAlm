from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    

    path("profile/",                        views.profile_dashboard,  name="profile"),
    path("api/activity/heatmap/",           views.heatmap_data,       name="heatmap_data"),
    path("api/case-log/save/",              views.save_case_log,      name="save_case_log"),
    path("api/case-log/<int:log_id>/delete/", views.delete_case_log,  name="delete_case_log"),
    path("api/case-log/<int:log_id>/pin/",    views.pin_case_log,     name="pin_case_log"),

    path("subscription/", views.subscription_view, name="subscription"),


    path("institute/", views.institute_view, name="institute"),
    path("parents/", views.parents_view, name="parents"),
    path("performance/", views.performance_view, name="performance"),
]