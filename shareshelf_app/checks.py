from django.core.checks import Error, register

from . import logic


@register()
def swipl_installed(app_configs, **kwargs):
    """ShareShelf's matching and request rules run in SWI-Prolog, so it must be installed."""
    if logic.swipl_path():
        return []
    return [Error(
        "SWI-Prolog isn't installed, so matching and the request rules can't run.",
        hint="Install it from https://www.swi-prolog.org/download/stable, "
             "or set SWIPL_PATH to the full path of swipl.",
        id="shareshelf_app.E001",
    )]
