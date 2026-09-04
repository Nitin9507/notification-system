from django.test import SimpleTestCase

from notifications.renderer import build_context, render_text, resolve_path


class Person:
    def __init__(self, name):
        self.first_name = name
        self._secret = "hidden"


class ResolvePathTests(SimpleTestCase):
    def test_walks_objects_and_dicts(self):
        ctx = {"user": Person("Nitin"), "order": {"total": 499}}
        self.assertEqual(resolve_path(ctx, "user.first_name"), "Nitin")
        self.assertEqual(resolve_path(ctx, "order.total"), 499)

    def test_missing_path_is_empty_not_an_error(self):
        self.assertEqual(resolve_path({}, "user.first_name"), "")

    def test_private_attributes_are_refused(self):
        self.assertEqual(resolve_path({"user": Person("Nitin")}, "user._secret"), "")


class RenderTests(SimpleTestCase):
    def test_variable_map_exposes_placeholders(self):
        ctx = build_context(
            {"name": "user.first_name"}, {"user": Person("Nitin")}
        )
        self.assertEqual(render_text("Hi {{ name }}!", ctx), "Hi Nitin!")

    def test_unknown_placeholder_renders_empty(self):
        self.assertEqual(render_text("Hi {{ nope }}!", {}), "Hi !")

    def test_malformed_template_degrades_to_raw_text(self):
        self.assertEqual(render_text("Hi {% bad %}", {}), "Hi {% bad %}")
