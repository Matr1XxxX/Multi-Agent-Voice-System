# Voice Agent Project Structure Improvements

## 1. Backend Architecture Improvements

### Current Issues:
- All logic is in a single `views.py` file (not shown but implied)
- Models are basic without proper relationships
- No proper service layer separation
- Missing proper error handling and logging structure

### Recommended Structure:

```
voice_agent/
├── voice_agent/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── processors.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── llm_handlers.py
│   │   ├── conversation_manager.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── tts_handler.py
│   │   ├── speech_recognition.py
│   │   ├── urls.py
│   │   └── admin.py
│   └── podcasts/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── services.py
│       ├── script_generator.py
│       ├── urls.py
│       └── admin.py
├── services/
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── ollama_client.py
│   │   └── conversation_router.py
│   ├── document_processing/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── pdf_processor.py
│   │   ├── docx_processor.py
│   │   └── text_processor.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── tts_service.py
│   │   └── speech_service.py
│   └── external/
│       ├── __init__.py
│       └── ollama_service.py
├── utils/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── validators.py
│   ├── helpers.py
│   └── constants.py
├── tests/
│   ├── __init__.py
│   ├── test_documents/
│   ├── test_agents/
│   ├── test_voice/
│   └── test_services/
└── requirements/
    ├── base.txt
    ├── development.txt
    ├── production.txt
    └── testing.txt
```

## 2. Frontend Architecture Improvements

### Current Issues:
- Single large App.js file (not shown but implied)
- No proper component structure
- Missing state management
- No proper error boundaries

### Recommended Structure:

```
voice_agent_frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button/
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   └── LoadingSpinner/
│   │   ├── layout/
│   │   │   ├── Header/
│   │   │   ├── Sidebar/
│   │   │   └── Footer/
│   │   ├── document/
│   │   │   ├── DocumentUpload/
│   │   │   ├── DocumentList/
│   │   │   └── DocumentViewer/
│   │   ├── chat/
│   │   │   ├── ChatInterface/
│   │   │   ├── MessageList/
│   │   │   ├── MessageInput/
│   │   │   └── VoiceControls/
│   │   ├── agents/
│   │   │   ├── AgentSelector/
│   │   │   ├── AgentConfig/
│   │   │   └── AgentStatus/
│   │   └── podcast/
│   │       ├── PodcastPlayer/
│   │       ├── PodcastControls/
│   │       └── ScriptViewer/
│   ├── hooks/
│   │   ├── useDocuments.js
│   │   ├── useChat.js
│   │   ├── useVoice.js
│   │   └── usePodcast.js
│   ├── services/
│   │   ├── api.js
│   │   ├── documentService.js
│   │   ├── chatService.js
│   │   ├── voiceService.js
│   │   └── podcastService.js
│   ├── context/
│   │   ├── AppContext.js
│   │   ├── ChatContext.js
│   │   └── VoiceContext.js
│   ├── utils/
│   │   ├── constants.js
│   │   ├── helpers.js
│   │   └── validators.js
│   ├── styles/
│   │   ├── globals.css
│   │   ├── components/
│   │   └── themes/
│   └── App.js
```

## 3. Database Improvements

### Current Issues:
- Simple models without proper relationships
- No indexing strategy
- Missing audit fields
- No soft delete capability

### Improved Models:

```python
# apps/core/models.py
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True

# apps/documents/models.py
class Document(BaseModel):
    file = models.FileField(upload_to=document_upload_path)
    filename = models.CharField(max_length=255, db_index=True)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    processed_text = models.TextField(blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['filename', 'created_at']),
            models.Index(fields=['processing_status']),
        ]

# apps/agents/models.py
class Agent(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    agent_type = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical Thinker'),
            ('analytical', 'Analytical'),
            ('creative', 'Creative'),
            ('practical', 'Practical'),
        ]
    )
    system_prompt = models.TextField()
    is_default = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict)

class Conversation(BaseModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    participants = models.ManyToManyField(Agent)
    is_podcast_mode = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('completed', 'Completed'),
        ],
        default='active'
    )

class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User'),
            ('agent', 'Agent'),
            ('system', 'System'),
        ]
    )
    metadata = models.JSONField(default=dict)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
```

## 4. Service Layer Implementation

### Document Processing Service:
```python
# services/document_processing/base.py
from abc import ABC, abstractmethod

class DocumentProcessor(ABC):
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> dict:
        pass

# services/document_processing/pdf_processor.py
class PDFProcessor(DocumentProcessor):
    def extract_text(self, file_path: str) -> str:
        # Implementation
        pass
    
    def extract_metadata(self, file_path: str) -> dict:
        # Implementation
        pass
```

### LLM Service:
```python
# services/llm/base.py
class LLMService(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, context: str = None) -> str:
        pass
    
    @abstractmethod
    def generate_conversation(self, messages: list) -> str:
        pass

# services/llm/ollama_client.py
class OllamaLLMService(LLMService):
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
    
    def generate_response(self, prompt: str, context: str = None) -> str:
        # Implementation
        pass
```

## 5. Configuration Management

### Environment-based Settings:
```python
# voice_agent/settings/base.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Common settings
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'apps.core',
    'apps.documents',
    'apps.agents',
    'apps.voice',
    'apps.podcasts',
]

# voice_agent/settings/development.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Development-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# voice_agent/settings/production.py
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Production-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}
```

## 6. Testing Structure

### Backend Tests:
```python
# tests/test_documents/test_services.py
import pytest
from django.test import TestCase
from apps.documents.services import DocumentProcessingService

class TestDocumentProcessingService(TestCase):
    def setUp(self):
        self.service = DocumentProcessingService()
    
    def test_pdf_processing(self):
        # Test implementation
        pass
    
    def test_docx_processing(self):
        # Test implementation
        pass
```

### Frontend Tests:
```javascript
// src/components/chat/ChatInterface/ChatInterface.test.js
import { render, screen, fireEvent } from '@testing-library/react';
import ChatInterface from './ChatInterface';

describe('ChatInterface', () => {
  test('renders chat interface', () => {
    render(<ChatInterface />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
  
  test('sends message on submit', () => {
    // Test implementation
  });
});
```

## 7. Error Handling and Logging

### Custom Exceptions:
```python
# utils/exceptions.py
class VoiceAgentException(Exception):
    """Base exception for Voice Agent"""
    pass

class DocumentProcessingError(VoiceAgentException):
    """Raised when document processing fails"""
    pass

class LLMServiceError(VoiceAgentException):
    """Raised when LLM service fails"""
    pass

class VoiceProcessingError(VoiceAgentException):
    """Raised when voice processing fails"""
    pass
```

### Structured Logging:
```python
# utils/logging.py
import logging
import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

## 8. API Improvements

### Use Django REST Framework:
```python
# apps/documents/serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

# apps/documents/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        document = self.get_object()
        # Processing logic
        return Response({'status': 'processing'})
```

## 9. Security Improvements

### Add Security Middleware:
```python
# voice_agent/settings/base.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'utils.middleware.SecurityHeadersMiddleware',  # Custom security headers
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

## 10. Performance Improvements

### Caching Strategy:
```python
# voice_agent/settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Cache decorators
from django.core.cache import cache
from functools import wraps

def cache_result(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator
```

## 11. Deployment Improvements

### Docker Configuration:
```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements/production.txt .
RUN pip install -r production.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "voice_agent.wsgi:application"]
```

### Docker Compose:
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/voiceagent
    depends_on:
      - db
      - redis
      - ollama

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: voiceagent
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  ollama_data:
```

## 12. Monitoring and Observability

### Health Checks:
```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    try:
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check external services
        # ... other checks
        
        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)
```

## Summary of Key Improvements:

1. **Modular Architecture**: Split into focused apps and services
2. **Better Models**: Proper relationships, indexing, and audit fields
3. **Service Layer**: Clean separation of business logic
4. **Configuration Management**: Environment-based settings
5. **Comprehensive Testing**: Unit and integration tests
6. **Error Handling**: Custom exceptions and structured logging
7. **API Design**: RESTful APIs with proper serialization
8. **Security**: Security headers and best practices
9. **Performance**: Caching and optimization strategies
10. **Deployment**: Docker containerization and orchestration
11. **Monitoring**: Health checks and observability
12. **Frontend Structure**: Component-based architecture with proper state management

These improvements will make your project more maintainable, scalable, and production-ready.