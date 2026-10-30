#!/usr/bin/env python3
"""Add outline boxes and a separate, wrapped legend to a screenshot.

Requires Pillow. Coordinates refer to the unscaled source image's pixel grid.
The source image is never overwritten; the output is always PNG.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow is required. Install it with: python -m pip install Pillow")


PALETTE = ["#C2410C", "#1D4ED8", "#047857", "#7E22CE", "#BE123C", "#0369A1"]


def positive_integer(value: object, name: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def validate_annotations(data: object, image_size: tuple[int, int]) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("annotations must be a JSON object")
    expected = (
        positive_integer(data.get("image_width"), "image_width"),
        positive_integer(data.get("image_height"), "image_height"),
    )
    if expected != image_size:
        raise ValueError(f"dimension mismatch: annotations {expected}, source image {image_size}")
    boxes = data.get("boxes")
    if not isinstance(boxes, list) or not boxes:
        raise ValueError("boxes must be a non-empty array")
    seen_ids: set[str] = set()
    normalized = []
    for index, box in enumerate(boxes):
        prefix = f"boxes[{index}]"
        if not isinstance(box, dict):
            raise ValueError(f"{prefix} must be an object")
        box_id, label = box.get("id"), box.get("label")
        for field, value in [("id", box_id), ("label", label)]:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{prefix}.{field} must be a non-empty string")
        if box_id in seen_ids:
            raise ValueError(f"duplicate box id: {box_id}")
        seen_ids.add(box_id)
        x = positive_integer(box.get("x"), f"{prefix}.x", allow_zero=True)
        y = positive_integer(box.get("y"), f"{prefix}.y", allow_zero=True)
        width = positive_integer(box.get("width"), f"{prefix}.width")
        height = positive_integer(box.get("height"), f"{prefix}.height")
        if x + width > image_size[0] or y + height > image_size[1]:
            raise ValueError(f"{prefix} exceeds source image bounds")
        normalized.append({"id": box_id, "x": x, "y": y, "width": width,
                           "height": height, "label": label.strip()})
    return normalized


def resolve_font(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"font not found: {path}")
        return path
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [
        windows_fonts / "msyh.ttc", windows_fonts / "msjh.ttc",
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError("No Chinese system font found. Provide --font /absolute/path/to/font.ttf")


def wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont,
              max_width: int) -> list[str]:
    """Character wrapping handles Chinese and long URLs without truncation."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for char in paragraph:
            candidate = line + char
            if line and draw.textlength(candidate, font=font) > max_width:
                lines.append(line)
                line = char
            else:
                line = candidate
        lines.append(line)
    return lines


def annotate(image_path: Path, annotations_path: Path, output_path: Path,
             font_path: str | None = None) -> dict:
    image_path = image_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    annotations_path = annotations_path.expanduser().resolve()
    if image_path == output_path:
        raise ValueError("output must not overwrite the source image")
    if output_path.suffix.lower() != ".png":
        raise ValueError("output must have a .png extension")
    metadata_path = output_path.with_suffix(".annotations.json")
    if metadata_path in (image_path, annotations_path) or output_path == annotations_path:
        raise ValueError("output paths must not overwrite the source image or annotations")
    if output_path.exists() or metadata_path.exists():
        raise ValueError("output image or metadata already exists; choose a new output path")
    source_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    data = json.loads(annotations_path.read_text(encoding="utf-8-sig"))
    with Image.open(image_path) as opened:
        source = opened.convert("RGB")
    boxes = validate_annotations(data, source.size)
    selected_font = resolve_font(font_path)
    font_size = 22
    font = ImageFont.truetype(str(selected_font), font_size)
    heading_font = ImageFont.truetype(str(selected_font), 25)
    line_height = sum(font.getmetrics()) + 6
    legend_width, padding = 420, 24
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    wrapped = [wrap_text(f"{box['id']}  {box['label']}", probe, font,
                         legend_width - padding * 2) for box in boxes]
    legend_height = 108 + sum(len(lines) * line_height + 24 for lines in wrapped)
    canvas = Image.new("RGB", (source.width + legend_width, max(source.height, legend_height)), "#F8FAFC")
    canvas.paste(source, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.line((source.width, 0, source.width, canvas.height), fill="#CBD5E1", width=1)
    legend_x = source.width + padding
    draw.text((legend_x, padding), "证据标注 / Evidence", font=heading_font, fill="#0F172A")
    draw.text((legend_x, padding + 40), "编号对应原图中的彩色边框", font=font, fill="#475569")
    legend_y = 108
    for index, (box, lines) in enumerate(zip(boxes, wrapped)):
        color = PALETTE[index % len(PALETTE)]
        x, y, width, height = (box[key] for key in ("x", "y", "width", "height"))
        # Outlines only: labels and filled blocks never obscure the original text.
        stroke = max(1, min(3, width // 2, height // 2))
        draw.rectangle((x, y, x + width - 1, y + height - 1), outline=color, width=stroke)
        for line in lines:
            draw.text((legend_x, legend_y), line, font=font, fill=color)
            legend_y += line_height
        legend_y += 24
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG")
    metadata = {
        "source_image": str(image_path), "source_sha256": source_hash,
        "image_width": source.width, "image_height": source.height,
        "annotated_image": str(output_path), "output_width": canvas.width,
        "output_height": canvas.height, "font": str(selected_font), "boxes": boxes,
        "coordinate_system": "unscaled source pixels; x/y origin is top-left",
        "note": "Only outlines are added over source pixels; all labels are in a separate right legend.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output_path), "metadata": str(metadata_path), "boxes": len(boxes)}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font", help="Chinese-capable TTF/OTF/TTC path; auto-detected if omitted")
    args = parser.parse_args()
    try:
        result = annotate(args.image, args.annotations, args.output, args.font)
    except (OSError, ValueError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
