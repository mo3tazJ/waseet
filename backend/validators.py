import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# file validators
def validate_file_extension(value):
    """Basic extension validation as a safety net"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg',
                        '.jpeg', '.png', '.mp4', '.mov', '.avi', '.txt']
    if ext not in valid_extensions:
        raise ValidationError(_('Unsupported file extension.'))


def validate_file_size(value):
    """Validate file size"""
    filesize = value.size
    max_size = 25 * 1024 * 1024  # 25MB
    if filesize > max_size:
        raise ValidationError(
            _("The maximum file size that can be uploaded is 25MB"))
