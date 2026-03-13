from rest_framework import serializers
from .models import *
from django.db.models import Q
from django.utils import timezone


class ProgramSerializer(serializers.ModelSerializer):
    program_type_display = serializers.CharField(
        source='get_program_type_display', read_only=True)

    class Meta(object):
        model = Program
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class CourseResourcesSerializer(serializers.ModelSerializer):
    """Minimal Course serializer for Profile representation"""
    class Meta:
        model = Resource
        fields = ('id', 'name', 'resource_type',
                  'file', 'link', 'description', 'note')


class CourseSerializer(serializers.ModelSerializer):
    program_code = serializers.CharField(
        source='program.code', read_only=True)
    course_resources = CourseResourcesSerializer(
        source='resources', many=True, read_only=True)

    class Meta:
        model = Course
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class ResourceSerializer(serializers.ModelSerializer):
    resource_type_display = serializers.CharField(
        source='get_resource_type_display', read_only=True)
    course_name = serializers.CharField(source='course.title', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class ProfileCourseSerializer(serializers.ModelSerializer):
    """Minimal Course serializer for Profile representation"""
    class Meta:
        model = Course
        fields = ('id', 'title', 'code', 'lms_id')


class ProfileSerializer(serializers.ModelSerializer):
    program_code = serializers.CharField(source='program.code', read_only=True)
    program_name = serializers.CharField(
        source='program.title', read_only=True)
    courses_detail = CourseSerializer(
        source='courses', many=True, read_only=True)
    # courses_detail = ProfileCourseSerializer(
    #     source='courses', many=True, read_only=True)

    class Meta:
        model = Profile
        fields = (
            'id', 'username', 'full_name', 'email', 'program', 'program_code', 'program_name',
            'registration_term', 'email_password', 'is_mentor',
            'is_admin', 'is_active', 'courses', 'courses_detail'
        )
        read_only_fields = ('created_at', 'updated_at', 'is_active')
        extra_kwargs = {
            'email_password': {'write_only': True}
        }

    def create(self, validated_data):
        # The encryption happens automatically at the model level
        return Profile.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # The encryption happens automatically at the model level
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProfileMinimalSerializer(serializers.ModelSerializer):
    """Minimal Profile serializer for related models"""
    class Meta:
        model = Profile
        fields = ('id', 'username', 'full_name', 'email')


class FCMTokenSerializer(serializers.ModelSerializer):
    profile_detail = ProfileMinimalSerializer(source='profile', read_only=True)

    class Meta:
        model = FCMToken
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at',
                            'last_used', 'is_active')


class ProfileMentorRequestSerializer(serializers.ModelSerializer):
    """Minimal Profile serializer for related models"""
    program_code = serializers.CharField(source='program.code', read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'username', 'full_name',
                  'email', 'program', 'program_code')


class MentorRequestSerializer(serializers.ModelSerializer):
    profile_detail = ProfileMentorRequestSerializer(
        source='profile', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = MentorRequest
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class ContactUsSerializer(serializers.ModelSerializer):
    profile_detail = ProfileMinimalSerializer(source='profile', read_only=True)
    category_display = serializers.CharField(
        source='get_category_display', read_only=True)

    class Meta:
        model = ContactUs
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class NewsSerializer(serializers.ModelSerializer):

    class Meta:
        model = News
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class MessageSerializer(serializers.ModelSerializer):
    message_type_display = serializers.CharField(
        source='get_message_type_display', read_only=True)

    class Meta:
        model = Message
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class ChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    profile_detail = ProfileMinimalSerializer(source='profile', read_only=True)

    class Meta:
        model = Chat
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')


class BulkMessageSerializer(serializers.Serializer):
    message_type = serializers.ChoiceField(choices=MessageType.choices)
    time_stamp = serializers.DateTimeField()
    content = serializers.CharField()

    def validate_time_stamp(self, value):
        """
        Ensure timestamp is not in the future
        """
        if value > timezone.now():
            raise serializers.ValidationError(
                "Timestamp cannot be in the future")
        return value


class ChatBulkCreateSerializer(serializers.Serializer):
    chat_id = serializers.CharField(max_length=255)
    messages = BulkMessageSerializer(many=True)


# Utility function to get choice serializers
def get_choice_serializer(choices):
    return [{'value': choice[0], 'display': choice[1]} for choice in choices]


#
#

########################
## Helper Serializers ##
########################


class StudentLoginSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    email_password = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if len(value) < 6:
            raise serializers.ValidationError(
                "Username must be at least 6 characters long")
        return value


class ProfileResponseSerializer(serializers.ModelSerializer):
    program_code = serializers.CharField(source='program.code', read_only=True)
    courses_detail = ProfileCourseSerializer(
        source='courses', many=True, read_only=True)
    program = ProgramSerializer()
    courses = CourseSerializer()

    class Meta:
        model = Profile
        exclude = ('created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at', 'is_active')
        extra_kwargs = {
            'email_password': {'write_only': True}
        }


class ProgramUpdateSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=True)
    program_id = serializers.CharField(required=True)

    class Meta:
        model = Program
        fields = ['code', 'program_id', 'title', 'program_type', 'description']


class CourseUpdateSerializer(serializers.ModelSerializer):
    lms_id = serializers.CharField(required=True)

    class Meta:
        model = Course
        fields = ['lms_id', 'title', 'code', 'description', 'link']


class ProfileUpdateSerializer(serializers.Serializer):
    program = ProgramUpdateSerializer(required=True)
    courses = CourseUpdateSerializer(many=True, required=True)


class EmailServiceSerializer(serializers.ModelSerializer):
    tokens = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('email', 'email_password', 'tokens')

    def get_tokens(self, obj):
        # Get all active tokens
        try:
            active_tokens = obj.fcm_tokens.filter(
                is_active=True).values_list('token', flat=True)
            return list(active_tokens)
        except Exception as e:
            # Log error or handle appropriately
            return None


class BroadcastFCMTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = FCMToken
        fields = ('token',)
        read_only_fields = ('created_at', 'updated_at',
                            'last_used', 'is_active')
#
#
