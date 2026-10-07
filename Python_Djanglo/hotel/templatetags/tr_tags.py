from django import template
from hotel import l10n

register = template.Library()


@register.simple_tag(takes_context=True)
def tr(context, key, **kwargs):
    request = context.get("request")
    lang = "en"
    if request is not None:
        lang = request.session.get("lang", "en")
    prev = l10n.CURRENT_LANG
    l10n.CURRENT_LANG = lang
    try:
        return l10n.tr(key, **kwargs)
    finally:
        l10n.CURRENT_LANG = prev
