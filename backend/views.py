from django.forms import ValidationError
from backend.fcm.messaging2 import send_fcm_message
from backend.notification import send_news_notifications, send_notification_to_students, send_notification_to_students_async
from .models import *
from .serializers import *
from django.db.models import Prefetch, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets, status, permissions
from .authentication import FCMTokenAuthentication
from django.db import IntegrityError, transaction
from django.forms import ValidationError
from django.utils import timezone
import logging


logger = logging.getLogger(__name__)


################
##  ViewSets  ##
################


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.filter(is_active=True)
    serializer_class = ProgramSerializer
    authentication_classes = [FCMTokenAuthentication]

    def destroy(self, request, *args, **kwargs):
        # Soft delete implementation
        instance = self.get_object()
        instance.delete()  # This will set is_active=False
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    authentication_classes = [FCMTokenAuthentication]


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.filter(is_active=True)
    serializer_class = ResourceSerializer
    authentication_classes = [FCMTokenAuthentication]

    def perform_create(self, serializer):
        # Check if user is a mentor
        if not self.request.user.is_mentor:
            raise PermissionDenied("Only mentors can upload resources")

        data = serializer.validated_data
        course = data.get('course')
        resource = serializer.save()

        # Send notifications to students enrolled in the course
        if resource.course:
            try:
                send_notification_to_students(
                    course=resource.course,
                    resource_name=resource.name,
                    resource_type=resource.get_resource_type_display()
                )
                # # Use async version to avoid blocking the response
                # send_notification_to_students_async(
                #     course=resource.course,
                #     resource_name=resource.name,
                #     resource_type=resource.get_resource_type_display())
            except Exception as e:
                # Log the error but don't prevent resource creation
                logger.error(f"Failed to send notifications: {str(e)}")


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.filter(is_active=True)
    serializer_class = ProfileSerializer
    authentication_classes = [FCMTokenAuthentication]

    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Return choice options for various fields"""
        return Response({
            'program_types': get_choice_serializer(ProgramType.choices),
            'resource_types': get_choice_serializer(ResourceType.choices),
            'category_types': get_choice_serializer(CategoryType.choices),
        })

    @action(detail=False, methods=['post'])
    def update_profile(self, request):
        """
        Update profile with program and courses information from SVU server
        """
        # The user is authenticated via FCMTokenAuthentication
        profile = request.user

        # Validate input data
        serializer = ProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        program_data = data.get('program')
        courses_data = data.get('courses', [])

        try:
            with transaction.atomic():
                # 1. Handle Program
                program = self.handle_program(program_data)

                # 2.a Handle Courses
                courses = self.handle_courses(courses_data, program)

                # # 2.b Handle Courses Bulk
                # courses = self.handle_courses_bulk(courses_data, program)

                # 3. Update Profile with Program and Courses
                profile.program = program
                profile.courses.set(courses)
                profile.save()

                # 4. Return detailed profile response
                profile_serializer = ProfileSerializer(profile)

                return Response(
                    {
                        'message': 'Profile updated successfully',
                        'profile': profile_serializer.data
                    },
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            return Response(
                {'error': f'Error updating profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def handle_program(self, program_data):
        """
        Handle program creation or update
        """
        program_code = program_data.get('code')
        if not program_code:
            raise ValueError("Program code is required")

        try:
            # Try to get existing program
            program = Program.objects.get(code=program_code)

            # Update program fields if they are provided and different
            update_fields = {}
            for field, value in program_data.items():
                if hasattr(program, field) and getattr(program, field) != value:
                    update_fields[field] = value

            if update_fields:
                for field, value in update_fields.items():
                    setattr(program, field, value)
                program.save()

            return program

        except Program.DoesNotExist:
            # Create new program
            return Program.objects.create(**program_data)

        except IntegrityError as e:
            raise ValueError(
                f"Database error while handling program: {str(e)}")

    def handle_courses(self, courses_data, program):
        """
        Handle courses creation or update
        """
        courses = []

        for course_data in courses_data:
            lms_id = course_data.get('lms_id')
            if not lms_id:
                continue  # Skip courses without lms_id

            try:
                # Try to get existing course
                course = Course.objects.get(lms_id=lms_id)

                # Update course fields if they are provided and different
                update_fields = {}
                for field, value in course_data.items():
                    if hasattr(course, field) and getattr(course, field) != value:
                        update_fields[field] = value

                # Always ensure the course is associated with the correct program
                if course.program != program:
                    update_fields['program'] = program

                if update_fields:
                    for field, value in update_fields.items():
                        setattr(course, field, value)
                    course.save()

                courses.append(course)

            except Course.DoesNotExist:
                # Create new course with the program association
                course_data['program'] = program
                course = Course.objects.create(**course_data)
                courses.append(course)

            except IntegrityError as e:
                # Log the error but continue with other courses
                logger.error(f"Error handling course {lms_id}: {str(e)}")
                continue
        return courses

    def handle_courses_bulk(self, courses_data, program):
        """
        Handle courses creation or update using bulk operations for better performance
        """
        # Extract all LMS IDs from the incoming data
        lms_ids = [course.get('lms_id')
                   for course in courses_data if course.get('lms_id')]

        # Fetch all existing courses in a single query
        existing_courses = Course.objects.filter(lms_id__in=lms_ids)
        existing_courses_map = {
            course.lms_id: course for course in existing_courses}

        courses_to_update = []
        courses_to_create = []

        for course_data in courses_data:
            lms_id = course_data.get('lms_id')

            if not lms_id:
                continue  # Skip courses without lms_id

            if lms_id in existing_courses_map:
                # Course exists, check if updates are needed
                course = existing_courses_map[lms_id]
                needs_update = False

                # Check each field for changes
                for field, value in course_data.items():
                    if hasattr(course, field) and getattr(course, field) != value:
                        setattr(course, field, value)
                        needs_update = True

                # Check if program association needs update
                if course.program != program:
                    course.program = program
                    needs_update = True

                if needs_update:
                    courses_to_update.append(course)
            else:
                # Course doesn't exist, create new one
                course_data['program'] = program
                courses_to_create.append(Course(**course_data))

        # Use bulk operations
        if courses_to_update:
            Course.objects.bulk_update(
                courses_to_update,
                fields=['title', 'code', 'description', 'link', 'program']
            )

        if courses_to_create:
            Course.objects.bulk_create(courses_to_create)

        # Return all courses (existing + newly created)
        return list(existing_courses) + courses_to_create


class MentorRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing mentor requests
    """
    queryset = MentorRequest.objects.filter(is_active=True)
    serializer_class = MentorRequestSerializer
    authentication_classes = [FCMTokenAuthentication]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a mentor request and update profile
        """
        mentor_request = self.get_object()
        mentor_request.status = True
        mentor_request.save()

        serializer = self.get_serializer(mentor_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a mentor request and update profile
        """
        mentor_request = self.get_object()
        mentor_request.status = False
        mentor_request.save()

        serializer = self.get_serializer(mentor_request)
        return Response(serializer.data)


class FCMTokenViewSet(viewsets.ModelViewSet):
    queryset = FCMToken.objects.filter(is_active=True)
    serializer_class = FCMTokenSerializer
    authentication_classes = [FCMTokenAuthentication]


class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.filter(is_active=True)
    serializer_class = ContactUsSerializer
    authentication_classes = [FCMTokenAuthentication]


class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.filter(is_active=True)
    serializer_class = NewsSerializer
    authentication_classes = [FCMTokenAuthentication]

    def perform_create(self, serializer):
        # Check if user is an Admin
        # if not self.request.user.is_admin:
        #     raise PermissionDenied("Only Admins can Add News")
        news = serializer.save()
        if news:
            print("News")
            # Send notifications to all active profiles
            try:
                send_news_notifications(
                    head=news.title,
                    news_type=news.get_news_type_display(),
                    description=news.description[:60]
                )
            except Exception as e:
                # Log the error but don't prevent resource creation
                logger.error(f"Failed to send notifications: {str(e)}")
        else:
            print("No News")


#
#
####################
##  Custom Views  ##
####################


# Student logout
@api_view(['POST'])
@permission_classes([AllowAny])
def student_logout(request):
    """
    Logout endpoint that deactivates FCM token based on token and device ID
    Expects: FCM-Token and Device-ID in headers
    Expects: {} in body
    """
    # Get FCM token and device ID from headers
    fcm_token = request.headers.get('FCM-Token')
    device_id = request.headers.get('Device-ID')
    # Validate required headers
    if not fcm_token or not device_id:
        return Response(
            {'error': 'FCM-Token and Device-ID headers are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        # Find and delete all matching FCM tokens
        deleted_count, _ = FCMToken.objects.filter(
            token=fcm_token,
            device_id=device_id
        ).delete()

        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} FCM tokens. Device ID: {device_id}, "
                f"Token: {fcm_token}"
            )
            return Response(
                {'message': f'Logout successful. {deleted_count} FCM token(s) permanently deleted.'},
                status=status.HTTP_200_OK
            )
        else:
            logger.warning(
                f"Failed logout attempt - no tokens found. Device ID: {device_id}, "
                f"Token: {fcm_token}"
            )
            return Response(
                {'error': 'FCM token not found for the provided token and device ID'},
                status=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return Response(
            {'error': f'Error during logout: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Student login
@api_view(['POST'])
@permission_classes([AllowAny])
def student_login(request):
    """
    Handle student login from the Flutter app
    Expects: {full_name, username, email, email_password} in body
    Expects: FCM-Token and Device-ID in headers
    """
    # Validate input data
    serializer = StudentLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    # Extract data from request body
    full_name = data.get('full_name')
    username = data.get('username')
    email = data.get('email')
    email_password = data.get('email_password', '')

    # Extract data from headers
    fcm_token = request.headers.get('FCM-Token')
    device_id = request.headers.get('Device-ID')

    if not all([fcm_token, device_id]):
        return Response(
            {'error': 'Missing FCM-Token or Device-ID in headers'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Check if profile exists
        try:
            profile = Profile.objects.get(username=username)
            is_new_user = False

            # Profile exists, update if needed
            update_fields = {}
            if profile.full_name != full_name:
                update_fields['full_name'] = full_name
            if profile.email != email:
                update_fields['email'] = email
            if email_password and profile.email_password != email_password:
                update_fields['email_password'] = email_password

            if update_fields:
                for field, value in update_fields.items():
                    setattr(profile, field, value)
                profile.save()
        except Profile.DoesNotExist:
            # Profile doesn't exist, create new one
            profile = Profile.objects.create(
                full_name=full_name,
                username=username,
                email=email,
                email_password=email_password
            )
            is_new_user = True

        # Handle FCM token
        handle_fcm_token(profile, fcm_token, device_id)

        # Return profile data
        if is_new_user:
            profile_serializer = ProfileMinimalSerializer(profile)
        else:
            profile_serializer = ProfileSerializer(profile)

        return Response(
            {
                'message': 'Login successful',
                'is_new_user': is_new_user,
                'profile': profile_serializer.data
            },
            status=status.HTTP_201_CREATED if is_new_user else status.HTTP_200_OK
        )
    except IntegrityError as e:
        if 'unique constraint' in str(e).lower():
            if 'username' in str(e).lower():
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif 'email' in str(e).lower():
                return Response(
                    {'error': 'Email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(
            {'error': f'Database error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_fcm_token(profile, fcm_token, device_id):
    """
    Handle FCM token creation or update for a profile
    """
    # Check if device_id already exists for this profile
    try:
        fcm_token_obj = FCMToken.objects.get(
            profile=profile, device_id=device_id)
        # Update existing token
        fcm_token_obj.token = fcm_token
        fcm_token_obj.is_active = True
        fcm_token_obj.save()
    except FCMToken.DoesNotExist:
        # Create new token
        FCMToken.objects.create(
            profile=profile,
            token=fcm_token,
            device_id=device_id
        )
    # Deactivate any other tokens with the same FCM token (to prevent duplicates)
    FCMToken.objects.filter(token=fcm_token).exclude(
        device_id=device_id).update(is_active=False)


# Get Mentor Resources
@api_view(['GET'])
@authentication_classes([FCMTokenAuthentication])
def get_mentor_resources(request):
    profile = request.user
    courses = Course.objects.filter(program=profile.program)
    serialized = CourseSerializer(courses, many=True)
    return Response({"courses": serialized.data})


# Email Service
@api_view(['GET'])
def email_service(request):
    try:
        # Prefetch related data to optimize queries
        profiles = Profile.objects.filter(is_active=True).prefetch_related(
            Prefetch('fcm_tokens', queryset=FCMToken.objects.filter(is_active=True))
        )
        serialized = EmailServiceSerializer(profiles, many=True)
        return Response({"profiles": serialized.data})
    except Exception as e:
        return Response(
            {"error": "Failed to retrieve profiles", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Broadcast A Message
@api_view(['POST'])
@authentication_classes([FCMTokenAuthentication])
def broadcast(request, *args, **kwargs):

    try:
        title = request.data.get('title')
        body = request.data.get('body')
        if not title or not body:
            return Response(
                {"error": "Title and body are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # print(f"{title} - {body}")

        # Get all the tokens
        try:
            tokens = FCMToken.objects.filter(is_active=True)
            tokens_QuerySet = tokens.values_list('token', flat=True)
            # print(list(tokens_QuerySet))
        except Exception as e:
            return Response(
                {"error": "Failed to retrieve tokens", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        total = 0
        success_count = 0
        failed_count = 0
        for fcm_token in tokens_QuerySet:
            total += 1
            try:
                send_fcm_message(
                    fcm_token=fcm_token, title=title, body=body)
                success_count += 1
                # return Response(
                #     {
                #         "message": "Notification sent successfully"
                #     },
                #     status=status.HTTP_200_OK
                # )
            except Exception as e:
                failed_count += 1
                print(str(e))
                continue
                # # Handle FCM-specific errors
                # error_msg = str(e)
                # if "Timeout" in error_msg:
                #     return Response(
                #         {"error": "Notification service temporarily unavailable"},
                #         status=status.HTTP_503_SERVICE_UNAVAILABLE
                #     )
                # elif "Invalid" in error_msg or "not found" in error_msg.lower():
                #     return Response(
                #         {"error": "Invalid device token"},
                #         status=status.HTTP_400_BAD_REQUEST
                #     )
                # else:
                #     return Response(
                #         {"error": "Failed to send notification"},
                #         status=status.HTTP_500_INTERNAL_SERVER_ERROR
                #     )
        # print("Done Looping")
        # print(f"Total = {total}")
        # print(f"Success = {success_count}")
        # print(f"Failed = {failed_count}")
        return Response(
            {"Result": f"Total = {total}, Success = {success_count}, Failed = {failed_count}"},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "Failed to retrieve profiles", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Chat Bulk Messages Save API
@api_view(['POST'])
@authentication_classes([FCMTokenAuthentication])
def chat_bulk_messages(request):
    serializer = ChatBulkCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    chat_id = serializer.validated_data['chat_id']
    messages_data = serializer.validated_data['messages']
    try:
        with transaction.atomic():
            # Get or create the chat
            chat, created = Chat.objects.get_or_create(
                unq_chat_id=chat_id,
                profile=request.user,
                defaults={'unq_chat_id': chat_id, 'profile': request.user}
            )
            # Create all messages
            messages = []
            for msg_data in messages_data:
                message = Message(
                    chat=chat,
                    message_type=msg_data['message_type'],
                    content=msg_data['content'],
                    timestamp=msg_data['time_stamp']
                )
                messages.append(message)

            # Bulk create all messages
            Message.objects.bulk_create(messages)

            # Return success response
            return Response({
                'chat_id': chat_id,
                'created': created,
                'message_count': len(messages),
                'status': 'success'
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in chat_bulk_messages: {str(e)}")
        return Response(
            {'error': f'Failed to process messages: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
