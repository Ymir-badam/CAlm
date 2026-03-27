from django.urls import path
from . import views

urlpatterns = [
    
    path(
        "notebooks/<int:notebook_id>/chat/create/",
        views.create_chat_session,
        name="create_chat_session",
    ),
    path("chat/<int:session_id>/", views.chat_page, name="chat_page"),
    path("chat/<int:session_id>/stream/", views.chat_stream, name="chat_stream"),
    path("chat/<int:session_id>/toggle-doc/", views.toggle_document, name="toggle_document"),
]