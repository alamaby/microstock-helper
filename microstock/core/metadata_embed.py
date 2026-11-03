"""Metadata injection for JPG (ExifTool triple-sync), EPS (XMP-dc), and SVG (native XML)."""

from __future__ import annotations

import csv
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..preflight import resolve_binary
from .renumber import extract_3digit_number


def run_exiftool(args: List[str], binary_path: Optional[str] = None) -> Tuple[int, str]:
    """Execute ExifTool CLI command."""
    bin_path = resolve_binary("exiftool", binary_path)
    if not bin_path:
        raise FileNotFoundError("ExifTool binary not found. Run preflight check.")

    cmd = [bin_path] + args
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout + res.stderr


def embed_jpg_file(
    file_path: str,
    title: str,
    description: str,
    keywords: List[str],
    copyright: str = "",
    creator: str = "",
    binary_path: Optional[str] = None,
) -> bool:
    """Embed metadata to JPG/PNG using 2-phase ExifTool execution.

    Phase 1: Clear old tags (avoids duplicate concatenation)
    Phase 2: Write clean triple-sync IPTC + XMP + EXIF tags
    """
    is_png = Path(file_path).suffix.lower() == ".png"

    # Phase 1: Reset
    reset_args = [
        "-overwrite_original",
        "-P", "-m",
        "-XMP-dc:Title=", "-IPTC:ObjectName=", "-XMP-photoshop:Headline=",
        "-XMP-dc:Description=", "-IPTC:Caption-Abstract=", "-EXIF:ImageDescription=",
        "-IPTC:Keywords=", "-XMP-dc:Subject=",
    ]
    if copyright:
        reset_args.extend(["-XMP-dc:Rights=", "-IPTC:CopyrightNotice=", "-EXIF:Copyright="])
    if creator:
        reset_args.extend(["-XMP-dc:Creator=", "-IPTC:By-line=", "-EXIF:Artist="])
    reset_args.append(file_path)

    code, _ = run_exiftool(reset_args, binary_path)
    if code != 0:
        return False

    # Phase 2: Write
    write_args = [
        "-overwrite_original",
        "-P", "-m",
        "-IPTC:CodedCharacterSet=UTF8",
        f"-XMP-dc:Title={title}",
        f"-IPTC:ObjectName={title}",
        f"-XMP-photoshop:Headline={title}",
        f"-XMP-dc:Description={description}",
        f"-IPTC:Caption-Abstract={description}",
        f"-EXIF:ImageDescription={description}",
    ]
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        if not is_png:
            write_args.append(f"-IPTC:Keywords+={kw}")
        write_args.append(f"-XMP-dc:Subject+={kw}")

    if copyright:
        write_args.extend([
            f"-XMP-dc:Rights={copyright}",
            f"-IPTC:CopyrightNotice={copyright}",
            f"-EXIF:Copyright={copyright}",
        ])
    if creator:
        write_args.extend([
            f"-XMP-dc:Creator={creator}",
            f"-IPTC:By-line={creator}",
            f"-EXIF:Artist={creator}",
        ])
    write_args.append(file_path)

    code, _ = run_exiftool(write_args, binary_path)
    return code == 0


def embed_eps_file(
    file_path: str,
    title: str,
    description: str,
    keywords: List[str],
    copyright: str = "",
    creator: str = "",
    binary_path: Optional[str] = None,
) -> bool:
    """Embed XMP-dc metadata to PostScript EPS using ExifTool."""
    # Phase 1: Reset
    reset_args = [
        "-overwrite_original",
        "-P", "-m",
        "-XMP-dc:Title=", "-XMP-dc:Description=", "-XMP-dc:Subject=",
    ]
    if copyright:
        reset_args.append("-XMP-dc:Rights=")
    if creator:
        reset_args.append("-XMP-dc:Creator=")
    reset_args.append(file_path)

    code, _ = run_exiftool(reset_args, binary_path)
    if code != 0:
        return False

    # Phase 2: Write
    write_args = [
        "-overwrite_original",
        "-P", "-m",
        f"-XMP-dc:Title={title}",
        f"-XMP-dc:Description={description}",
    ]
    for kw in keywords:
        kw = kw.strip()
        if kw:
            write_args.append(f"-XMP-dc:Subject+={kw}")
    if copyright:
        write_args.append(f"-XMP-dc:Rights={copyright}")
    if creator:
        write_args.append(f"-XMP-dc:Creator={creator}")
    write_args.append(file_path)

    code, _ = run_exiftool(write_args, binary_path)
    return code == 0


def embed_svg_file(
    file_path: str,
    title: str,
    description: str,
    keywords: List[str],
    copyright: str = "",
    creator: str = "",
) -> bool:
    """Embed native XML Dublin Core / RDF metadata into an SVG file."""
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        ET.register_namespace("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        ET.register_namespace("dc", "http://purl.org/dc/elements/1.1/")

        tree = ET.parse(file_path)
        root = tree.getroot()

        # Remove local namespace prefix if present to clean tags
        tag_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag_name.lower() != "svg":
            return False

        # Remove existing title, desc, metadata
        for child in list(root):
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag.lower() in ("title", "desc", "metadata"):
                root.remove(child)

        svg_ns = "http://www.w3.org/2000/svg"
        rdf_ns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        dc_ns = "http://purl.org/dc/elements/1.1/"

        # Create title & desc
        title_elem = ET.Element(f"{{{svg_ns}}}title")
        title_elem.text = title

        desc_elem = ET.Element(f"{{{svg_ns}}}desc")
        desc_elem.text = description or title

        # Create metadata > rdf:RDF > rdf:Description
        meta_elem = ET.Element(f"{{{svg_ns}}}metadata")
        rdf_elem = ET.SubElement(meta_elem, f"{{{rdf_ns}}}RDF")
        desc_rdf = ET.SubElement(rdf_elem, f"{{{rdf_ns}}}Description", {f"{{{rdf_ns}}}about": ""})

        t_dc = ET.SubElement(desc_rdf, f"{{{dc_ns}}}title")
        t_dc.text = title

        d_dc = ET.SubElement(desc_rdf, f"{{{dc_ns}}}description")
        d_dc.text = description or title

        subj_dc = ET.SubElement(desc_rdf, f"{{{dc_ns}}}subject")
        bag = ET.SubElement(subj_dc, f"{{{rdf_ns}}}Bag")
        for kw in keywords:
            kw = kw.strip()
            if kw:
                li = ET.SubElement(bag, f"{{{rdf_ns}}}li")
                li.text = kw

        if copyright:
            r_dc = ET.SubElement(desc_rdf, f"{{{dc_ns}}}rights")
            r_dc.text = copyright
        if creator:
            c_dc = ET.SubElement(desc_rdf, f"{{{dc_ns}}}creator")
            c_dc.text = creator

        # Insert as first children
        root.insert(0, meta_elem)
        root.insert(0, desc_elem)
        root.insert(0, title_elem)

        tmp_out = f"{file_path}.tmp"
        tree.write(tmp_out, encoding="utf-8", xml_declaration=True)
        if os.path.isfile(file_path):
            os.remove(file_path)
        os.rename(tmp_out, file_path)
        return True
    except Exception:
        return False


def find_matching_file(
    available_files: List[str],
    target_name: str,
    allowed_exts: Optional[Tuple[str, ...]] = None,
) -> Optional[str]:
    """Find file in available_files matching target_name exactly or via 3-digit number."""
    stem = Path(target_name).stem.lower()
    exts = tuple(e.lower() for e in allowed_exts) if allowed_exts else None

    # 1. Exact filename match
    for f in available_files:
        p = Path(f)
        if exts and p.suffix.lower() not in exts:
            continue
        if p.name.lower() == target_name.lower():
            return f

    # 2. Exact stem match
    for f in available_files:
        p = Path(f)
        if exts and p.suffix.lower() not in exts:
            continue
        if p.stem.lower() == stem:
            return f

    # 3. 3-digit number match fallback
    num = extract_3digit_number(target_name)
    if num:
        matches = []
        for f in available_files:
            p = Path(f)
            if exts and p.suffix.lower() not in exts:
                continue
            if extract_3digit_number(p.name) == num:
                matches.append(f)
        if len(matches) == 1:
            return matches[0]

    return None


def read_metadata_csv(csv_path: str) -> List[Dict[str, str]]:
    """Read CSV file supporting both Filename and SourceFile headers."""
    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows
