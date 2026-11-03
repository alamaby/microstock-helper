"""Per-platform publishing profiles. Defaults from knowledge cutoff + local evidence; verify in portals before tightening."""
PLATFORMS = {
    "adobe": {"title_max": 70, "description_max": 200, "kw_min": 25, "kw_max": 49, "kw_style": "phrase", "category_system": "adobe_portal_names"},
    "dreamstime": {"title_max": 200, "description_max": 200, "kw_min": 10, "kw_max": 70, "kw_style": "single", "category_system": "dreamstime_web"},
    "vecteezy": {"title_max": 70, "description_max": 200, "kw_min": 5, "kw_max": 50, "kw_style": "phrase", "category_system": "vecteezy_web"},
    "pixabay": {"title_max": 100, "description_max": 200, "kw_min": 5, "kw_max": 25, "kw_style": "phrase", "category_system": "none"},
}
VECTEEZY_CATEGORY_MAP = {}  # kosong disengaja; diisi S7 dari peta manual, jangan tebak
PIXABAY_MAX_TAGS = 25
