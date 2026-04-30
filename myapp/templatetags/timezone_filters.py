from django import template
from django.utils import timezone
import pytz

register = template.Library()

@register.filter
def to_ist(value):
    """
    Convert a datetime to Indian Standard Time (IST).
    Usage: {{ datetime_value|to_ist }}
    """
    if value is None:
        return None
    
    # Get IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    
    # If the datetime is naive, make it aware in UTC first
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.utc)
    
    # Convert to IST
    return value.astimezone(ist)
