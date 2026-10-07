from .l10n import tr


def ui_prefs(request):
    lang = request.session.get("lang", "en")
    theme = request.session.get("theme", "light")

    def t(key, **kwargs):
        from . import l10n
        prev = l10n.CURRENT_LANG
        l10n.CURRENT_LANG = lang
        try:
            return tr(key, **kwargs)
        finally:
            l10n.CURRENT_LANG = prev

    return {"lang": lang, "theme": theme, "t": t, "tr": t}
