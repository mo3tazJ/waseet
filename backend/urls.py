from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()

router.register(r'programs', views.ProgramViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'resources', views.ResourceViewSet)
# 'api/profiles/update_profile/' for update automaticly created by Viewset
router.register(r'profiles', views.ProfileViewSet)
router.register(r'fcm-tokens', views.FCMTokenViewSet)
router.register(r'mentor-requests', views.MentorRequestViewSet)
router.register(r'contact-messages', views.ContactUsViewSet)
router.register(r'news', views.NewsViewSet)


urlpatterns = [
    path('api/', include(router.urls)),  # API routes
    path('api/student-login/', views.student_login, name='student-login'),
    path('api/student-logout/', views.student_logout, name='student-logout'),
    path('api/get_mentor_resources/',
         views.get_mentor_resources, name='get-mentor-resources'),
    path("api/broadcast/", views.broadcast, name="broadcast"),
    path('api/email-service/', views.email_service, name='email-service'),
    path('api/chat/bulk-messages/', views.chat_bulk_messages,
         name='chat-bulk-messages'),

]
