"""Template tags for in-template obfuscation.

Usage in templates:

    {% load obfuscator_tags %}
    {% obfuscate %}
       ...your HTML content...
    {% endobfuscate %}

Or for inline text:

    {% load obfuscator_tags %}
    <p>{% obfuscate_text book.title %}</p>

The tags look up the current site from the template context variable `site`
(automatically provided by the Sites app via the theme renderer).
"""

from django import template
from django.template.base import Node, TemplateSyntaxError, token_kwargs
from django.utils.safestring import mark_safe

from apps.sites.models import Site

from ..engine import apply_obfuscation, apply_text_only


register = template.Library()


# ------------------------------------------------------------------
# Block tag: {% obfuscate %} ... {% endobfuscate %}
# ------------------------------------------------------------------
class ObfuscateNode(Node):
    def __init__(self, nodelist, site_expr=None):
        self.nodelist = nodelist
        self.site_expr = site_expr

    def render(self, context):
        rendered = self.nodelist.render(context)
        site = None
        if self.site_expr:
            try:
                site = self.site_expr.resolve(context)
            except Exception:
                site = None
        if site is None:
            # Try to get `site` from the context (set by theme renderer)
            site = context.get("site")
        if not site or not isinstance(site, Site):
            return rendered
        try:
            return mark_safe(apply_obfuscation(rendered, site=site))
        except Exception:
            return rendered


@register.tag(name="obfuscate")
def do_obfuscate(parser, token):
    nodelist = parser.parse(("endobfuscate",))
    parser.delete_first_token()
    # Optional: {% obfuscate site=... %}
    bits = token.split_contents()[1:]
    site_expr = None
    if bits:
        kwargs = token_kwargs(bits, parser, template.loader.Loader())
        site_expr = kwargs.get("site")
    return ObfuscateNode(nodelist, site_expr)


# ------------------------------------------------------------------
# Inline filter: {{ value|obfuscate_text }}
# ------------------------------------------------------------------
@register.filter(name="obfuscate_text")
def obfuscate_text(value, site=None):
    """Apply Layer 2 + Layer 3 only (text-only, no HTML structure work)."""
    if not value:
        return value
    if not site:
        return value
    try:
        return mark_safe(apply_text_only(str(value), site=site))
    except Exception:
        return value


@register.simple_tag(takes_context=True)
def obfuscate_for_site(context, value):
    """Like {% obfuscate_text %} but auto-pulls site from context."""
    site = context.get("site")
    return obfuscate_text(value, site)
