import json
import uuid
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Document, ChatSession, ChatMessage
from .rag_utils import process_document, get_answer

def index(request):
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    company_id = request.user.id if request.user.is_authenticated else None
    
    # Get or create chat session
    chat_session, created = ChatSession.objects.get_or_create(session_id=session_id, defaults={'user_id': company_id})
    messages_list = chat_session.messages.all().order_by('timestamp')
    
    return render(request, 'chatbot/index.html', {'chat_messages': messages_list, 'company_id': company_id})

@csrf_exempt
def chat_api(request, company_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('message')
        
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        
        chat_session, _ = ChatSession.objects.get_or_create(session_id=session_id, defaults={'user_id': company_id})
        
        # Save user message
        ChatMessage.objects.create(session=chat_session, role='user', content=query)
        
        # Get AI response
        try:
            ai_response = get_answer(query, user_id=company_id)
        except Exception as e:
            error_msg = str(e)
            print(f"--- Chat API Error ---: {error_msg}")
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                return JsonResponse({'error': 'Free API quota exceeded. Please wait a minute and try again.'}, status=429)
            elif "503" in error_msg or "UNAVAILABLE" in error_msg:
                return JsonResponse({'error': 'The AI model is currently experiencing high demand. Please try again in a few moments.'}, status=503)
            return JsonResponse({'error': 'An internal error occurred while processing your request.'}, status=500)
        
        # Save AI message
        ChatMessage.objects.create(session=chat_session, role='ai', content=ai_response)
        
        return JsonResponse({'reply': ai_response})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
def dashboard(request):
    documents = Document.objects.filter(user=request.user).order_by('-uploaded_at')
    user_sessions = ChatSession.objects.filter(user=request.user)
    
    # Analytics
    total_chats = user_sessions.count()
    total_messages = ChatMessage.objects.filter(session__in=user_sessions).count()
    total_documents = documents.count()
    questions_asked = ChatMessage.objects.filter(session__in=user_sessions, role='user').count()
    
    recent_queries = ChatMessage.objects.filter(session__in=user_sessions, role='user').order_by('-timestamp')[:10]
    
    context = {
        'documents': documents,
        'total_chats': total_chats,
        'total_messages': total_messages,
        'total_documents': total_documents,
        'questions_asked': questions_asked,
        'recent_queries': recent_queries
    }
    return render(request, 'chatbot/dashboard.html', context)

@login_required(login_url='login')
def upload_document(request):
    if request.method == 'POST' and request.FILES.get('document'):
        file = request.FILES['document']
        title = request.POST.get('title', file.name)
        
        doc = Document.objects.create(title=title, file=file, user=request.user)
        
        # Process for RAG
        try:
            process_document(doc.file.path, request.user.id)
            doc.processed = True
            doc.save()
            messages.success(request, f"Document '{title}' uploaded and processed successfully.")
        except Exception as e:
            print(f"Error processing document: {e}")
            messages.error(request, "An error occurred while processing the document.")
            
    referer = request.META.get('HTTP_REFERER')
    if referer and 'documents' in referer:
        return redirect('documents_list')
    return redirect('dashboard')

def clear_chat(request):
    request.session.flush()
    return redirect('index')

@login_required(login_url='login')
def chat_history(request):
    query = request.GET.get('q', '')
    user_sessions = ChatSession.objects.filter(user=request.user)
    if query:
        sessions_with_query = ChatMessage.objects.filter(session__in=user_sessions, content__icontains=query).values_list('session', flat=True)
        sessions = ChatSession.objects.filter(id__in=sessions_with_query).order_by('-created_at').prefetch_related('messages')
    else:
        sessions = user_sessions.order_by('-created_at').prefetch_related('messages')
        
    return render(request, 'chatbot/history.html', {'sessions': sessions, 'query': query})

@login_required(login_url='login')
def documents_list(request):
    documents = Document.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'chatbot/documents.html', {'documents': documents})

@login_required(login_url='login')
def delete_document(request, doc_id):
    if request.method == 'POST':
        try:
            doc = Document.objects.get(id=doc_id, user=request.user)
            title = doc.title
            if doc.file:
                doc.file.delete(save=False)
            doc.delete()
            messages.success(request, f"Document '{title}' deleted successfully.")
        except Document.DoesNotExist:
            messages.error(request, "Document not found.")
    return redirect('documents_list')

@login_required(login_url='login')
def integration(request):
    host_url = request.build_absolute_uri('/')[:-1]
    return render(request, 'chatbot/integration.html', {'host_url': host_url})

@xframe_options_exempt
def chat_widget(request, company_id):
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    chat_session, created = ChatSession.objects.get_or_create(session_id=session_id, defaults={'user_id': company_id})
    messages_list = chat_session.messages.all().order_by('timestamp')
    
    return render(request, 'chatbot/widget.html', {'chat_messages': messages_list, 'company_id': company_id})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required(login_url='login')
def settings_view(request):
    from chatbot.models import UserSettings
    settings_obj, created = UserSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        api_key = request.POST.get('gemini_api_key', '').strip()
        
        # Test the API key if provided
        if api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            try:
                test_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, max_retries=1)
                test_llm.invoke("Hi")
                settings_obj.gemini_api_key = api_key
                settings_obj.save()
                messages.success(request, "Gemini API Key updated and verified successfully!")
            except Exception as e:
                messages.error(request, "Invalid Gemini API Key. Please check the key and try again.")
        else:
            settings_obj.gemini_api_key = ""
            settings_obj.save()
            messages.success(request, "API Key removed. Using system default.")
            
        return redirect('settings')
        
    return render(request, 'chatbot/settings.html', {'settings': settings_obj})
