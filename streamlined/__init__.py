import ray

from .constants import *
from .pipeline import Pipeline

if not ray.is_initialized():
    ray.init()
