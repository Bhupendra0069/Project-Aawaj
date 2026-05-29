"""
AAWAJ Views Package.
Re-exports all views so that existing imports (e.g., `from complaints import views`)
continue to work without any changes to urls.py or other files.
"""

from .helpers import role_required
from .pages import *
from .complaints_api import *
from .moderation_api import *
from .government_api import *
from .analytics_api import *
from .resolved_api import *
