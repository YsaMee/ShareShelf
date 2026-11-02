from datetime import date

from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()

# Item tiles store a short name; these map them to icons in icons.svg.
ITEM_ICONS = {
    "pencil": "pencil",
    "calculator": "calculator",
    "text": "type",
    "ruler": "ruler",
    "notebook": "notebook",
    "scroll": "scroll",
    "book": "book-open",
    "grid": "grid-3x3",
    "package": "package",
    "compass": "drafting-compass",
    "folder": "folder",
}

STATUS_TONES = {
    "Available": "green",
    "Reserved": "amber",
    "Paused": "gray",
    "None left": "gray",
    "Matched": "purple",
    "Requested": "purple",
    "Accepted": "purple",
    "Borrowed": "purple",
    "Lent out": "purple",
    "Returned": "green",
    "Pending": "amber",
    "Fulfilled": "green",
    "Completed": "green",
    "Cancelled": "gray",
    "Declined": "gray",
}


@register.simple_tag
def icon(name, size=16, stroke=2, css_class=""):
    """{% icon "plus" 16 %} draws a Lucide icon from icons.svg."""
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="{}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<use href="{}#{}"></use></svg>',
        css_class, size, size, stroke, static("shelf/icons.svg"), name,
    )


@register.inclusion_tag("shelf/partials/item_icon.html")
def item_icon(item, size="md"):
    return {
        "icon": ITEM_ICONS.get(item.icon, "package"),
        "tone": item.tone or "purple",
        "size": size,
        "px": 28 if size == "lg" else 18,
    }


@register.inclusion_tag("shelf/partials/status_badge.html")
def status_badge(status, pill=False):
    return {"status": status, "tone": STATUS_TONES.get(status, "gray"), "pill": pill}


@register.filter
def lookup(mapping, key):
    """{{ posted|lookup:item.id }} reads mapping[key] in a template."""
    return mapping.get(key, "")


@register.filter
def short_category(category):
    """"Drafting & Arts (Architecture, Fine Arts)" -> "Drafting & Arts" """
    return (category or "").split(" (")[0]


@register.filter
def first_name(full_name):
    return (full_name or "").split(" ")[0]


@register.filter
def nice_date(value):
    """"2026-11-06" -> "Nov 6" """
    if not value:
        return ""
    d = value if isinstance(value, date) else date.fromisoformat(str(value))
    return f"{d:%b} {d.day}"

