from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/<int:company_id>/', views.chat_api, name='chat_api'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/upload/', views.upload_document, name='upload_document'),
    path('history/', views.chat_history, name='chat_history'),
    path('documents/', views.documents_list, name='documents_list'),
    path('documents/delete/<int:doc_id>/', views.delete_document, name='delete_document'),
    path('integration/', views.integration, name='integration'),
    path('settings/', views.settings_view, name='settings'),
    path('widget/<int:company_id>/', views.chat_widget, name='chat_widget'),
    path('clear-chat/', views.clear_chat, name='clear_chat'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
]
