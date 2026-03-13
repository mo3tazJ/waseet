from django.db import models
from django.core.validators import MinLengthValidator
# from django_cryptography.fields import encrypt
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField
from model_utils import FieldTracker
import logging

from backend.helper import resource_upload_path
from .validators import validate_file_extension, validate_file_size


# Set up logging
logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Created", auto_now_add=True)
    updated_at = models.DateTimeField("Updated", auto_now=True)
    is_active = models.BooleanField(default=True)

    # # override delete method (Soft Delete)
    # def delete(self, *args, **kwargs):
    #     self.is_active = False
    #     self.save()

    class Meta:
        abstract = True  # MUST be abstract to prevent separate table


class ProgramType(models.TextChoices):
    MASTER = "master", "Master"
    BACHELOR = "bachelor", "Bachelor"
    INSTITUTION = "institution", "Institution"
    NOTDEFINED = "notdefined", "Not Defined"


class ResourceType(models.TextChoices):
    ARTICLE = "article", "Article"
    VIDEO = "video", "Video"
    FILE = "file", "File"
    SOCIAL = "social", "Social"


class CategoryType(models.TextChoices):
    PROBLEM = "problem", "Problem"
    FEATURE = "feature", "Feature Request"


class NewsType(models.TextChoices):
    SVU = "svu", "SVU"
    EDUCATION = "education", "Education"
    GENERAL = "general", "General"


class NewsPriority(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class MessageType(models.TextChoices):
    QUESTION = "question", "Question"
    ANSWER = "answer", "Answer"


class Program(TimeStampedModel):
    code = models.CharField("Program Code", max_length=10, unique=True)
    program_id = models.CharField("program_id", max_length=10, unique=True)
    title = models.CharField(
        "Program Title", max_length=100, null=True, blank=True)
    program_type = models.CharField(
        "Program Type",
        max_length=20,
        choices=ProgramType.choices,
        default=ProgramType.NOTDEFINED
    )
    description = models.TextField("Description", null=True, blank=True)

    class Meta:
        verbose_name = ("Program")
        verbose_name_plural = ("Programs")
        ordering = ["code"]
        indexes = [
            # For filtering by program type
            models.Index(fields=['program_type']),
            models.Index(fields=['is_active']),     # For soft delete queries
        ]

    def __str__(self):
        return self.code


class Course(TimeStampedModel):
    lms_id = models.CharField("LMS ID", max_length=50, unique=True)
    title = models.CharField("Course Title", max_length=255)
    program = models.ForeignKey(
        Program,
        verbose_name="Program",
        on_delete=models.CASCADE,
        related_name="courses"
    )
    code = models.CharField(
        "Course Code", max_length=10, null=True, blank=True)
    description = models.TextField("Description", null=True, blank=True)
    link = models.URLField("Course URL", null=True, blank=True)

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ['program', 'title']
        indexes = [
            # Added for query optimization
            models.Index(fields=['lms_id']),
            # For filtering courses by program
            models.Index(fields=['program', 'is_active']),
            # For soft delete queries
            models.Index(fields=['is_active']),

        ]

    def __str__(self):
        return f"{self.program.code} - {self.title}"


class Resource(TimeStampedModel):
    name = models.CharField("Resource", max_length=255)
    link = models.URLField("External Link", null=True, blank=True)
    description = models.TextField("Description", null=True, blank=True)
    note = models.CharField("Note", null=True, blank=True, max_length=255)
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.FILE
    )
    course = models.ForeignKey(
        Course,
        verbose_name=("Course"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources'
    )
    file = models.FileField(
        help_text="The maximum file size that can be uploaded is 25MB",
        upload_to=resource_upload_path,
        validators=[validate_file_extension, validate_file_size],
        blank=True,
        null=True
    )

    # file = models.FileField(
    #     upload_to='resources/%Y/%m/%d/',
    #     validators=[validate_file_extension],  # Basic validation
    #     blank=True,
    #     null=True
    # )

    class Meta:
        verbose_name = ("Resource")
        verbose_name_plural = ("Resources")
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'resource_type', 'course'],
                name='unique_resource_type_course'
            )
        ]
        indexes = [
            # For filtering by resource type
            models.Index(fields=['resource_type']),
            # For filtering resources by course
            models.Index(fields=['course', 'is_active']),
            models.Index(fields=['is_active']),       # For soft delete queries
        ]

    def __str__(self):
        return f"{self.get_resource_type_display()}: {self.name}"


class Profile(TimeStampedModel):
    username = models.CharField(
        "User Name",
        max_length=50,
        unique=True,
        validators=[MinLengthValidator(6)]
    )
    full_name = models.CharField("Full Name", max_length=255)
    program = models.ForeignKey(
        Program,
        verbose_name=("Program"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    registration_term = models.CharField(
        "Registration Term", max_length=10, null=True, blank=True)  # from svuis personal profile
    email = models.EmailField("Email", unique=True)
    email_password = EncryptedCharField(
        "Encrypted Email Password",
        help_text="Automatically encrypted at rest",
        null=True,
        blank=True,
        max_length=255
    )
    # email_password = EncryptedTextField(
    #     "Encrypted Email Password",
    #     help_text="Automatically encrypted at rest",
    #     null=True,
    #     blank=True
    # )
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name='students'
    )
    is_mentor = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = ("Profile")
        verbose_name_plural = ("Profiles")
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['email']),
            # For filtering profiles by program
            models.Index(fields=['program', 'is_active']),
            # For filtering mentors
            models.Index(fields=['is_mentor']),
            # For filtering admins
            models.Index(fields=['is_admin']),
            # For filtering by registration term
            models.Index(fields=['registration_term']),


        ]

    def __str__(self):
        return self.full_name


class FCMToken(TimeStampedModel):
    profile = models.ForeignKey(
        Profile,
        verbose_name="Profile",
        on_delete=models.CASCADE,
        related_name='fcm_tokens'
    )
    token = models.CharField("FCM Token", unique=True, max_length=255)
    device_id = models.CharField(
        "Device ID",
        max_length=255,
        null=True,
        blank=True,
        help_text="Unique identifier for the device"
    )
    last_used = models.DateTimeField("Last Used", auto_now=True)

    class Meta:
        verbose_name = "FCM Token"
        verbose_name_plural = "FCM Tokens"
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['profile', 'is_active']),
            # For device-specific queries
            models.Index(fields=['device_id']),
            # For cleaning up old tokens
            models.Index(fields=['last_used']),
        ]

    def __str__(self):
        return f"{self.profile.username} - FCMToken"

    def save(self, *args, **kwargs):
        # Deactivate any existing token for this device
        if self._state.adding or self.device_id:  # Only if adding or device_id is set
            FCMToken.objects.filter(
                profile=self.profile,
                device_id=self.device_id
            ).update(is_active=False)

        # Ensure token is unique and deactivate any duplicates
        if self.token:
            FCMToken.objects.filter(
                token=self.token
            ).exclude(device_id=self.device_id).update(is_active=False)

        super().save(*args, **kwargs)


class MentorRequest(TimeStampedModel):
    profile = models.ForeignKey(
        Profile, verbose_name="Profile", on_delete=models.CASCADE, related_name='mentor_requests')
    message = models.TextField("Message", null=True, blank=True)
    phone = models.CharField(
        "Phone Number", max_length=15, null=True, blank=True)
    status = models.BooleanField(
        "Mentor Status", default=False, help_text="Approval status for mentor request")
    # tracker to monitor changes to the status field
    tracker = FieldTracker(fields=['status'])

    class Meta:
        verbose_name = ("Mentor Request")
        verbose_name_plural = ("Mentor Requests")
        ordering = ['-created_at']
        indexes = [
            # For filtering by approval status
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),     # For time-based queries
        ]

    def __str__(self):
        return f"Mentor Request from {self.profile.full_name}"

    def save(self, *args, **kwargs):
        # Check if status is being changed
        if self.pk and self.tracker.has_changed('status'):
            # Update the profile's is_mentor field
            if self.profile.is_mentor != self.status:
                self.profile.is_mentor = self.status
                self.profile.save(update_fields=['is_mentor'])
        super().save(*args, **kwargs)


class ContactUs(TimeStampedModel):
    profile = models.ForeignKey(
        Profile,
        verbose_name="Profile",
        on_delete=models.CASCADE,
        related_name='contact_us_messages')
    message = models.TextField("Message", null=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=CategoryType.choices,
        default=CategoryType.PROBLEM
    )

    class Meta:
        verbose_name = ("ContactUs")
        verbose_name_plural = ("Contact Us Messages")
        indexes = [
            # For filtering by category
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),     # For time-based queries
        ]

    def __str__(self):
        # More informative
        return f"{self.profile.full_name} - {self.category}"


class News(TimeStampedModel):
    title = models.CharField("Title", max_length=255)
    description = models.TextField("Description", null=True, blank=True)
    link = models.URLField("External Link", null=True, blank=True)
    news_type = models.CharField(
        "News Type", max_length=20, choices=NewsType.choices, default=NewsType.GENERAL)
    priority = models.CharField("Priority",
                                max_length=20,
                                choices=NewsPriority.choices,
                                default=NewsPriority.MEDIUM
                                )

    class Meta:
        verbose_name = ("News")
        verbose_name_plural = ("News")
        ordering = ['-created_at']
        indexes = [
            # For filtering by category
            models.Index(fields=['news_type']),
            models.Index(fields=['priority']),
            # For time-based queries
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        # More informative
        return f"{self.get_news_type_display()} - {self.title}"


class Chat(TimeStampedModel):
    unq_chat_id = models.CharField("Title", max_length=255)
    profile = models.ForeignKey(
        Profile,
        verbose_name="Profile",
        on_delete=models.CASCADE,
        related_name='chats')

    class Meta:
        verbose_name = ("Chat")
        verbose_name_plural = ("Chats")
        ordering = ['-created_at']
        indexes = [
            # For filtering by category
            models.Index(fields=['unq_chat_id']),
            models.Index(fields=['profile']),
            # For time-based queries
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        # More informative
        return f"{self.profile.full_name}"


class Message(TimeStampedModel):
    chat = models.ForeignKey(
        Chat,
        verbose_name="Chat",
        on_delete=models.CASCADE,
        related_name='messages')
    message_type = models.CharField("Message Type",
                                    max_length=20,
                                    choices=MessageType.choices,
                                    default=MessageType.QUESTION
                                    )
    content = models.TextField("Message", null=True, blank=True)
    timestamp = models.DateTimeField(
        "Time Stamp", auto_now=False, auto_now_add=False)

    class Meta:
        verbose_name = ("Message")
        verbose_name_plural = ("Messages")
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['message_type']),
            models.Index(fields=['chat']),
            # For time-based queries
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        # More informative
        return self.chat.unq_chat_id
