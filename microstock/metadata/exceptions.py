"""Explicit exception hierarchy. CLI exit codes are mapped in cli.py."""


class MicrostockError(Exception):
    """Base class for all application errors."""


class ConfigurationError(MicrostockError):
    """Invalid CLI arguments, config file, or environment setup."""


class UnsupportedImageError(MicrostockError):
    """File extension is not in the supported list."""


class ImageReadError(MicrostockError):
    """Image exists but cannot be opened, decoded, or normalized."""


class ModelLoadError(MicrostockError):
    """Model or processor could not be loaded (incl. OOM, missing backend)."""


class OfflineModelNotFoundError(ModelLoadError):
    """Offline mode requested but no cached/local model files were found."""


class InferenceError(MicrostockError):
    """Generation failed at runtime (recoverable or not, decided by caller)."""


class InvalidModelResponseError(MicrostockError):
    """Model output is not valid JSON or fails schema validation."""


class MetadataValidationError(MicrostockError):
    """Normalized metadata misses required fields (triggers retry)."""


class ExportError(MicrostockError):
    """Output files could not be written."""


class CheckpointError(MicrostockError):
    """Checkpoint state could not be loaded or persisted."""
