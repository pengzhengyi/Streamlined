"""
Services folder is like a toolbox providing necessary tools for different purposes.

These services should be plug and use, decoupled from anything else.
"""

from .dependency_injection import DependencyInjection
from .dependency_tracking import DependencyTracking
from .event_notification import EventNotification
from .reference import EvalRef, NameRef, ValueRef
from .scoping import Scoped, Scoping, to_magic_naming
from .storage_provider import (
    HybridStorageProvider,
    InMemoryStorageProvider,
    PersistentStorageProvider,
    StorageProvider,
)
