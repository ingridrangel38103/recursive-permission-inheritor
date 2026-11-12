# recursive-permission-inheritor

Applies a permission mask down a directory tree while respecting existing
overrides for specific entries.

```python
from recursive_permission_inheritor import Entry, apply_mask, plan_mask

root = Entry("root").add(
    Entry("a").add(Entry("a1")),
    Entry("b", override=0o700).add(Entry("b1")),
)

# Inspect the plan without touching the tree.
print(plan_mask(root, 0o755))
# [('root', 0o755), ('a', 0o755), ('a1', 0o755), ('b', 0o700), ('b1', 0o700)]

# Write the masks onto the entries.
apply_mask(root, 0o755)
print(root.children[0].mask)  # 0o755
print(root.children[1].mask)  # 0o700
```

The package exports four names: `Entry`, `PermissionError_`, `plan_mask`, and
`apply_mask`.

## Why this exists

Applying a single mask to a tree is easy until some entries already carry a
permission of their own. The usual failure mode is either to clobber those
values or to skip them and leave their children inheriting from the wrong
place. This library treats an entry with an `override` as a pin: that value is
applied to the entry and becomes the inherited value for its whole subtree,
while everything else takes the mask passed to `plan_mask` or `apply_mask`.

The trade-off is that the module is pure and works on an in-memory tree of
`Entry` objects rather than the real filesystem. That keeps the inheritance
rules explicit and testable without fixtures on disk; callers who need to
apply the resulting plan to real files can read the returned list of
`(name, mask)` pairs and do so themselves.

## Edge cases

`plan_mask` returns pairs in pre-order, so parents appear before their
children. `apply_mask` walks the tree in the same order and assigns masks by
traversal position, not by name, so two sibling entries that happen to share a
name still receive distinct values. Negative masks, boolean masks, and
non-`Entry` roots raise `PermissionError_`.
