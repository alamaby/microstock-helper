"""Core processing utilities for microstock images, vectors, and metadata."""

from .image_ops import convert_image_to_jpeg, batch_convert_to_jpg, is_jpeg_bytes, is_png_bytes
from .renumber import renumber_directory, extract_3digit_number
from .upscaler import upscale_image, batch_upscale
from .tracer import trace_image_to_svg, batch_trace, is_valid_svg
from .vector_ops import convert_svg_to_eps, render_svg_preview, batch_convert_eps, batch_render_previews, is_valid_eps
from .metadata_embed import embed_jpg_file, embed_eps_file, embed_svg_file, find_matching_file, read_metadata_csv
