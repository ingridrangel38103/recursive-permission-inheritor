"""Core logic for recursive permission inheritance.

The model is deliberately small and pure: a tree of :class:`Entry` objects is
walked in memory, and for each entry we compute the permission mask that should
be applied. Nothing here touches the real filesystem, which keeps the module
testable without fixtures on disk and makes the semantics explicit.

An entry may carry an *override* mask. An override pins that entry's
permissions and stops inheritance from reaching its children: the children are
treated as roots of their own subtrees and inherit from the override value.
This is the one interpretation of "respect existing overrides" we commit to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


class PermissionError_(ValueError):
    """Raised when a mask or an entry is not well formed.

    Named with a trailing underscore so it does not shadow the builtin
    ``PermissionError``.
    """


@dataclass
class Entry:
    """A node in the directory tree.

    ``name`` is the path component (or any stable identifier). ``mask`` is the
    permission mask currently recorded for this entry, if any. ``override``
    pins the entry: when set, it is the value applied to this entry and its
    descendants instead of the inherited mask. ``children`` are the direct
    descendants.
    """

    name: str
    mask: Optional[int] = None
    override: Optional[int] = None
    children: List["Entry"] = field(default_factory=list)

    def add(self, *children: "Entry") -> "Entry":
        """Append children and return self, for fluent tree construction."""
        self.children.extend(children)
        return self


def _check_mask(mask: int, label: str) -> None:
    if not isinstance(mask, int) or isinstance(mask, bool):
        raise PermissionError_(f"{label} must be an int, got {type(mask).__name__}")
    if mask < 0:
        raise PermissionError_(f"{label} must be non-negative, got {mask}")


def _check_entry(entry: Entry) -> None:
    if not isinstance(entry, Entry):
        raise PermissionError_(f"expected Entry, got {type(entry).__name__}")
    if entry.mask is not None:
        _check_mask(entry.mask, f"mask of {entry.name!r}")
    if entry.override is not None:
        _check_mask(entry.override, f"override of {entry.name!r}")


def plan_mask(root: Entry, mask: int) -> List[Tuple[str, int]]:
    """Compute the mask to apply to every entry under ``root``.

    Returns a list of ``(name, effective_mask)`` pairs in pre-order (parents
    before children). ``root`` itself is included and receives ``mask`` unless
    it has an override, in which case the override wins for the whole subtree.

    The input tree is not modified.
    """
    _check_mask(mask, "mask")
    _check_entry(root)

    plan: List[Tuple[str, int]] = []

    def visit(entry: Entry, inherited: int) -> None:
        _check_entry(entry)
        effective = entry.override if entry.override is not None else inherited
        plan.append((entry.name, effective))
        for child in entry.children:
            visit(child, effective)

    visit(root, mask)
    return plan


def apply_mask(root: Entry, mask: int) -> List[Tuple[str, int]]:
    """Apply ``mask`` down the tree, mutating each entry's ``mask`` field.

    Returns the same plan as :func:`plan_mask` so callers can inspect what was
    written. Overrides are honoured exactly as in :func:`plan_mask`.
    """
    plan = plan_mask(root, mask)

    def write(entry: Entry) -> None:
        for name, value in plan:
            if name == entry.name:
                entry.mask = value
                break
        for child in entry.children:
            write(child)

    # Walk the tree and set masks from the plan, matching by object identity
    # rather than by name to avoid ambiguity when two entries share a name.
    index: Dict[int, int] = {}
    for i, (_, value) in enumerate(plan):
        index[i] = value

    counter = 0

    def assign(entry: Entry) -> None:
        nonlocal counter
        entry.mask = index[counter]
        counter += 1
        for child in entry.children:
            assign(child)

    assign(root)
    return plan
