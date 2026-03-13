from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html
from .models import *


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    # list_display = "__all__"
    list_display = ('code', 'title', "program_id", 'program_type', 'is_active')
    list_filter = ('program_type', 'is_active', 'created_at')
    search_fields = ('code', 'title', 'description')
    ordering = ('code',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('code', 'title', 'program_type', 'program_id', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    actions = ['activate_programs', 'deactivate_programs']

    def activate_programs(self, request, queryset):
        queryset.update(is_active=True)
    activate_programs.short_description = "Activate selected programs"

    def deactivate_programs(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_programs.short_description = "Deactivate selected programs"


class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    show_change_link = True


class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 0
    # readonly_fields = ('created_at', 'updated_at')
    exclude = ('created_at', 'updated_at', 'note', 'description', 'link')
    can_delete = False
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'program', 'code', 'lms_id', 'is_active')
    list_filter = ('program', 'is_active', 'created_at')
    search_fields = ('code', 'title', 'lms_id', 'description')
    ordering = ('program',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('program',)
    inlines = [ResourceInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'program', 'code', 'lms_id')
        }),
        ('Additional Information', {
            'fields': ('description', 'link'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource_type', 'course',
                    'link', 'file_link', 'is_active')
    list_filter = ('resource_type', 'course', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'note')
    ordering = ('course', 'resource_type')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('course',)

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "No file"
    file_link.short_description = 'File'

    fieldsets = (
        (None, {
            'fields': ('name', 'resource_type', 'course')
        }),
        ('Content', {
            'fields': ('description', 'note', 'link', 'file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


class FCMTokenInline(admin.TabularInline):
    model = FCMToken
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'last_used')
    can_delete = False
    show_change_link = True


class MentorRequestInline(admin.TabularInline):
    model = MentorRequest
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    show_change_link = True


class ContactUsInline(admin.TabularInline):
    model = ContactUs
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False
    show_change_link = True


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'email',
                    'is_mentor', 'is_admin', 'is_active')
    list_filter = ('is_mentor', 'is_admin', 'program', 'registration_term',
                   'is_active', 'created_at')
    search_fields = ('username', 'full_name', 'email', 'registration_term')
    ordering = ('full_name',)
    readonly_fields = ('created_at', 'updated_at')

    filter_horizontal = ('courses',)
    raw_id_fields = ('program',)
    inlines = [FCMTokenInline, MentorRequestInline, ContactUsInline]

    fieldsets = (
        ('Personal Info', {
            'fields': ('username', 'full_name', 'email', 'program', 'registration_term')
        }),
        ('Security', {
            'fields': ('email_password',),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_mentor', 'is_admin')
        }),
        ('Courses', {
            'fields': ('courses',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

    # def save_model(self, request, obj, form, change):
    #     # Handle password encryption if the password field was changed
    #     if 'email_password' in form.changed_data:
    #         obj.set_email_password(form.cleaned_data['email_password'])
    #     super().save_model(request, obj, form, change)


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('profile', 'device_id', 'last_used', 'is_active')
    list_filter = ('is_active', 'last_used', 'created_at')
    search_fields = ('profile__username',
                     'profile__full_name', 'token', 'device_id')
    ordering = ('profile', 'device_id', 'is_active', '-last_used',)
    readonly_fields = ('created_at', 'updated_at', 'last_used')
    raw_id_fields = ('profile',)

    fieldsets = (
        (None, {
            'fields': ('profile', 'token', 'device_id')
        }),
        ('Usage', {
            'fields': ('last_used',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(MentorRequest)
class MentorRequestAdmin(admin.ModelAdmin):
    list_display = ('profile', 'status', 'phone', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('profile__username',
                     'profile__full_name', 'phone', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('profile',)
    actions = ['approve_requests', 'reject_requests']

    fieldsets = (
        (None, {
            'fields': ('profile', 'status')
        }),
        ('Contact Info', {
            'fields': ('phone', 'message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )

    def approve_requests(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, f"{updated} mentor requests approved.")

    def reject_requests(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, f"{updated} mentor requests rejected.")

    approve_requests.short_description = "Approve selected mentor requests"
    reject_requests.short_description = "Reject selected mentor requests"


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('profile', 'category', 'created_at', 'is_active')
    list_filter = ('category', 'created_at', 'is_active')
    search_fields = ('profile__username', 'profile__full_name', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('profile',)

    fieldsets = (
        (None, {
            'fields': ('profile', 'category')
        }),
        ('Message', {
            'fields': ('message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'news_type', 'created_at', 'is_active')
    list_filter = ('news_type', 'created_at', 'is_active')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('title', 'news_type', 'priority')
        }),
        ('Details', {
            'fields': ('link', 'description',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('profile', 'unq_chat_id', 'created_at', 'is_active')
    list_filter = ('profile', 'created_at', 'is_active')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'message_type', 'timestamp', 'is_active')
    list_filter = ('message_type', 'created_at', 'is_active')
    ordering = ('timestamp',)
    readonly_fields = ('created_at', 'updated_at', 'timestamp')

    fieldsets = (
        (None, {
            'fields': ('chat',)
        }),
        ('Details', {
            'fields': ('message_type', 'content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # date_hierarchy = 'action_time'
    # readonly_fields = ['user', 'content_type', 'object_id',
    #                    'object_repr', 'action_flag', 'action_time', 'change_message']
    # list_filter = ['user', 'action_flag']
    search_fields = ['object_repr', 'change_message']
    # list_display = ['__str__', 'user', 'action_flag',
    #                 'action_time', 'content_type', 'object_id']


# Customizing admin site header and title
admin.site.site_header = 'Waseet App Administration'
admin.site.site_title = 'Waseet App Admin'
admin.site.index_title = 'Dashboard'
