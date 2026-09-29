"""Language codes. English is the default everywhere; Arabic is opt-in (CLAUDE.md §2)."""

DEFAULT_LANGUAGE = "en"

# UI languages that have a locale file. Add a code here + a locale file to add a language.
SUPPORTED_UI_LANGUAGES: tuple[str, ...] = ("en", "ar")

# Languages a site can track. Kept small on purpose; extend as locale support grows.
SUPPORTED_SITE_LANGUAGES: tuple[str, ...] = ("en", "ar", "fr", "de", "es", "tr", "ur", "hi")

RTL_LANGUAGES = frozenset({"ar", "he", "fa", "ur"})


def is_rtl(code: str) -> bool:
    return code.split("-")[0].lower() in RTL_LANGUAGES
