"""Explicitly synthetic source-shaped input, no HA stubs or network calls."""


def source(family, index, *, date="1960-03-04", precision="day"):
    from custom_components.djconnect import session_facts as facts

    catalog = {
        "uri": f"spotify:track:{index + 1:022d}",
        "title": f"Amber Lines {index + 1}",
        "artist": f"Nora Vale {index + 1}",
        "album_name": f"Paper Windows {index + 1}",
        "album_uri": f"spotify:album:{index + 1:022d}",
        "release_date": date,
        "release_date_precision": precision,
    }
    if family == "edition":
        return catalog, facts.catalog_facts(catalog)[0]
    if family in {"birth", "formation"}:
        fact = facts.artist_facts(
            catalog,
            {
                "id": f"00000000-0000-0000-0000-{index + 1:012d}",
                "name": catalog["artist"],
                "type": "Person" if family == "birth" else "Group",
                "life-span": {"begin": date},
            },
        )[0]
        return catalog, fact
    if family == "description":
        descriptions = {
            "en": "American musician",
            "nl": "Amerikaans musicus",
            "de": "US-amerikanischer Musiker",
            "fr": "musicien américain",
            "es": "músico estadounidense",
        }
        return catalog, facts.description_fact(
            catalog,
            {
                "id": f"Q{index + 1}",
                "descriptions": {lang: {"value": text} for lang, text in descriptions.items()},
            },
            f"Q{index + 1}",
        )
    genre = ("ambient", "jazz", "soul", "pop", "folk", "blues", "rock", "dub")[index % 8]
    return catalog, {
        "track": {
            "title": catalog["title"],
            "artist": catalog["artist"],
            "album": catalog["album_name"],
            "genres": [genre],
        },
        "analysis": {
            "genre": genre,
            "summary": "Source-shaped context.",
            "full_text": f"Existing source-shaped Track Insight context {index}.",
        },
    }
