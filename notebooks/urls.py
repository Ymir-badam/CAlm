from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notebooks/", views.notebook_list, name="notebook_list"),
    path("notebooks/create/", views.create_notebook, name="create_notebook"),
    path("notebooks/<int:notebook_id>/", views.notebook_detail, name="notebook_detail"),
]