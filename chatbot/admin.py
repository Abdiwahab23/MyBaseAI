from django.contrib import admin
from .models import Document, ChatSession, ChatMessage

class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at', 'processed')

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'timestamp')

class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'created_at')
    inlines = [ChatMessageInline]

admin.site.register(Document, DocumentAdmin)
admin.site.register(ChatSession, ChatSessionAdmin)
admin.site.register(ChatMessage)
