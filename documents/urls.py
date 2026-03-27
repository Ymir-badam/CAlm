from django.urls import path
from . import views

urlpatterns = [
    path(
        "notebooks/<int:notebook_id>/upload/",
        views.upload_document,
        name="upload_document",
    ),
     path("documents/<int:doc_id>/chart/",     views.document_chart,     name="document_chart"),
    path("documents/<int:doc_id>/waterfall/", views.document_waterfall, name="document_waterfall"),
    path("documents/<int:doc_id>/variance/",  views.document_variance,  name="document_variance"),
    path("documents/dashboard/",              views.chart_dashboard,    name="chart_dashboard"),
]