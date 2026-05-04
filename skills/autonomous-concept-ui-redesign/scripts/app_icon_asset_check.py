#!/usr/bin/env python3
"""Check a transparent app icon master and optionally export Windows .ico assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - depends on local environment
    raise SystemExit(
        "Pillow is required. Install it in the active Python environment with: python -m pip install Pillow"
    ) from exc


DEFAULT_SIZES = (256, 128, 64, 48, 32, 16)


def parse_sizes(value: str) -> tuple[int, ...]:
    sizes: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        size = int(item)
        if size <= 0:
            raise argparse.ArgumentTypeError("sizes must be positive integers")
        sizes.append(size)
    if not sizes:
        raise argparse.ArgumentTypeError("at least one size is required")
    return tuple(sorted(set(sizes), reverse=True))


def has_alpha(image: Image.Image) -> bool:
    return "A" in image.getbands() or "transparency" in image.info


def corner_alpha_values(image: Image.Image) -> dict[str, int]:
    alpha = image.getchannel("A")
    width, height = image.size
    return {
        "top_left": int(alpha.getpixel((0, 0))),
        "top_right": int(alpha.getpixel((width - 1, 0))),
        "bottom_left": int(alpha.getpixel((0, height - 1))),
        "bottom_right": int(alpha.getpixel((width - 1, height - 1))),
    }


def max_border_alpha(image: Image.Image, border: int) -> int:
    alpha = image.getchannel("A")
    width, height = image.size
    border = max(1, min(border, width, height))
    edges = [
        alpha.crop((0, 0, width, border)),
        alpha.crop((0, height - border, width, height)),
        alpha.crop((0, 0, border, height)),
        alpha.crop((width - border, 0, width, height)),
    ]
    return max(max(edge.getdata()) for edge in edges)


def alpha_bbox_ratio(image: Image.Image, threshold: int) -> float:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return 0.0
    left, top, right, bottom = bbox
    bbox_area = (right - left) * (bottom - top)
    width, height = image.size
    return bbox_area / float(width * height)


def save_previews(image: Image.Image, preview_dir: Path, sizes: tuple[int, ...]) -> list[str]:
    preview_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    backgrounds = {
        "light": (245, 246, 248, 255),
        "dark": (24, 25, 28, 255),
    }
    for size in sizes:
        resized = image.resize((size, size), Image.Resampling.LANCZOS)
        for name, color in backgrounds.items():
            canvas = Image.new("RGBA", (size, size), color)
            canvas.alpha_composite(resized)
            out = preview_dir / f"icon_{size}_{name}.png"
            canvas.convert("RGB").save(out)
            paths.append(str(out))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a transparent app icon PNG and optionally export a multi-size Windows .ico."
    )
    parser.add_argument("--input", required=True, type=Path, help="Transparent PNG/WebP icon master.")
    parser.add_argument("--ico-out", type=Path, help="Optional .ico output path.")
    parser.add_argument("--preview-dir", type=Path, help="Optional directory for light/dark size previews.")
    parser.add_argument("--sizes", type=parse_sizes, default=DEFAULT_SIZES, help="Comma-separated sizes. Default: 256,128,64,48,32,16.")
    parser.add_argument("--corner-alpha-threshold", type=int, default=8, help="Maximum accepted alpha for corner pixels.")
    parser.add_argument("--border-alpha-threshold", type=int, default=8, help="Maximum accepted alpha on the outer 1%% border.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    source = args.input
    image = Image.open(source)
    source_has_alpha = has_alpha(image)
    rgba = image.convert("RGBA")
    width, height = rgba.size
    border_width = max(1, int(round(min(width, height) * 0.01)))
    corners = corner_alpha_values(rgba)
    max_corner_alpha = max(corners.values())
    border_alpha = max_border_alpha(rgba, border_width)
    bbox_ratio = alpha_bbox_ratio(rgba, args.corner_alpha_threshold)

    failures: list[str] = []
    warnings: list[str] = []

    if not source_has_alpha:
        failures.append("source image has no alpha/transparency channel")
    if max_corner_alpha > args.corner_alpha_threshold:
        failures.append("one or more corners are not transparent")
    if border_alpha > args.border_alpha_threshold:
        warnings.append("visible pixels touch the outer border; add padding or remove an opaque tile")
    if width != height:
        warnings.append("source image is not square; app icons usually need a square master")
    if bbox_ratio > 0.86:
        warnings.append("opaque content covers most of the canvas; check for a square tile or framed card")
    if bbox_ratio < 0.12:
        warnings.append("visible mark is very small; check whether the taskbar icon will be recognizable")

    ico_path = None
    if args.ico_out:
        args.ico_out.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(args.ico_out, format="ICO", sizes=[(size, size) for size in args.sizes])
        ico_path = str(args.ico_out)

    preview_paths: list[str] = []
    if args.preview_dir:
        preview_paths = save_previews(rgba, args.preview_dir, args.sizes)

    result = {
        "status": "fail" if failures else "pass",
        "input": str(source),
        "size": {"width": width, "height": height},
        "has_alpha": source_has_alpha,
        "corner_alpha": corners,
        "max_border_alpha": border_alpha,
        "alpha_bbox_ratio": round(bbox_ratio, 4),
        "sizes": list(args.sizes),
        "ico_out": ico_path,
        "preview_paths": preview_paths,
        "failures": failures,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Status: {result['status']}")
        if failures:
            print("Failures:")
            for item in failures:
                print(f"- {item}")
        if warnings:
            print("Warnings:")
            for item in warnings:
                print(f"- {item}")
        if ico_path:
            print(f"ICO: {ico_path}")
        if preview_paths:
            print(f"Previews: {len(preview_paths)} files in {args.preview_dir}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
