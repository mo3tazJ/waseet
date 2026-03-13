import os
import re
import uuid
from datetime import datetime
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q
from backend.fcm.messaging2 import send_fcm_message
import logging

logger = logging.getLogger(__name__)


def resource_upload_path(instance, filename):
    """
    Generate upload path for resource files in the format:
    resources/{program_code}/{course_title}/{year}/{month}/{day}/{filename}
    """
    # Get the current date for organizing by date
    now = timezone.now()

    # Get program code and course title, with fallbacks for None values
    program_code = "unknown_program"
    course_title = "unknown_course"

    if instance.course and instance.course.program:
        program_code = instance.course.program.code
        # Clean the program code to remove special characters and make URL-safe
        program_code = slugify(program_code)
        if not program_code:  # If slugify returns empty string
            program_code = "unknown_program"

    if instance.course:
        course_title = instance.course.title
        # Clean the course title to remove special characters and make URL-safe
        course_title = slugify(course_title)
        if not course_title:  # If slugify returns empty string
            course_title = "unknown_course"

    # Ensure filename is safe

    # Split filename into name and extension
    name, ext = os.path.splitext(filename)
    # Slugify Onle the name
    safe_name = slugify(name)
    # fallback name
    if not safe_name:  # If slugify returns empty string
        safe_name = f"file_{now:%Y%m%d_%H%M%S}"
    # safe_filename = f"{safe_name}{ext}"
    # Add a unique identifier to prevent filename collisions
    # unique_id = uuid.uuid4().hex[:4]
    # Add Time Stamp to avoid file name collision
    current_datetime = datetime.now()
    timestamp = current_datetime.strftime("%Y%m%d_%H%M%S")
    # Recnstract the file name with the original extension and unique_id
    safe_filename = f"{safe_name}_{timestamp}{ext}"

    # safe_filename = slugify(filename)
    # if not safe_filename:
    #     # If the filename can't be slugified, use a timestamp-based name
    #     ext = filename.split('.')[-1] if '.' in filename else ''
    #     safe_filename = f"file_{now:%Y%m%d_%H%M%S}.{ext}" if ext else f"file_{now:%Y%m%d_%H%M%S}"

    # Generate the path
    path = f"resources/{program_code}/{course_title}/{now:%Y}/{now:%m}/{now:%d}/{safe_filename}"

    return path


def send_notification(subs):
    print("start function")
    print(subs)
    try:
        for sub in subs:
            print(sub)
        print("Done looping")
    except:
        print("Error!")
    print("Finish From function")
