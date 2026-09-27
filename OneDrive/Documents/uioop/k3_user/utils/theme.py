"""Shared guest portal theme helpers."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image

BG = "#EFF5F3"
PAGE = "#F7FBFA"
CARD = "#FFFFFF"
WHITE = CARD
CARD_ALT = "#F8FBFA"
TEAL = "#43BBB4"
TEAL_DARK = "#2B8F8A"
TEAL_LIGHT = "#D8F2EF"
TEAL_LINE = "#55C3BC"
TEXT = "#36414D"
SUBTEXT = "#91A4A8"
DIVIDER = "#E5EEEB"
SAND = "#FFF7E8"
SAND_DARK = "#EAD7B0"
DANGER = "#E47D78"
DANGER_SOFT = "#FBE7E6"
SUCCESS_SOFT = "#E2F7F3"
SUCCESS_TEXT = "#2B8F8A"
AMBER_SOFT = "#F6EBC6"
AMBER_TEXT = "#A07B18"
BLUE_SOFT = "#DDEBFA"
BLUE_TEXT = "#5A84B8"
SHADOW = "#E9F1EF"

STATUS_COLORS = {
    "Available": (SUCCESS_SOFT, SUCCESS_TEXT),
    "Reserved": (AMBER_SOFT, AMBER_TEXT),
    "On Going": (BLUE_SOFT, BLUE_TEXT),
    "Confirmed": (SUCCESS_SOFT, SUCCESS_TEXT),
    "Cancelled": (DANGER_SOFT, DANGER),
    "Rejected": ("#F5D0D0", "#C05050"),
    "Completed": ("#EEF2F3", "#6A7F86"),
    "Pending": ("#F8F2D9", "#A07B18"),
}

DESTINATION_CHIP_COLORS = (
    ("#E8F7F5", TEAL_DARK),
    ("#EAF2FB", "#5A84B8"),
    ("#FFF3E8", "#C68A52"),
)


def make_label(parent, text, size=13, weight="normal", color=TEXT, **kwargs):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=("Segoe UI", size, weight),
        text_color=color,
        **kwargs,
    )


def make_entry(parent, placeholder="", **kwargs):
    return ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        fg_color=SAND,
        border_color=SAND_DARK,
        text_color=TEXT,
        border_width=1,
        corner_radius=10,
        height=42,
        font=("Segoe UI", 12),
        **kwargs,
    )


def make_dropdown(parent, values, **kwargs):
    return ctk.CTkOptionMenu(
        parent,
        values=values,
        fg_color=SAND,
        button_color=SAND,
        button_hover_color="#F5EACE",
        text_color=TEXT,
        corner_radius=10,
        height=42,
        font=("Segoe UI", 12),
        dropdown_fg_color=CARD,
        dropdown_text_color=TEXT,
        dropdown_hover_color=TEAL_LIGHT,
        **kwargs,
    )


def make_button(parent, text, cmd, color=TEAL, hover=TEAL_DARK, fg=CARD, **kwargs):
    height = kwargs.pop("height", 44)
    font = kwargs.pop("font", ("Segoe UI", 13, "bold"))
    return ctk.CTkButton(
        parent,
        text=text,
        command=cmd,
        fg_color=color,
        hover_color=hover,
        text_color=fg,
        corner_radius=12,
        height=height,
        font=font,
        **kwargs,
    )


def make_card(parent, fg_color=CARD, radius=18, border_color=DIVIDER, **kwargs):
    return ctk.CTkFrame(
        parent,
        fg_color=fg_color,
        corner_radius=radius,
        border_width=1,
        border_color=border_color,
        **kwargs,
    )


def make_status_badge(parent, status):
    bg_color, text_color = STATUS_COLORS.get(status, (CARD_ALT, SUBTEXT))
    return ctk.CTkLabel(
        parent,
        text=status,
        fg_color=bg_color,
        text_color=text_color,
        corner_radius=9,
        font=("Segoe UI", 11, "bold"),
        padx=14,
        pady=5,
    )


def make_image(parent, path, size=(280, 180), alt="Cottage Preview"):
    try:
        resolved = Path(path)
        if not resolved.is_absolute():
            guest_root = Path(__file__).resolve().parent.parent
            project_root = guest_root.parent
            candidates = [
                guest_root / resolved,
                project_root / resolved,
            ]
            resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        image = Image.open(resolved)
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        label = ctk.CTkLabel(parent, text="", image=ctk_image)
        label._img_ref = ctk_image
        return label
    except Exception:
        return ctk.CTkLabel(
            parent,
            text=f"[Image] {alt}",
            fg_color=CARD_ALT,
            text_color=SUBTEXT,
            width=size[0],
            height=size[1],
            corner_radius=14,
            font=("Segoe UI", 12, "bold"),
        )


def make_navbar(parent, title, back_cmd=None, logout_cmd=None):
    nav = ctk.CTkFrame(parent, fg_color=CARD, height=62, corner_radius=0)
    nav.pack(fill="x")
    nav.pack_propagate(False)

    if back_cmd:
        make_button(
            nav,
            "Back",
            back_cmd,
            color="transparent",
            hover=TEAL_LIGHT,
            fg=TEAL_DARK,
            width=92,
            height=36,
        ).place(x=18, rely=0.5, anchor="w")

    make_label(nav, title, 16, "bold", color=TEXT).place(relx=0.5, rely=0.5, anchor="center")

    if logout_cmd:
        make_button(
            nav,
            "Log Out",
            logout_cmd,
            color=DANGER_SOFT,
            hover="#F7D9D7",
            fg=DANGER,
            width=102,
            height=36,
        ).place(relx=1.0, x=-18, rely=0.5, anchor="e")

    return nav


def top_strip(parent, title, subtitle="", right_text="", right_cmd=None):
    # Base container
    strip = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=0, height=78)
    strip.grid_columnconfigure(0, weight=1)
    strip.grid_columnconfigure(1, weight=0)
    strip.grid_rowconfigure(0, weight=1)
    strip.grid_rowconfigure(1, weight=1)

    # Content layout
    make_label(strip, title, 20, "bold", color=TEXT).grid(
        row=0,
        column=0,
        sticky="sw",
        padx=(24, 18),
        pady=(10, 2),
    )
    if subtitle:
        make_label(strip, subtitle, 12, color=SUBTEXT).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=(24, 18),
            pady=(2, 10),
        )
    else:
        # Pad bottom if no subtitle
        strip.grid_rowconfigure(1, weight=0)
        make_label(strip, "", 1).grid(row=1, column=0, pady=(0, 10))

    if right_text and right_cmd is not None:
        is_danger = right_text.lower().startswith("log")
        make_button(
            strip,
            right_text,
            right_cmd,
            color=DANGER_SOFT if is_danger else TEAL_LIGHT,
            hover="#F7D9D7" if is_danger else "#BFE5E1",
            fg=DANGER if is_danger else TEAL_DARK,
            width=120,
            height=38,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, rowspan=2, padx=40, pady=18, sticky="e")
    
    # Subtle bottom border
    ctk.CTkFrame(strip, fg_color=DIVIDER, height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
    
    return strip


def info_chip(parent, text, bg_color, fg_color):
    return ctk.CTkLabel(
        parent,
        text=text,
        fg_color=bg_color,
        text_color=fg_color,
        corner_radius=8,
        font=("Segoe UI", 10, "bold"),
        padx=12,
        pady=5,
    )
