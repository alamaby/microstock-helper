"""Convert generator metadata.csv into ExifTool embed templates.

Reads the generator output (filename,title,description,keywords,...) and
writes the two per-agency CSVs consumed by Embed-JpgMetadata.ps1:

- Adobe template: titles/descriptions/phrase keywords as generated.
- Dreamstime template: keywords split into single lowercase words
  (Dreamstime splits phrases on spaces), stopwords dropped, capped.

Only rows with real content are converted (failed/empty rows skipped).
"""

from __future__ import annotations

import csv

STOPWORDS = frozenset(
    {"and", "or", "the", "a", "an", "of", "for", "with", "to", "in", "on", "no"}
)

DREAMSTIME_MAX_WORDS = 70
VECTEEZY_MAX_TAGS = 50
PIXABAY_MAX_TAGS = 25
EMBED_COLUMNS = ["SourceFile", "Title", "Description", "Keywords", "Copyright", "Creator"]
ADOBE_COLUMNS = ["Filename", "Title", "Description", "Keywords", "Category", "Releases", "Copyright", "Creator"]
VIDEO_ADOBE_COLUMNS = ["Filename", "Title", "Description", "Keywords", "Category", "Releases", "Copyright", "Creator", "IsAIGenerated"]
VECTEEZY_COLUMNS = ["Filename", "Title", "Description", "Keywords", "Copyright", "Creator"]
PIXABAY_COLUMNS = ["Filename", "Title", "Description", "Keywords", "Copyright", "Creator"]

# Generator category name -> closest official Adobe Stock portal category name
# ("Choose the right category for your content", helpx, Jun 2026).
# "Other"/unknown -> "" (left blank for Sensei/portal to suggest).
# NOTE: the official CSV spec asks for the category NUMBER (from the portal
# upload-CSV dialog), not the name. Names are used here so the mapping stays
# verifiable against the article; swap to numbers once confirmed from portal.
# Keep in sync with Orchestrate-Stock.ps1 $script:AdobeCategoryMap.
ADOBE_CATEGORY_MAP = {
    "animals": "Animals",
    "architecture": "Buildings and architecture",
    "backgrounds and textures": "Graphic resources",
    "beauty and fashion": "People",
    "business": "Business",
    "education": "People",
    "food and drink": "Food",
    "healthcare and medical": "Science",
    "holidays": "Culture and religion",
    "industrial": "Industry",
    "nature": "The environment",
    "people": "People",
    "religion and culture": "Culture and religion",
    "science": "Science",
    "signs and symbols": "Graphic resources",
    "sports and fitness": "Sports",
    "technology": "Technology",
    "transportation": "Transport",
    "travel": "Travel",
    "other": "",
}


def adobe_category(generator_category: object) -> str:
    """Map a generator category name to the closest Adobe portal category."""
    key = (generator_category or "").strip().lower() if isinstance(generator_category, str) else ""
    if not key:
        return ""
    return ADOBE_CATEGORY_MAP.get(key, "")


def split_single_words(keywords_cell: str) -> list[str]:
    """Comma phrases -> unique lowercase single words, order preserved."""
    words: list[str] = []
    for phrase in (keywords_cell or "").split(","):
        for token in phrase.strip().split():
            word = token.strip().lower()
            if word and word not in STOPWORDS and word not in words:
                words.append(word)
    return words


def convert_rows(rows: list[dict], copyright_: str, creator: str) -> tuple[list[dict], list[dict], dict]:
    """Return (adobe_rows, dreamstime_rows, counts). Skips empty/failed rows."""
    adobe: list[dict] = []
    dream: list[dict] = []
    skipped = 0
    for row in rows:
        if row.get("status") not in ("success", "skipped"):
            skipped += 1
            continue
        title = (row.get("title") or "").strip()
        keywords = (row.get("keywords") or "").strip()
        if not title or not keywords:
            skipped += 1
            continue
        fname = (row.get("filename") or "").strip()
        base = {
            "Title": title,
            "Description": (row.get("description") or "").strip(),
            "Copyright": copyright_,
            "Creator": creator,
        }
        adobe.append({**base, "Filename": fname, "Keywords": keywords,
                      "Category": adobe_category(row.get("category")), "Releases": ""})
        words = split_single_words(keywords)[:DREAMSTIME_MAX_WORDS]
        dream.append({**base, "SourceFile": fname, "Keywords": ", ".join(words)})
    return adobe, dream, {"converted": len(adobe), "skipped": skipped}


def convert_file(input_path: str, adobe_path: str, dreamstime_path: str,
                 copyright_: str = "alamaby", creator: str = "alamaby") -> dict:
    with open(input_path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    adobe, dream, counts = convert_rows(rows, copyright_, creator)
    for path, data, columns in ((adobe_path, adobe, ADOBE_COLUMNS),
                                (dreamstime_path, dream, EMBED_COLUMNS)):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
    return counts


def cap_phrase_keywords(keywords_cell: str, cap: int) -> str:
    """Keep original phrase order, cut to cap phrases."""
    phrases = [p.strip() for p in (keywords_cell or "").split(",") if p.strip()]
    return ", ".join(phrases[:cap])


def convert_video_rows(
    rows: list[dict], copyright_: str, creator: str
) -> tuple[dict[str, list[dict]], dict]:
    """Return dict platform -> rows for video. Skips failed/empty like convert_rows."""
    out = {"adobe": [], "dreamstime": [], "vecteezy": [], "pixabay": []}
    skipped = 0
    for row in rows:
        if row.get("status") not in ("success", "skipped"):
            skipped += 1
            continue
        if (row.get("media_type") or "") not in ("", "video", "image"):
            skipped += 1
            continue
        title = (row.get("title") or "").strip()
        keywords = (row.get("keywords") or "").strip()
        if not title or not keywords:
            skipped += 1
            continue
        fname = (row.get("filename") or "").strip()
        desc = (row.get("description") or "").strip()
        media_type = (row.get("media_type") or "").strip()

        out["adobe"].append({
            "Filename": fname,
            "Title": title[:70].rstrip(),
            "Description": desc[:200],
            "Keywords": cap_phrase_keywords(keywords, 49),
            "Category": adobe_category(row.get("category")),
            "Releases": "",
            "Copyright": copyright_,
            "Creator": creator,
            "IsAIGenerated": "yes" if media_type == "video" else "",
        })

        words = split_single_words(keywords)[:DREAMSTIME_MAX_WORDS]
        out["dreamstime"].append({
            "SourceFile": fname,
            "Title": title[:200].rstrip(),
            "Description": (desc or title)[:200],
            "Keywords": ", ".join(words),
            "Copyright": copyright_,
            "Creator": creator,
        })

        out["vecteezy"].append({
            "Filename": fname,
            "Title": title[:70].rstrip(),
            "Description": desc[:200],
            "Keywords": cap_phrase_keywords(keywords, VECTEEZY_MAX_TAGS),
            "Copyright": copyright_,
            "Creator": creator,
        })

        out["pixabay"].append({
            "Filename": fname,
            "Title": title[:100].rstrip(),
            "Description": desc[:200],
            "Keywords": cap_phrase_keywords(keywords, PIXABAY_MAX_TAGS),
            "Copyright": copyright_,
            "Creator": creator,
        })

    return out, {"converted": len(out["adobe"]), "skipped": skipped}


def convert_video_file(
    input_path: str,
    adobe_path: str | None = None,
    dreamstime_path: str | None = None,
    vecteezy_path: str | None = None,
    pixabay_path: str | None = None,
    copyright_: str = "alamaby",
    creator: str = "alamaby",
) -> tuple[dict, dict[str, int]]:
    with open(input_path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out, counts = convert_video_rows(rows, copyright_, creator)
    platform_targets = [
        (adobe_path, out["adobe"], VIDEO_ADOBE_COLUMNS),
        (dreamstime_path, out["dreamstime"], EMBED_COLUMNS),
        (vecteezy_path, out["vecteezy"], VECTEEZY_COLUMNS),
        (pixabay_path, out["pixabay"], PIXABAY_COLUMNS),
    ]
    platform_counts: dict[str, int] = {}
    for path, data, columns in platform_targets:
        if path:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
            platform_counts[path] = len(data)
    return counts, platform_counts


def convert_to_all_platforms(
    input_path: str,
    out_dir: str,
    copyright_: str = "alamaby",
    creator: str = "alamaby",
) -> dict[str, str]:
    """Convert master CSV into 4 agency-specific CSV files in out_dir."""
    import os
    from pathlib import Path

    base_name = Path(input_path).stem
    if base_name.endswith("_metadata"):
        prefix = base_name[:-9] + "_"
    elif base_name == "metadata":
        prefix = ""
    else:
        prefix = f"{base_name}_"

    adobe_path = os.path.join(out_dir, f"{prefix}metadata_adobe.csv" if prefix else "metadata_adobe.csv")
    dream_path = os.path.join(out_dir, f"{prefix}metadata_dreamstime.csv" if prefix else "metadata_dreamstime.csv")
    vec_path = os.path.join(out_dir, f"{prefix}metadata_vecteezy.csv" if prefix else "metadata_vecteezy.csv")
    pix_path = os.path.join(out_dir, f"{prefix}metadata_pixabay.csv" if prefix else "metadata_pixabay.csv")

    convert_video_file(
        input_path,
        adobe_path=adobe_path,
        dreamstime_path=dream_path,
        vecteezy_path=vec_path,
        pixabay_path=pix_path,
        copyright_=copyright_,
        creator=creator,
    )
    return {
        "adobe": adobe_path,
        "dreamstime": dream_path,
        "vecteezy": vec_path,
        "pixabay": pix_path,
    }


