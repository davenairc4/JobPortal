from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('rfqts/create/', views.create_rfqts, name='create_rfqts'),
    path('rfqts/list/', views.rfqts_list, name='rfqts_list'),
    path('rfqts/<int:rfqts_id>/', views.rfqts_detail, name='rfqts_detail'),
    path('create/', views.create_job, name='create_job'),
    path('create/<int:rfqts_id>/', views.create_job, name='create_job_from_rfqts'),
    path('<int:job_id>/positions/', views.manage_positions, name='manage_positions'),
    path('<int:job_id>/advertise/', views.create_advertisement, name='create_advertisement'),
    path('advertisement/<int:ad_id>/edit/', views.edit_advertisement, name='edit_advertisement'),
    path('<int:job_id>/apply/', views.apply_for_job, name='apply_for_job'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('<int:job_id>/applications/', views.view_applications, name='view_applications'),
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('application/<int:application_id>/status/<str:status>/', views.update_application_status, name='update_application_status'),
]