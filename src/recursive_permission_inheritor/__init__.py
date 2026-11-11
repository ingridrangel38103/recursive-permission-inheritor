"""Recursive Permission Inheritor.

Applies a permission mask down a directory tree while respecting existing
overrides for specific entries.
"""

from .core import (
    PermissionError_,
    Entry,
    apply_mask,
    plan_mask,
)

__all__ = [
    "PermissionError_",
    "Entry",
    "apply_mask",
    "plan_mask",
]
