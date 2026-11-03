"""Shared constants: exit codes, limits, categories, schema versions."""

EXIT_OK = 0
EXIT_ITEM_FAILURE = 1
EXIT_CONFIG_ERROR = 2
EXIT_MODEL_LOAD_ERROR = 3
EXIT_OUTPUT_ERROR = 4

SCHEMA_VERSION = "1.0"
PROMPT_VERSION = "microstock-v2"  # current default; v1/v3 kept in prompts.py
API_PROMPT_VERSION = "microstock-v3"
DEFAULT_MODEL_ID = "oc/mimo-v2.6-flash-free"

TITLE_MAX_LENGTH = 70
DESCRIPTION_MAX_LENGTH = 200
KEYWORD_MIN_TARGET = 25
KEYWORD_MAX_DEFAULT = 49
KEYWORD_MAX_LENGTH = 60

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")
SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")
DEFAULT_VIDEO_FRAMES = 6
VIDEO_MAX_DURATION_SEC = 30

CATEGORIES = [
    "Animals",
    "Architecture",
    "Backgrounds and Textures",
    "Beauty and Fashion",
    "Business",
    "Education",
    "Food and Drink",
    "Healthcare and Medical",
    "Holidays",
    "Industrial",
    "Nature",
    "People",
    "Religion and Culture",
    "Science",
    "Signs and Symbols",
    "Sports and Fitness",
    "Technology",
    "Transportation",
    "Travel",
    "Other",
]

# Small explicit alias map only. No fuzzy matching (spec: unpredictable).
CATEGORY_ALIASES = {
    "background": "Backgrounds and Textures",
    "backgrounds": "Backgrounds and Textures",
    "texture": "Backgrounds and Textures",
    "textures": "Backgrounds and Textures",
    "fashion": "Beauty and Fashion",
    "beauty": "Beauty and Fashion",
    "food": "Food and Drink",
    "drink": "Food and Drink",
    "drinks": "Food and Drink",
    "health": "Healthcare and Medical",
    "medical": "Healthcare and Medical",
    "healthcare": "Healthcare and Medical",
    "holiday": "Holidays",
    "christmas": "Holidays",
    "sport": "Sports and Fitness",
    "sports": "Sports and Fitness",
    "fitness": "Sports and Fitness",
    "tech": "Technology",
    "transport": "Transportation",
    "car": "Transportation",
    "people": "People",
    "person": "People",
    "animal": "Animals",
    "building": "Architecture",
    "school": "Education",
    "money": "Business",
    "office": "Business",
}
