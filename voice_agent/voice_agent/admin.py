from django.contrib import admin
from .models import Document, ChatMessage

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'content_type', 'timestamp')
    search_fields = ('filename', 'processed_text')
    readonly_fields = ('timestamp',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('document', 'message', 'timestamp', 'agent_id')
    search_fields = ('message', 'response')
    readonly_fields = ('timestamp',)
    list_filter = ('agent_id',) 