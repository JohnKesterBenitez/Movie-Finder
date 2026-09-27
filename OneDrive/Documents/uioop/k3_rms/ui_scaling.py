"""Responsive UI scaling helpers for CustomTkinter windows."""

from __future__ import annotations

from dataclasses import dataclass
import math

import customtkinter as ctk


@dataclass(frozen=True)
class ScreenProfile:
    screen_width: int
    screen_height: int
    scale: float


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def compute_screen_profile(
    screen_width: int,
    screen_height: int,
    *,
    baseline_width: int = 1440,
    baseline_height: int = 900,
    min_scale: float = 1.0,
    max_scale: float = 1.28,
) -> ScreenProfile:
    """Return a balanced scaling profile based on the device screen size."""
    width_ratio = float(screen_width) / float(baseline_width)
    height_ratio = float(screen_height) / float(baseline_height)
    raw_scale = math.sqrt(width_ratio * height_ratio)
    scale = _clamp(raw_scale, min_scale, max_scale)
    return ScreenProfile(
        screen_width=int(screen_width),
        screen_height=int(screen_height),
        scale=round(scale, 3),
    )


def apply_customtkinter_scaling(
    screen_width: int,
    screen_height: int,
    *,
    baseline_width: int = 1440,
    baseline_height: int = 900,
    min_scale: float = 1.0,
    max_scale: float = 1.28,
) -> ScreenProfile:
    """Compute and apply a shared CustomTkinter scaling factor."""
    profile = compute_screen_profile(
        screen_width,
        screen_height,
        baseline_width=baseline_width,
        baseline_height=baseline_height,
        min_scale=min_scale,
        max_scale=max_scale,
    )
    ctk.set_widget_scaling(profile.scale)
    ctk.set_window_scaling(profile.scale)
    return profile
