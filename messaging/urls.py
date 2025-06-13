# messaging/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("send/<int:recipient_id>/", views.send_message, name="send_message"),
    path("send/<int:recipient_id>/job/<int:job_id>/", views.send_message, name="send_message_job"),
    path("send/<int:recipient_id>/application/<int:application_id>/", views.send_message, name="send_message_application"),

    path("", views.message_list, name="message_list"),
    path("<int:message_id>/", views.message_detail, name="message_detail"),
    path("<int:message_id>/delete/", views.delete_message, name="delete_message"),

    path(
        "jobs/<int:job_id>/messages/",
        views.fetch_job_messages,
        name="fetch_job_messages",   # ← name must be exactly this
    ),
]
