"""
URL configuration for voice_agent project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html')),
    path('api/upload/', views.upload_document, name='upload_document'),
    path('api/process-message/', views.process_message, name='process_message'),
    path('api/voice-input/', views.process_voice_input, name='process_voice_input'),
    path('api/voice-response/', views.generate_voice_response, name='generate_voice_response'),
    path('api/podcast-tts/', views.podcast_tts, name='podcast-tts'),
]
