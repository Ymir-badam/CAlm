from django.db import models
from notebooks.models import Notebook
from documents.models import Document

class ChatSession(models.Model):
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    selected_documents = models.ManyToManyField(Document)
    model_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    credits_used = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)