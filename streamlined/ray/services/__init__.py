"""
Services folder is like a toolbox providing necessary tools for different purposes.

These services should be plug and use, decoupled from anything else.
"""

from .dependency_injection import DependencyInjection
from .dependency_tracking import DependencyTracking
from .event_notification import EventNotification
from .reaction import Reaction, after, before, raises
from .scoping import Scoping, to_magic_naming
from .service import Service
