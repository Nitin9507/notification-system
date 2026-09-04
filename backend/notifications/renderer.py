"""
Template rendering: variable mapping + placeholder substitution.

Two steps, deliberately separate:

1. The template's ``variables`` map turns the raw trigger context into the
   placeholders an admin is allowed to type, e.g. ``{"first_name":
   "user.first_name"}`` makes ``{{ first_name }}`` available.
2. The resulting context is applied to the body with Django's template engine,
   with autoescaping off (these are plain-text messages, not HTML pages).

Admins are not developers, so an unknown placeholder must never raise — it
renders as an empty string, exactly like Django templates do elsewhere.
"""

from typing import Any, Mapping

from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

_MISSING = object()


def resolve_path(context: Mapping[str, Any], path: str) -> Any:
    """
    Walk a dotted path through dicts and objects.

    ``resolve_path({"user": user}, "user.first_name")`` -> ``user.first_name``.
    Returns ``""`` rather than raising when any segment is missing, and never
    reaches private attributes.
    """
    current: Any = context
    for part in path.split("."):
        if part.startswith("_"):
            return ""
        if isinstance(current, Mapping):
            current = current.get(part, _MISSING)
        else:
            current = getattr(current, part, _MISSING)
        if current is _MISSING or current is None:
            return ""
        if callable(current):
            current = current()
    return current


def build_context(variables: Mapping[str, str] | None, base: Mapping[str, Any]) -> dict:
    """Merge the raw trigger context with the template's mapped variables."""
    ctx = dict(base)
    for placeholder, source_path in (variables or {}).items():
        ctx[placeholder] = resolve_path(base, str(source_path))
    return ctx


def render_text(text: str, ctx: Mapping[str, Any]) -> str:
    """Render one plain-text string. A malformed template degrades to raw text."""
    if not text:
        return ""
    try:
        return Template(text).render(Context(dict(ctx), autoescape=False))
    except TemplateSyntaxError:
        return text
