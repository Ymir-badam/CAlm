from django.db import models
from notebooks.models import Notebook

def user_file_path(instance, filename):
    return f"user_{instance.notebook.user.id}/{instance.notebook.id}/{filename}"

class Document(models.Model):
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=user_file_path)
    qdrant_collection = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title