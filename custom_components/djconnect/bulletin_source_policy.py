"""Closed metadata-summary notices; never permission to reuse linked articles.

The five publisher defaults apply only after intake rejected explicit exceptions.
This policy identifies DJConnect's generated adaptation separately from its
source material. It cannot certify third-party rights absent from feed metadata.
"""
from __future__ import annotations

from .bulletin_intake import NewsItem, SOURCES, article_url


# Reviewed metadata defaults, not a rule for future additions to SOURCES.
SOURCE_DEFAULTS = {
    "cbs": ("CBS", "CC-BY-4.0", "https://www.cbs.nl/nl-nl/over-ons/website/copyright"),
    "knmi": ("KNMI", "CC0-1.0", "https://www.knmi.nl/copyright"),
    "nasa": ("NASA", "NASA-media-guidelines", "https://www.nasa.gov/nasa-brand-center/images-and-media/"),
    "eea": ("European Environment Agency", "CC-BY-4.0", "https://www.eea.europa.eu/en/legal-notice"),
    "eurostat": ("Eurostat", "CC-BY-4.0", "https://ec.europa.eu/eurostat/help/copyright-notice"),
}


NOTICES = {
    "nl": "AI-bewerking door DJConnect, met eventuele vertaling. Bronmateriaal: {sources}. "
        "De bronnen hebben deze samenvatting niet beoordeeld of onderschreven en zijn niet verantwoordelijk voor de inhoud.",
    "en": "AI adaptation by DJConnect, including translation where applicable. Source material: {sources}. "
        "The sources have not reviewed or endorsed this summary and are not responsible for its content.",
    "de": "KI-Bearbeitung durch DJConnect, gegebenenfalls übersetzt. Quellenmaterial: {sources}. "
        "Die Quellen haben diese Zusammenfassung weder geprüft noch gebilligt und sind nicht für ihren Inhalt verantwortlich.",
    "fr": "Adaptation par l’IA de DJConnect, avec traduction éventuelle. Sources : {sources}. "
        "Les sources n’ont ni vérifié ni approuvé ce résumé et ne sont pas responsables de son contenu.",
    "es": "Adaptación por IA de DJConnect, con traducción cuando corresponda. Fuentes: {sources}. "
        "Las fuentes no han revisado ni aprobado este resumen y no son responsables de su contenido.",
}


def qualified_item(item):
    """Accept only the exact fixed publisher/metadata default, never arbitrary labels."""
    if type(item) is not NewsItem:
        return False
    source = next((source for source in SOURCES if source.source_id == item.source_id), None)
    if (source is None or SOURCE_DEFAULTS.get(source.source_id)
            != (source.title, source.license, source.rights_url)
            or item.source_title != source.title or item.license != source.license):
        return False
    try:
        return article_url(item.source_url, source) == item.source_url
    except ValueError:
        return False


def source_notice(items, locale):
    language = locale.replace("_", "-").split("-", 1)[0].lower() if type(locale) is str else ""
    if (language not in NOTICES or len(items) != 2
            or not all(qualified_item(item) for item in items)
            or len({item.source_id for item in items}) != 2):
        raise ValueError("bulletin_source_policy_unavailable")
    return NOTICES[language].format(sources=" / ".join(item.source_title for item in items))


def admitted_text(text, items, locale):
    """Every publication/delivery rechecks the same complete, unstripped notice."""
    try:
        notice = source_notice(items, locale)
    except ValueError:
        return False
    return (type(text) is str and text.endswith("\n\n" + notice)
        and text.count(notice) == 1 and 60 <= len(text.split()) <= 110 and len(text) <= 1200)
