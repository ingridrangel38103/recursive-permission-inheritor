import unittest

from recursive_permission_inheritor import (
    Entry,
    PermissionError_,
    apply_mask,
    plan_mask,
)


class PlanMaskTests(unittest.TestCase):
    def test_root_only(self):
        root = Entry("root")
        self.assertEqual(plan_mask(root, 0o755), [("root", 0o755)])

    def test_preorder_parents_before_children(self):
        root = Entry("root").add(
            Entry("a").add(Entry("a1")),
            Entry("b"),
        )
        self.assertEqual(
            plan_mask(root, 0o640),
            [("root", 0o640), ("a", 0o640), ("a1", 0o640), ("b", 0o640)],
        )

    def test_override_pins_subtree(self):
        root = Entry("root").add(
            Entry("a", override=0o700).add(Entry("a1")),
            Entry("b"),
        )
        self.assertEqual(
            plan_mask(root, 0o755),
            [("root", 0o755), ("a", 0o700), ("a1", 0o700), ("b", 0o755)],
        )

    def test_root_override_wins_over_inherited(self):
        root = Entry("root", override=0o600).add(Entry("a"))
        self.assertEqual(
            plan_mask(root, 0o777),
            [("root", 0o600), ("a", 0o600)],
        )

    def test_nested_overrides(self):
        root = Entry("root").add(
            Entry("a", override=0o700).add(
                Entry("a1", override=0o500).add(Entry("a1x"))
            )
        )
        self.assertEqual(
            plan_mask(root, 0o755),
            [("root", 0o755), ("a", 0o700), ("a1", 0o500), ("a1x", 0o500)],
        )

    def test_plan_does_not_mutate(self):
        root = Entry("root").add(Entry("a"))
        plan_mask(root, 0o755)
        self.assertIsNone(root.mask)
        self.assertIsNone(root.children[0].mask)

    def test_negative_mask_rejected(self):
        with self.assertRaises(PermissionError_):
            plan_mask(Entry("root"), -1)

    def test_negative_override_rejected(self):
        with self.assertRaises(PermissionError_):
            plan_mask(Entry("root", override=-1), 0o755)

    def test_bool_mask_rejected(self):
        with self.assertRaises(PermissionError_):
            plan_mask(Entry("root"), True)

    def test_non_entry_rejected(self):
        with self.assertRaises(PermissionError_):
            plan_mask("not an entry", 0o755)  # type: ignore[arg-type]


class ApplyMaskTests(unittest.TestCase):
    def test_apply_sets_every_mask(self):
        root = Entry("root").add(Entry("a").add(Entry("a1")))
        plan = apply_mask(root, 0o750)
        self.assertEqual(
            plan,
            [("root", 0o750), ("a", 0o750), ("a1", 0o750)],
        )
        self.assertEqual(root.mask, 0o750)
        self.assertEqual(root.children[0].mask, 0o750)
        self.assertEqual(root.children[0].children[0].mask, 0o750)

    def test_apply_respects_overrides(self):
        root = Entry("root").add(
            Entry("a", override=0o700).add(Entry("a1")),
        )
        apply_mask(root, 0o755)
        self.assertEqual(root.mask, 0o755)
        self.assertEqual(root.children[0].mask, 0o700)
        self.assertEqual(root.children[0].children[0].mask, 0o700)

    def test_apply_overwrites_existing_mask(self):
        root = Entry("root", mask=0o777)
        apply_mask(root, 0o644)
        self.assertEqual(root.mask, 0o644)

    def test_duplicate_names_do_not_collide(self):
        # Two distinct entries named "x" must each get the right value; the
        # implementation keys the plan by traversal position, not by name.
        root = Entry("root").add(
            Entry("x", override=0o700),
            Entry("x"),
        )
        apply_mask(root, 0o755)
        self.assertEqual(root.children[0].mask, 0o700)
        self.assertEqual(root.children[1].mask, 0o755)

    def test_apply_returns_plan_matching_plan_mask(self):
        root = Entry("root").add(Entry("a", override=0o700).add(Entry("a1")))
        self.assertEqual(apply_mask(root, 0o755), plan_mask(root, 0o755))


if __name__ == "__main__":
    unittest.main()
