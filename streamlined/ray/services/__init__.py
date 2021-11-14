"""
Services folder is like a toolbox providing necessary tools for different purposes.

These services should be plug and use, decoupled from anything else.
"""

from .dependency_injection import DependencyInjection
from .scoping import Scoping, to_magic_naming
from .service import Service
