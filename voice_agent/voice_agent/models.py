from django.db import models
import os
from datetime import datetime

def document_upload_path(instance, filename):
    # Create a unique path for each document using current date if uploaded_at is not set
    date_str = instance.uploaded_at.strftime("%Y/%m/%d") if instance.uploaded_at else datetime.now().strftime("%Y/%m/%d")
    return f'documents/{date_str}/{filename}'

class Document(models.Model):
    file = models.FileField(upload_to='documents/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    processed_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename

class ChatMessage(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField(default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    agent_id = models.IntegerField(default=1)
    
    def __str__(self):
        return f"Message on {self.document.filename} at {self.timestamp}" 