from django.urls import path
from . import views

urlpatterns = [
    path('', views.message_list, name='message_list'),
    path('<int:message_id>/', views.message_detail, name='message_detail'),
    path('send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('send/<int:recipient_id>/job/<int:job_id>/', views.send_message, name='send_message_job'),
    path('send/<int:recipient_id>/application/<int:application_id>/', views.send_message, name='send_message_application'),
    path('reply/<int:message_id>/', views.reply_message, name='reply_message'),
]