from django.urls import path
from . import views

urlpatterns = [
    # NOTE: '/ai/health/' must be declared BEFORE the generic '/<user_id>/<chat_id>/'
    # pattern. Django matches in order, first match wins; otherwise '/ai/health/' is
    # captured as user_id='ai', chat_id='health' and routed to chat_detail.
    path('/ai/health/', views.ai_health, name='ai-health'),
    path('/<str:user_id>/', views.chat_session, name='chat-session'),
    path('/<str:user_id>/documents/', views.document_chat_session, name='document-chat-session'),
    path('/<str:user_id>/<str:chat_id>/', views.chat_detail, name='retrieve-chat-session'),
    path('/<str:user_id>/<str:chat_id>/messages/', views.chat_messages, name='chat-messages'),
    path('/<str:user_id>/<str:chat_id>/self-assessment/submit/', views.submit_self_assessment, name='self-assessment-submit'),
    path('/<str:user_id>/<str:chat_id>/self-assessment/skip/', views.skip_self_assessment, name='self-assessment-skip'),
    path('/<str:user_id>/<str:chat_id>/generate-document/', views.generate_document, name='generate-document'),
    path('/<str:user_id>/<str:chat_id>/documents/', views.get_documents, name='get-documents'),
    path('/<str:user_id>/<str:chat_id>/documents/<str:document_id>/download/', views.download_document, name='download-document'),
    path('/<str:user_id>/<str:chat_id>/documents/<str:document_id>/', views.update_document, name='update-document'),
    path('/<str:user_id>/<str:chat_id>/export/', views.export_chat, name='export-chat'),
]