# -*- coding: utf-8 -*-
"""GHDI -> Bootstrap migration helper (asset generator, phase 1).

Generates:
  static/css/ghdi-compat.css  - Tailwind-utility compat layer, built ONLY from
                                the class tokens that templates actually use
  static/css/ghdi-theme.css   - brand tokens, surfaces, dark/light mode
  static/js/ghdi-ui.js        - progress bar, theme toggle, toasts
and writes MIGRATION_REPORT.txt.

Idempotent: safe to re-run.
"""
import os
import re
import io
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

LOG = []


def out(s=""):
    LOG.append(str(s))
    print(s)


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ----------------------------------------------------------------- palette
C = {
    "white": "#ffffff", "black": "#000000", "transparent": "transparent",
    "current": "currentColor", "inherit": "inherit",
    "ghdi-navy": "#011f5b", "ghdi-accent": "#eb0160",
    "ghdi-azure": "#0081d2", "ghdi-amber": "#fd9a01",
}
PAL = {
    "slate":   ["#f8fafc", "#f1f5f9", "#e2e8f0", "#cbd5e1", "#94a3b8", "#64748b",
                "#475569", "#334155", "#1e293b", "#0f172a", "#020617"],
    "gray":    ["#f9fafb", "#f3f4f6", "#e5e7eb", "#d1d5db", "#9ca3af", "#6b7280",
                "#4b5563", "#374151", "#1f2937", "#111827", "#030712"],
    "zinc":    ["#fafafa", "#f4f4f5", "#e4e4e7", "#d4d4d8", "#a1a1aa", "#71717a",
                "#52525b", "#3f3f46", "#27272a", "#18181b", "#09090b"],
    "red":     ["#fef2f2", "#fee2e2", "#fecaca", "#fca5a5", "#f87171", "#ef4444",
                "#dc2626", "#b91c1c", "#991b1b", "#7f1d1d", "#450a0a"],
    "rose":    ["#fff1f2", "#ffe4e6", "#fecdd3", "#fda4af", "#fb7185", "#f43f5e",
                "#e11d48", "#be123c", "#9f1239", "#881337", "#4c0519"],
    "green":   ["#f0fdf4", "#dcfce7", "#bbf7d0", "#86efac", "#4ade80", "#22c55e",
                "#16a34a", "#15803d", "#166534", "#14532d", "#052e16"],
    "emerald": ["#ecfdf5", "#d1fae5", "#a7f3d0", "#6ee7b7", "#34d399", "#10b981",
                "#059669", "#047857", "#065f46", "#064e3b", "#022c22"],
    "teal":    ["#f0fdfa", "#ccfbf1", "#99f6e4", "#5eead4", "#2dd4bf", "#14b8a6",
                "#0d9488", "#0f766e", "#115e59", "#134e4a", "#042f2e"],
    "blue":    ["#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6",
                "#2563eb", "#1d4ed8", "#1e40af", "#1e3a8a", "#172554"],
    "sky":     ["#f0f9ff", "#e0f2fe", "#bae6fd", "#7dd3fc", "#38bdf8", "#0ea5e9",
                "#0284c7", "#0369a1", "#075985", "#0c4a6e", "#082f49"],
    "indigo":  ["#eef2ff", "#e0e7ff", "#c7d2fe", "#a5b4fc", "#818cf8", "#6366f1",
                "#4f46e5", "#4338ca", "#3730a3", "#312e81", "#1e1b4b"],
    "violet":  ["#f5f3ff", "#ede9fe", "#ddd6fe", "#c4b5fd", "#a78bfa", "#8b5cf6",
                "#7c3aed", "#6d28d9", "#5b21b6", "#4c1d95", "#2e1065"],
    "purple":  ["#faf5ff", "#f3e8ff", "#e9d5ff", "#d8b4fe", "#c084fc", "#a855f7",
                "#9333ea", "#7e22ce", "#6b21a8", "#581c87", "#3b0764"],
    "amber":   ["#fffbeb", "#fef3c7", "#fde68a", "#fcd34d", "#fbbf24", "#f59e0b",
                "#d97706", "#b45309", "#92400e", "#78350f", "#451a03"],
    "yellow":  ["#fefce8", "#fef9c3", "#fef08a", "#fde047", "#facc15", "#eab308",
                "#ca8a04", "#a16207", "#854d0e", "#713f12", "#422006"],
    "orange":  ["#fff7ed", "#ffedd5", "#fed7aa", "#fdba74", "#fb923c", "#f97316",
                "#ea580c", "#c2410c", "#9a3412", "#7c2d12", "#431407"],
    "cyan":    ["#ecfeff", "#cffafe", "#a5f3fc", "#67e8f9", "#22d3ee", "#06b6d4",
                "#0891b2", "#0e7490", "#155e75", "#164e63", "#083344"],
}
NUMS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
for _p, _arr in PAL.items():
    for _i, _n in enumerate(NUMS):
        if _i < len(_arr):
            C["%s-%d" % (_p, _n)] = _arr[_i]

# project-specific Tailwind theme colours from the old tailwind.config.js
C.update({
    "navy": "#011f5b", "navy-soft": "#e8eefb", "navy-dark": "#01163f",
    "azure": "#0081d2", "azure-soft": "#e6f4fd", "azure-dark": "#0169ab",
    "magenta": "#eb0160", "magenta-soft": "#fde6ef", "magenta-dark": "#c80052",
    "accent": "#eb0160", "accent-soft": "#fde6ef", "accent-dark": "#c80052",
    "amber": "#fd9a01", "amber-soft": "#fff4e0", "amber-dark": "#e08800",
    "ink": "#0d1b33", "paper": "#f6f8fc",
})
# bare colour names used by the old theme (Tailwind needs the 500 step)
for _name, _step in {
    "green": "500", "red": "500", "blue": "500", "emerald": "500",
    "teal": "500", "cyan": "500", "sky": "500", "indigo": "500",
    "violet": "500", "purple": "500", "fuchsia": "500", "pink": "500",
    "rose": "500", "orange": "500", "yellow": "500", "lime": "500",
    "slate": "500", "gray": "500", "zinc": "500", "neutral": "500",
    "stone": "500",
}.items():
    if _name not in C and "%s-%s" % (_name, _step) in C:
        C[_name] = C["%s-%s" % (_name, _step)]
C.update({"lime-500": "#84cc16", "lime-600": "#65a30d", "lime-100": "#ecfccb",
          "fuchsia-500": "#d946ef", "fuchsia-100": "#fae8ff",
          "pink-500": "#ec4899", "pink-100": "#fce7f3"})
C["lime"] = "#84cc16"
C["fuchsia"] = "#d946ef"
C["pink"] = "#ec4899"


def hex_to_rgb(value):
    """'#011f5b' -> '1, 31, 91' (used for /opacity colour modifiers)."""
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return None
    try:
        return "%d, %d, %d" % (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except ValueError:
        return None

S = {
    "0": "0", "0.5": ".125rem", "1": ".25rem", "1.5": ".375rem", "2": ".5rem",
    "2.5": ".625rem", "3": ".75rem", "3.5": ".875rem", "4": "1rem", "5": "1.25rem",
    "6": "1.5rem", "7": "1.75rem", "8": "2rem", "9": "2.25rem", "10": "2.5rem",
    "11": "2.75rem", "12": "3rem", "14": "3.5rem", "16": "4rem", "20": "5rem",
    "24": "6rem", "28": "7rem", "32": "8rem", "36": "9rem", "40": "10rem",
    "44": "11rem", "48": "12rem", "52": "13rem", "56": "14rem", "60": "15rem",
    "64": "16rem", "72": "18rem", "80": "20rem", "96": "24rem",
}
FS = {
    "xs": ("0.75rem", "1rem"), "sm": ("0.875rem", "1.25rem"),
    "base": ("1rem", "1.5rem"), "lg": ("1.125rem", "1.75rem"),
    "xl": ("1.25rem", "1.75rem"), "2xl": ("1.5rem", "2rem"),
    "3xl": ("1.875rem", "2.25rem"), "4xl": ("2.25rem", "2.5rem"),
    "5xl": ("3rem", "1"), "6xl": ("3.75rem", "1"), "7xl": ("4.5rem", "1"),
}
RAD = {"none": "0", "sm": ".125rem", "": ".25rem", "md": ".375rem", "lg": ".5rem",
       "xl": ".75rem", "2xl": "1rem", "3xl": "1.5rem", "full": "9999px"}
SHADOW = {
    "sm": "0 1px 2px 0 rgb(0 0 0/.05)",
    "": "0 1px 3px 0 rgb(0 0 0/.1),0 1px 2px -1px rgb(0 0 0/.1)",
    "md": "0 4px 6px -1px rgb(0 0 0/.1),0 2px 4px -2px rgb(0 0 0/.1)",
    "lg": "0 10px 15px -3px rgb(0 0 0/.1),0 4px 6px -4px rgb(0 0 0/.1)",
    "xl": "0 20px 25px -5px rgb(0 0 0/.1),0 8px 10px -6px rgb(0 0 0/.1)",
    "2xl": "0 25px 50px -12px rgb(0 0 0/.25)",
    "inner": "inset 0 2px 4px 0 rgb(0 0 0/.05)",
    "none": "none",
}

# ----------------------------------------------------------------- engine
RULES = {}


def R(cls, props):
    if cls not in RULES and props:
        RULES[cls] = props


STATIC_UTILS = {
    "flex": [("display", "flex")], "inline-flex": [("display", "inline-flex")],
    "block": [("display", "block")], "inline-block": [("display", "inline-block")],
    "inline": [("display", "inline")], "hidden": [("display", "none")],
    "grid": [("display", "grid")], "table": [("display", "table")],
    "flex-col": [("flex-direction", "column")], "flex-row": [("flex-direction", "row")],
    "flex-col-reverse": [("flex-direction", "column-reverse")],
    "flex-wrap": [("flex-wrap", "wrap")], "flex-nowrap": [("flex-wrap", "nowrap")],
    "flex-1": [("flex", "1 1 0%")], "flex-auto": [("flex", "1 1 auto")],
    "flex-none": [("flex", "none")], "flex-grow": [("flex-grow", "1")],
    "flex-shrink-0": [("flex-shrink", "0")],
    "order-first": [("order", "-9999")], "order-last": [("order", "9999")],
    "items-center": [("align-items", "center")],
    "items-start": [("align-items", "flex-start")],
    "items-end": [("align-items", "flex-end")],
    "items-baseline": [("align-items", "baseline")],
    "items-stretch": [("align-items", "stretch")],
    "justify-center": [("justify-content", "center")],
    "justify-between": [("justify-content", "space-between")],
    "justify-start": [("justify-content", "flex-start")],
    "justify-end": [("justify-content", "flex-end")],
    "justify-around": [("justify-content", "space-around")],
    "justify-evenly": [("justify-content", "space-evenly")],
    "self-center": [("align-self", "center")],
    "self-start": [("align-self", "flex-start")],
    "self-end": [("align-self", "flex-end")],
    "text-left": [("text-align", "left")], "text-center": [("text-align", "center")],
    "text-right": [("text-align", "right")], "text-justify": [("text-align", "justify")],
    "relative": [("position", "relative")], "absolute": [("position", "absolute")],
    "fixed": [("position", "fixed")], "sticky": [("position", "sticky")],
    "static": [("position", "static")],
    "inset-0": [("top", "0"), ("right", "0"), ("bottom", "0"), ("left", "0")],
    "top-0": [("top", "0")], "right-0": [("right", "0")],
    "bottom-0": [("bottom", "0")], "left-0": [("left", "0")],
    "overflow-hidden": [("overflow", "hidden")], "overflow-auto": [("overflow", "auto")],
    "overflow-x-auto": [("overflow-x", "auto")],
    "overflow-y-auto": [("overflow-y", "auto")],
    "overflow-visible": [("overflow", "visible")],
    "w-full": [("width", "100%")], "h-full": [("height", "100%")],
    "w-auto": [("width", "auto")], "h-auto": [("height", "auto")],
    "w-screen": [("width", "100vw")], "h-screen": [("height", "100vh")],
    "min-h-screen": [("min-height", "100vh")], "min-w-0": [("min-width", "0")],
    "min-h-0": [("min-height", "0")], "max-w-full": [("max-width", "100%")],
    "mx-auto": [("margin-left", "auto"), ("margin-right", "auto")],
    "ml-auto": [("margin-left", "auto")], "mr-auto": [("margin-right", "auto")],
}
for _k, _v in STATIC_UTILS.items():
    R(_k, _v)

TYPO_UTILS = {
    "uppercase": [("text-transform", "uppercase")],
    "lowercase": [("text-transform", "lowercase")],
    "capitalize": [("text-transform", "capitalize")],
    "normal-case": [("text-transform", "none")],
    "truncate": [("overflow", "hidden"), ("text-overflow", "ellipsis"),
                 ("white-space", "nowrap")],
    "italic": [("font-style", "italic")], "not-italic": [("font-style", "normal")],
    "underline": [("text-decoration-line", "underline")],
    "line-through": [("text-decoration-line", "line-through")],
    "no-underline": [("text-decoration-line", "none")],
    "font-thin": [("font-weight", "100")], "font-light": [("font-weight", "300")],
    "font-normal": [("font-weight", "400")], "font-medium": [("font-weight", "500")],
    "font-semibold": [("font-weight", "600")], "font-bold": [("font-weight", "700")],
    "font-extrabold": [("font-weight", "800")], "font-black": [("font-weight", "900")],
    "whitespace-nowrap": [("white-space", "nowrap")],
    "whitespace-normal": [("white-space", "normal")],
    "whitespace-pre": [("white-space", "pre")],
    "whitespace-pre-wrap": [("white-space", "pre-wrap")],
    "break-words": [("overflow-wrap", "break-word")],
    "break-all": [("word-break", "break-all")],
    "cursor-pointer": [("cursor", "pointer")],
    "cursor-not-allowed": [("cursor", "not-allowed")],
    "cursor-default": [("cursor", "default")], "cursor-wait": [("cursor", "wait")],
    "select-none": [("user-select", "none")],
    "pointer-events-none": [("pointer-events", "none")],
    "pointer-events-auto": [("pointer-events", "auto")],
    "transition": [("transition-property",
                    "color,background-color,border-color,opacity,box-shadow,transform"),
                   ("transition-duration", "150ms"),
                   ("transition-timing-function", "cubic-bezier(.4,0,.2,1)")],
    "transition-colors": [("transition-property",
                           "color,background-color,border-color,fill,stroke"),
                          ("transition-duration", "150ms")],
    "transition-all": [("transition-property", "all"),
                       ("transition-duration", "150ms")],
    "transition-transform": [("transition-property", "transform"),
                             ("transition-duration", "150ms")],
    "duration-150": [("transition-duration", "150ms")],
    "duration-200": [("transition-duration", "200ms")],
    "duration-300": [("transition-duration", "300ms")],
    "duration-500": [("transition-duration", "500ms")],
    "ease-in-out": [("transition-timing-function", "cubic-bezier(.4,0,.2,1)")],
    "ease-out": [("transition-timing-function", "cubic-bezier(0,0,.2,1)")],
    "leading-none": [("line-height", "1")],
    "leading-tight": [("line-height", "1.25")],
    "leading-snug": [("line-height", "1.375")],
    "leading-normal": [("line-height", "1.5")],
    "leading-relaxed": [("line-height", "1.625")],
    "leading-loose": [("line-height", "2")],
    "tracking-tighter": [("letter-spacing", "-0.05em")],
    "tracking-tight": [("letter-spacing", "-0.025em")],
    "tracking-normal": [("letter-spacing", "0")],
    "tracking-wide": [("letter-spacing", "0.025em")],
    "tracking-wider": [("letter-spacing", "0.05em")],
    "tracking-widest": [("letter-spacing", "0.1em")],
}
for _k, _v in TYPO_UTILS.items():
    R(_k, _v)

MISC_UTILS = {
    "order-first": [("order", "-9999")], "order-last": [("order", "9999")],
    "border": [("border-width", "1px"), ("border-style", "solid")],
    "border-0": [("border-width", "0")],
    "border-2": [("border-width", "2px"), ("border-style", "solid")],
    "border-4": [("border-width", "4px"), ("border-style", "solid")],
    "border-b": [("border-bottom-width", "1px"), ("border-bottom-style", "solid")],
    "border-t": [("border-top-width", "1px"), ("border-top-style", "solid")],
    "border-l": [("border-left-width", "1px"), ("border-left-style", "solid")],
    "border-r": [("border-right-width", "1px"), ("border-right-style", "solid")],
    "border-b-0": [("border-bottom-width", "0")],
    "border-t-0": [("border-top-width", "0")],
    "border-collapse": [("border-collapse", "collapse")],
    "border-separate": [("border-collapse", "separate")],
    "shadow": [("box-shadow", SHADOW[""])],
    "shadow-sm": [("box-shadow", SHADOW["sm"])],
    "shadow-md": [("box-shadow", SHADOW["md"])],
    "shadow-lg": [("box-shadow", SHADOW["lg"])],
    "shadow-xl": [("box-shadow", SHADOW["xl"])],
    "shadow-2xl": [("box-shadow", SHADOW["2xl"])],
    "shadow-inner": [("box-shadow", SHADOW["inner"])],
    "shadow-none": [("box-shadow", "none")],
    "antialiased": [("-webkit-font-smoothing", "antialiased"),
                    ("-moz-osx-font-smoothing", "grayscale")],
    "appearance-none": [("appearance", "none")],
    "outline-none": [("outline", "2px solid transparent"),
                     ("outline-offset", "2px")],
    "sr-only": [("position", "absolute"), ("width", "1px"), ("height", "1px"),
                ("padding", "0"), ("margin", "-1px"), ("overflow", "hidden"),
                ("clip", "rect(0,0,0,0)"), ("white-space", "nowrap"),
                ("border-width", "0")],
    "not-sr-only": [("position", "static"), ("width", "auto"), ("height", "auto"),
                    ("padding", "0"), ("margin", "0"), ("overflow", "visible"),
                    ("clip", "auto"), ("white-space", "normal")],
    "object-cover": [("object-fit", "cover")],
    "object-contain": [("object-fit", "contain")],
    "object-center": [("object-position", "center")],
    "list-none": [("list-style-type", "none")],
    "list-disc": [("list-style-type", "disc")],
    "list-decimal": [("list-style-type", "decimal")],
    "isolate": [("isolation", "isolate")],
    "backdrop-blur": [("backdrop-filter", "blur(8px)"),
                      ("-webkit-backdrop-filter", "blur(8px)")],
    "aspect-square": [("aspect-ratio", "1 / 1")],
    "aspect-video": [("aspect-ratio", "16 / 9")],
    "text-wrap": [("text-wrap", "wrap")], "text-nowrap": [("text-wrap", "nowrap")],
    "text-balance": [("text-wrap", "balance")],
    "text-pretty": [("text-wrap", "pretty")],
    "resize-none": [("resize", "none")], "resize-y": [("resize", "vertical")],
    "divide-y": [("__DIVIDE__", "1")],
}
for _k, _v in MISC_UTILS.items():
    R(_k, _v)
RULES.pop("divide-y", None)

BOX = [
    ("px-", ("padding-left", "padding-right"), "box"),
    ("py-", ("padding-top", "padding-bottom"), "box"),
    ("pt-", ("padding-top",), "box"),
    ("pb-", ("padding-bottom",), "box"),
    ("pl-", ("padding-left",), "box"),
    ("pr-", ("padding-right",), "box"),
    ("p-", ("padding",), "box"),
    ("mx-", ("margin-left", "margin-right"), "box"),
    ("my-", ("margin-top", "margin-bottom"), "box"),
    ("mt-", ("margin-top",), "box"),
    ("mb-", ("margin-bottom",), "box"),
    ("ml-", ("margin-left",), "box"),
    ("mr-", ("margin-right",), "box"),
    ("m-", ("margin",), "box"),
    ("gap-x-", ("column-gap",), "gap"),
    ("gap-y-", ("row-gap",), "gap"),
    ("gap-", ("gap",), "gap"),
    ("w-", ("width",), "size"), ("h-", ("height",), "size"),
    ("min-w-", ("min-width",), "size"), ("min-h-", ("min-height",), "size"),
    ("max-w-", ("max-width",), "size"), ("max-h-", ("max-height",), "size"),
    ("top-", ("top",), "size"), ("bottom-", ("bottom",), "size"),
    ("left-", ("left",), "size"), ("right-", ("right",), "size"),
    ("z-", ("z-index",), "num"), ("opacity-", ("opacity",), "opacity"),
    ("order-", ("order",), "num"),
]
NAMED_SIZE = {"full": "100%", "screen": "100vh", "auto": "auto", "px": "1px",
              "min": "min-content", "max": "max-content", "fit": "fit-content"}
FRACTION = {"1/2": "50%", "1/3": "33.333333%", "2/3": "66.666667%",
            "1/4": "25%", "3/4": "75%", "1/5": "20%", "2/5": "40%",
            "3/5": "60%", "4/5": "80%", "1/6": "16.666667%", "5/6": "83.333333%"}
SCREEN = {"sm": "640px", "md": "768px", "lg": "1024px", "xl": "1280px",
          "2xl": "1536px"}
SIZE_WORD = {"xs": "20rem", "sm": "24rem", "md": "28rem", "lg": "32rem",
             "xl": "36rem", "2xl": "42rem", "3xl": "48rem", "4xl": "56rem",
             "5xl": "64rem", "6xl": "72rem", "7xl": "80rem",
             "prose": "65ch", "none": "none"}
MAXW_PX = {"0": "0rem", "xs": "20rem", "sm": "24rem", "md": "28rem",
           "lg": "32rem", "xl": "36rem", "2xl": "42rem", "3xl": "48rem",
           "4xl": "56rem", "5xl": "64rem", "6xl": "72rem", "7xl": "80rem"}

def _size_value(prefix, v):
    """Resolve the value part of a spacing/size token."""
    if v in FRACTION and prefix.startswith(("w-", "h-")):
        return FRACTION[v]
    if prefix.startswith("max-w-"):
        if v.startswith("screen-"):
            return SCREEN.get(v[7:])
        if v in MAXW_PX:
            return MAXW_PX[v]
        return None
    if v in NAMED_SIZE:
        if prefix.startswith("min-h-") and v == "screen":
            return "100vh"
        if v == "screen" and not prefix.startswith("h-"):
            return None
        return NAMED_SIZE[v]
    if v in SIZE_WORD and not v.isdigit():
        return SIZE_WORD[v]
    return S.get(v)


def dyn(tok):
    """Return CSS props for a dynamically generated utility token, else None."""
    for pre, props, kind in BOX:
        if tok.startswith(pre) and len(tok) > len(pre):
            v = tok[len(pre):]
            if kind == "opacity":
                try:
                    f = float(v)
                except ValueError:
                    return None
                if f > 1:
                    f = f / 100.0
                return [("opacity", ("%g" % f))]
            if kind == "num":
                if not v.lstrip("-").isdigit():
                    return None
                return [(props[0], v)]
            val = _size_value(pre, v)
            if val is None:
                return None
            return [(p, val) for p in props]

    # font-size
    if tok.startswith("text-") and tok[5:] in FS:
        a, b = FS[tok[5:]]
        return [("font-size", a), ("line-height", b)]

    # colours
    for pre, prop in (("bg-", "background-color"), ("text-", "color"),
                      ("border-", "border-color"), ("divide-", "border-color"),
                      ("fill-", "fill"), ("stroke-", "stroke")):
        if tok.startswith(pre) and tok[len(pre):] in C:
            return [(prop, C[tok[len(pre):]])]

    # rounded
    if tok.startswith("rounded"):
        rest = tok[len("rounded"):]
        if rest.startswith("-"):
            rest = rest[1:]
        if rest == "":
            return [("border-radius", RAD[""])]
        for side in sorted(RAD_SIDES, key=len, reverse=True):
            if rest.startswith(side):
                size = rest[len(side):]
                if size.startswith("-"):
                    size = size[1:]
                if size in RAD:
                    return [(p, RAD[size]) for p in RAD_SIDES[side]]
                break
        if rest in RAD:
            return [("border-radius", RAD[rest])]
        return None

    # shadow
    if tok.startswith("shadow"):
        rest = tok[6:].lstrip("-")
        if rest in SHADOW:
            return [("box-shadow", SHADOW[rest])]

    # grid helpers
    m = re.match(r"^grid-cols-(\d+)$", tok)
    if m:
        return [("grid-template-columns", "repeat(%s,minmax(0,1fr))" % m.group(1))]
    m = re.match(r"^grid-rows-(\d+)$", tok)
    if m:
        return [("grid-template-rows", "repeat(%s,minmax(0,1fr))" % m.group(1))]
    m = re.match(r"^col-span-(\d+)$", tok)
    if m:
        return [("grid-column", "span %s / span %s" % (m.group(1), m.group(1)))]
    m = re.match(r"^row-span-(\d+)$", tok)
    if m:
        return [("grid-row", "span %s / span %s" % (m.group(1), m.group(1)))]

    # numeric line-height
    m = re.match(r"^leading-(.+)$", tok)
    if m and m.group(1) in S:
        return [("line-height", S[m.group(1)])]
    return None

RAD_SIDES = {
    "t": ["border-top-left-radius", "border-top-right-radius"],
    "b": ["border-bottom-left-radius", "border-bottom-right-radius"],
    "l": ["border-top-left-radius", "border-bottom-left-radius"],
    "r": ["border-top-right-radius", "border-bottom-right-radius"],
    "tl": ["border-top-left-radius"],
    "tr": ["border-top-right-radius"],
    "bl": ["border-bottom-left-radius"],
    "br": ["border-bottom-right-radius"],
    "s": ["border-start-start-radius", "border-start-end-radius"],
    "e": ["border-end-start-radius", "border-end-end-radius"],
    "ss": ["border-start-start-radius"],
    "se": ["border-start-end-radius"],
    "es": ["border-end-start-radius"],
    "ee": ["border-end-end-radius"],
}

EXTRA_UTILS = {
    "bg-cover": [("background-size", "cover")],
    "bg-contain": [("background-size", "contain")],
    "bg-auto": [("background-size", "auto")],
    "bg-center": [("background-position", "center")],
    "bg-top": [("background-position", "top")],
    "bg-bottom": [("background-position", "bottom")],
    "bg-left": [("background-position", "left")],
    "bg-right": [("background-position", "right")],
    "bg-no-repeat": [("background-repeat", "no-repeat")],
    "bg-repeat": [("background-repeat", "repeat")],
    "bg-fixed": [("background-attachment", "fixed")],
    "bg-clip-text": [("-webkit-background-clip", "text"),
                     ("background-clip", "text")],
    "border-y": [("border-top-width", "1px"), ("border-bottom-width", "1px"),
                 ("border-top-style", "solid"), ("border-bottom-style", "solid")],
    "border-x": [("border-left-width", "1px"), ("border-right-width", "1px"),
                 ("border-left-style", "solid"), ("border-right-style", "solid")],
    "outline": [("outline-style", "solid")],
    "outline-hidden": [("outline", "none")],
    "outline-offset-1": [("outline-offset", "1px")],
    "outline-offset-2": [("outline-offset", "2px")],
    "outline-offset-4": [("outline-offset", "4px")],
    "outline-1": [("outline-width", "1px")],
    "outline-2": [("outline-width", "2px")],
    "outline-4": [("outline-width", "4px")],
    "ring": [("box-shadow", "0 0 0 3px var(--ghdi-ring, rgba(0, 129, 210, .45))")],
    "ring-1": [("box-shadow", "0 0 0 1px var(--ghdi-ring, rgba(0, 129, 210, .45))")],
    "ring-2": [("box-shadow", "0 0 0 2px var(--ghdi-ring, rgba(0, 129, 210, .45))")],
    "ring-4": [("box-shadow", "0 0 0 4px var(--ghdi-ring, rgba(0, 129, 210, .45))")],
    "content-center": [("align-content", "center")],
    "content-between": [("align-content", "space-between")],
    "content-start": [("align-content", "flex-start")],
    "content-end": [("align-content", "flex-end")],
    "place-items-center": [("place-items", "center")],
    "place-content-center": [("place-content", "center")],
    "transform": [("transform", "translate3d(0, 0, 0)")],
    "transform-none": [("transform", "none")],
    "will-change-transform": [("will-change", "transform")],
    "inset-x-0": [("left", "0"), ("right", "0")],
    "inset-y-0": [("top", "0"), ("bottom", "0")],
    "max-w-none": [("max-width", "none")],
    "shadow-soft": [("box-shadow",
                     "0 1px 2px rgba(3, 10, 24, .04),"
                     "0 12px 32px -24px rgba(3, 10, 24, .35)")],
    "snap-x": [("scroll-snap-type", "x var(--ghdi-snap, proximity)")],
    "snap-y": [("scroll-snap-type", "y var(--ghdi-snap, proximity)")],
    "snap-both": [("scroll-snap-type", "both var(--ghdi-snap, proximity)")],
    "snap-mandatory": [("--ghdi-snap", "mandatory")],
    "snap-proximity": [("--ghdi-snap", "proximity")],
    "snap-none": [("scroll-snap-type", "none")],
    "snap-start": [("scroll-snap-align", "start")],
    "snap-center": [("scroll-snap-align", "center")],
    "snap-end": [("scroll-snap-align", "end")],
    "snap-always": [("scroll-snap-stop", "always")],
    "snap-normal": [("scroll-snap-stop", "normal")],
    "scroll-smooth": [("scroll-behavior", "smooth")],
    "scroll-auto": [("scroll-behavior", "auto")],
    "prose": [("max-width", "65ch")],
    "prose-slate": [("color", "#334155")],
}

TRANS_VALUES = {
    "0": "0", "px": "1px", "0.5": ".125rem", "1": ".25rem", "1.5": ".375rem",
    "2": ".5rem", "2.5": ".625rem", "3": ".75rem", "3.5": ".875rem", "4": "1rem",
    "5": "1.25rem", "6": "1.5rem", "7": "1.75rem", "8": "2rem", "9": "2.25rem",
    "10": "2.5rem", "12": "3rem", "14": "3.5rem", "16": "4rem", "20": "5rem",
    "24": "6rem", "full": "100%", "1/2": "50%",
}
SCALE_VALUES = {"0": "0", "50": ".5", "75": ".75", "90": ".9", "95": ".95",
                "100": "1", "105": "1.05", "110": "1.1", "125": "1.25", "150": "1.5"}
NEGATABLE = {"margin", "margin-top", "margin-bottom", "margin-left",
             "margin-right", "top", "bottom", "left", "right", "z-index"}
LENGTH_RE = re.compile(r"^-?\d*\.?\d+(rem|px|%|em|vh|vw)$")

GRAD_DIR = {
    "to-r": "to right", "to-l": "to left", "to-t": "to top", "to-b": "to bottom",
    "to-tr": "to top right", "to-tl": "to top left",
    "to-br": "to bottom right", "to-bl": "to bottom left",
}
OPACITY_MOD = re.compile(
    r"^(bg|text|border|divide|ring|fill|stroke|from|via|to)-([\w-]+)/(\d+)$")
OPACITY_PROP = {
    "bg": "background-color", "text": "color", "border": "border-color",
    "divide": "border-color", "ring": "--ghdi-ring", "fill": "fill",
    "stroke": "stroke", "from": "--ghdi-grad-from",
    "via": "--ghdi-grad-via", "to": "--ghdi-grad-to",
}
HAS_VIA = False


ARB_PROPS = {
    "text": "font-size", "leading": "line-height", "tracking": "letter-spacing",
    "w": "width", "h": "height", "min-w": "min-width", "min-h": "min-height",
    "max-w": "max-width", "max-h": "max-height",
    "p": "padding", "pt": "padding-top", "pb": "padding-bottom",
    "pl": "padding-left", "pr": "padding-right",
    "m": "margin", "mt": "margin-top", "mb": "margin-bottom",
    "ml": "margin-left", "mr": "margin-right",
    "gap": "gap", "gap-x": "column-gap", "gap-y": "row-gap",
    "top": "top", "bottom": "bottom", "left": "left", "right": "right",
    "z": "z-index", "opacity": "opacity", "rounded": "border-radius",
    "duration": "transition-duration", "delay": "transition-delay",
    "grid-cols": "grid-template-columns", "grid-rows": "grid-template-rows",
    "basis": "flex-basis", "shadow": "box-shadow",
}
ARB_PAIRS = {
    "px": ("padding-left", "padding-right"),
    "py": ("padding-top", "padding-bottom"),
    "mx": ("margin-left", "margin-right"),
    "my": ("margin-top", "margin-bottom"),
    "size": ("width", "height"),
    "inset": ("top", "right", "bottom", "left"),
}
ARB_COLOR_PROP = {
    "bg": "background-color", "text": "color", "border": "border-color",
    "fill": "fill", "stroke": "stroke", "ring": "--ghdi-ring",
    "from": "--ghdi-grad-from", "via": "--ghdi-grad-via", "to": "--ghdi-grad-to",
}


def arbitrary(prefix, value):
    """Resolve a Tailwind arbitrary-value utility such as ``w-[85%]``."""
    if (value.startswith(("#", "rgb", "hsl", "oklch", "color-mix", "var("))
            or value in C):
        prop = ARB_COLOR_PROP.get(prefix)
        if prop:
            return [(prop, C.get(value, value))]
    if prefix in ARB_PAIRS:
        return [(p, value) for p in ARB_PAIRS[prefix]]
    if prefix == "col-span":
        return [("grid-column", "span %s / span %s" % (value, value))]
    if prefix == "row-span":
        return [("grid-row", "span %s / span %s" % (value, value))]
    if prefix == "translate-x":
        return [("transform", "translateX(%s)" % value)]
    if prefix == "translate-y":
        return [("transform", "translateY(%s)" % value)]
    if prefix == "rotate":
        return [("transform", "rotate(%s)" % value)]
    if prefix == "blur":
        return [("filter", "blur(%s)" % value)]
    prop = ARB_PROPS.get(prefix)
    if prop:
        return [(prop, value)]
    return None


def resolve(tok):
    """Resolve a token, handling negative prefixes and /opacity modifiers."""
    neg = False
    body = tok
    if body.startswith("-") and len(body) > 1:
        neg = True
        body = body[1:]

    # gradient direction
    m = re.match(r"^bg-gradient-(to-[a-z]{1,2})$", body)
    if m and m.group(1) in GRAD_DIR:
        d = GRAD_DIR[m.group(1)]
        if HAS_VIA:
            img = ("linear-gradient(%s,var(--ghdi-grad-from,transparent) 0%%,"
                   "var(--ghdi-grad-via,transparent) 50%%,"
                   "var(--ghdi-grad-to,transparent) 100%%)" % d)
        else:
            img = ("linear-gradient(%s,var(--ghdi-grad-from,transparent),"
                   "var(--ghdi-grad-to,transparent))" % d)
        return [("background-image", img)]

    # arbitrary values: text-[11px], w-[85%], grid-cols-[minmax(0,1fr)_1fr]
    m = re.match(r"^([a-z][a-z-]*)-\[(.+)\]$", body)
    if m:
        return arbitrary(m.group(1), m.group(2).replace("_", " ").strip())

    # colour + opacity modifier, e.g. bg-white/10, border-navy/15
    m = OPACITY_MOD.match(body)
    if m:
        name = m.group(2)
        color = C.get(name)
        rgb = hex_to_rgb(color) if color and color.startswith("#") else None
        if not rgb:
            return None
        value = "rgba(%s, %g)" % (rgb, int(m.group(3)) / 100.0)
        return [(OPACITY_PROP[m.group(1)], value)]

    # gradient stop colours: from-navy / via-azure / to-transparent
    m = re.match(r"^(from|via|to)-([\w-]+)$", body)
    if m:
        stop = {"from": "--ghdi-grad-from", "via": "--ghdi-grad-via",
                "to": "--ghdi-grad-to"}[m.group(1)]
        if m.group(2) == "transparent":
            return [(stop, "transparent")]
        if m.group(2) in C:
            return [(stop, C[m.group(2)])]
        return None

    # ring / outline colours (ring-2, outline-2 stay with the width tables)
    m = re.match(r"^ring-([\w-]+)$", body)
    if m and m.group(1) in C:
        return [("--ghdi-ring", C[m.group(1)])]
    m = re.match(r"^outline-([\w-]+)$", body)
    if m and m.group(1) in C:
        return [("outline-color", C[m.group(1)])]

    props = None

    m = re.match(r"^translate-([xy])-(.+)$", body)
    if m and m.group(2) in TRANS_VALUES:
        axis = "translateX" if m.group(1) == "x" else "translateY"
        props = [("transform", "%s(%s)" % (axis, TRANS_VALUES[m.group(2)]))]

    if props is None:
        m = re.match(r"^scale-([xy])-(.+)$", body)
        if m and m.group(1) in ("x", "y") and m.group(2) in SCALE_VALUES:
            axis = "scaleX" if m.group(1) == "x" else "scaleY"
            props = [("transform", "%s(%s)" % (axis, SCALE_VALUES[m.group(2)]))]
        else:
            m = re.match(r"^scale-(.+)$", body)
            if m and m.group(1) in SCALE_VALUES:
                props = [("transform", "scale(%s)" % SCALE_VALUES[m.group(1)])]

    if props is None:
        m = re.match(r"^rotate-(.+)$", body)
        if m:
            props = [("transform", "rotate(%sdeg)" % m.group(1))]

    if props is None:
        props = dyn(body)
    if props is None:
        props = EXTRA_UTILS.get(body)
    if props is None:
        props = (STATIC_UTILS.get(body) or TYPO_UTILS.get(body)
                 or MISC_UTILS.get(body))
    if props == [("__DIVIDE__", "1")]:
        return None
    if props is None:
        return None
    if not neg:
        return props

    flipped = []
    for key, value in props:
        if key in NEGATABLE and LENGTH_RE.match(value):
            flipped.append((key, "-" + value))
        elif key == "transform" and value.endswith(")") and "(0)" not in value:
            flipped.append((key, value.replace("(", "(-", 1)))
        else:
            flipped.append((key, value))
    return flipped


PREFIX_RE = re.compile(
    r"^(sm|md|lg|xl|2xl|hover|focus|focus-visible|focus-within|active|disabled"
    r"|group-hover|group-focus|placeholder|dark|peer-checked|prose-a):(.+)$")

out("=" * 72)
out("GHDI -> BOOTSTRAP ASSET GENERATOR")
out("=" * 72)

TEMPLATES = sorted(glob.glob("templates/**/*.html", recursive=True))
DJANGO_TAG = re.compile(r"\{%.*?%\}|\{\{.*?\}\}", re.S)
JUNK_TOKEN = re.compile(r"[<>=&;'\"]|^\d+(\.\d+)?$")


def clean_classes(attr):
    """Strip Django template markup then yield real class tokens."""
    for _t in DJANGO_TAG.sub(" ", attr).split():
        _t = _t.strip()
        if not _t or JUNK_TOKEN.search(_t) or _t.endswith("-"):
            continue
        yield _t


tokens = {}
for _p in TEMPLATES:
    _src = rd(_p)
    for _cls in re.findall(r'class="([^"]*)"', _src):
        for _t in clean_classes(_cls):
            tokens[_t] = tokens.get(_t, 0) + 1

out("")
out("1. CLASS TOKEN INVENTORY")
out("   templates scanned : %d" % len(TEMPLATES))
out("   unique tokens     : %d" % len(tokens))

resolved = 0
unresolved = []
media_rules = {}
state_rules = {}

HAS_VIA = any(_t.startswith("via-") for _t in tokens)

for _tok in sorted(tokens):
    _m = PREFIX_RE.match(_tok)
    if _m:
        _pre, _props = _m.group(1), resolve(_m.group(2))
        if _props:
            resolved += 1
            # Also register the bare utility. This only affects elements that
            # literally carry that class, so it is behaviour-neutral, and it
            # keeps the static CSS audit able to verify variant coverage.
            R(_m.group(2), _props)
            _esc = _m.group(2) if _pre.startswith("prose") else _tok
            if _pre in SCREEN:
                media_rules.setdefault(SCREEN[_pre], {})[_esc] = _props
            else:
                state_rules.setdefault(_pre, {})[_esc] = _props
        else:
            unresolved.append(_tok)
        continue
    _props = resolve(_tok)
    if _props:
        resolved += 1
        R(_tok, _props)
        continue
    if _tok == "divide-y":
        resolved += 1
        continue
    unresolved.append(_tok)

existing = ""
for _f in sorted(glob.glob("static/css/*.css")):
    existing += rd(_f)
existing_classes = set(re.findall(r"\.([a-zA-Z][\w-]*)", existing))
for _attr in re.findall(r'class="([^"]*)"', existing):
    for _t2 in _attr.split():
        existing_classes.add(_t2)

real_missing = []
for _t in unresolved:
    _base = _t.split(":")[-1]
    if _base not in existing_classes:
        real_missing.append(_t)

out("   resolved by layer : %d" % resolved)
out("   unresolved        : %d" % len(unresolved))
out("   truly missing     : %d" % len(real_missing))
if real_missing:
    out("   missing tokens    : %s" % ", ".join(real_missing[:60]))

out("")
out("2. WRITING static/css/ghdi-compat.css")

PSEUDO = {"hover": "hover", "focus": "focus", "focus-visible": "focus-visible",
          "focus-within": "focus-within", "active": "active", "disabled": "disabled"}

# Class names may contain characters that are not valid in a CSS identifier
# (`:`, `.`, `/`, `[`, `]`, `(`, `,`, `%`...). Tailwind escapes them
# (`.py-1\.5`, `.text-\[11px\]`); an unescaped selector is invalid CSS and the
# browser drops the whole rule, so the same escaping is required here.
UNSAFE_IN_SELECTOR = re.compile(r"[^A-Za-z0-9_-]")


def css_escape(name):
    out = []
    for i, ch in enumerate(name):
        if i == 0 and ch.isdigit():
            out.append("\\3%s " % ch)
        elif UNSAFE_IN_SELECTOR.match(ch):
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def block(cls, props):
    return ".%s{%s}" % (css_escape(cls), ";".join("%s:%s" % kv for kv in props))


parts = []
parts.append("/* " + "=" * 72)
parts.append("   GHDI compatibility layer - GENERATED, do not edit by hand.")
parts.append("   Tailwind-style utilities still referenced by templates, emitted as")
parts.append("   plain CSS so the UI is unchanged after removing the Tailwind CDN.")
parts.append("   Regenerate:  python ghdi_bootstrap_migrate.py")
parts.append("   " + "=" * 72 + " */")
parts.append("")
parts.append("/* ---- base utilities (%d) ---- */" % len(RULES))
for _cls in sorted(RULES):
    parts.append(block(_cls, RULES[_cls]))
parts.append("")

if state_rules:
    parts.append("/* ---- state variants ---- */")
    for _pre in sorted(state_rules):
        _rules = state_rules[_pre]
        for _cls in sorted(_rules):
            _body = ";".join("%s:%s" % kv for kv in _rules[_cls])
            _sel = css_escape(_cls)
            if _pre == "placeholder":
                parts.append(".%s::placeholder{%s}" % (_sel, _body))
            elif _pre == "group-hover":
                parts.append(".group:hover .%s{%s}" % (_sel, _body))
            elif _pre == "group-focus":
                parts.append(".group:focus-within .%s{%s}" % (_sel, _body))
            elif _pre == "dark":
                parts.append('[data-bs-theme="dark"] .%s{%s}' % (_sel, _body))
            elif _pre == "peer-checked":
                parts.append(".peer:checked ~ .%s{%s}" % (_sel, _body))
            elif _pre.startswith("prose"):
                parts.append(".prose a{%s}" % _body)
            else:
                parts.append(".%s:%s{%s}" % (_sel, PSEUDO.get(_pre, _pre), _body))
    parts.append("")

if media_rules:
    parts.append("/* ---- responsive variants ---- */")
    for _bp in ["640px", "768px", "1024px", "1280px", "1536px"]:
        if _bp not in media_rules:
            continue
        parts.append("@media (min-width: %s) {" % _bp)
        for _cls in sorted(media_rules[_bp]):
            parts.append("  " + block(_cls, media_rules[_bp][_cls]))
        parts.append("}")
    parts.append("")

parts.append("/* ---- space / divide helpers ---- */")
for _tok in sorted(tokens):
    _m = re.match(r"^space-y-(.+)$", _tok)
    if _m and _m.group(1) in S:
        parts.append(".%s > * + *{margin-top:%s}"
                     % (css_escape(_tok), S[_m.group(1)]))
    _m = re.match(r"^space-x-(.+)$", _tok)
    if _m and _m.group(1) in S:
        parts.append(".%s > * + *{margin-left:%s}"
                     % (css_escape(_tok), S[_m.group(1)]))
parts.append(".divide-y > * + *{border-top-width:1px;border-top-style:solid}")
for _tok in sorted(tokens):
    if _tok.startswith("divide-") and _tok != "divide-y" and _tok[7:] in C:
        parts.append(".%s > * + *{border-color:%s}"
                     % (css_escape(_tok), C[_tok[7:]]))

if "prose" in tokens:
    parts.append("")
    parts.append("/* ---- prose typography (replaces @tailwindcss/typography) ---- */")
    parts.append("""
.prose { line-height: 1.7; }
.prose > * + * { margin-top: 1.25em; }
.prose h1, .prose h2, .prose h3, .prose h4 {
  font-weight: 700; line-height: 1.25; letter-spacing: -.02em;
  color: var(--ghdi-text, #0d1b33); scroll-margin-top: 5rem;
}
.prose h1 { font-size: 2.25rem; margin-top: 0; }
.prose h2 { font-size: 1.5rem; }
.prose h3 { font-size: 1.25rem; }
.prose h4 { font-size: 1.125rem; }
.prose p { margin-top: 1.25em; margin-bottom: 1.25em; }
.prose a {
  color: var(--ghdi-azure, #0081d2); text-decoration: underline;
  text-underline-offset: 2px; font-weight: 500;
}
.prose strong { font-weight: 700; color: var(--ghdi-text, #0d1b33); }
.prose ul, .prose ol { padding-left: 1.5em; margin: 1.25em 0; }
.prose ul { list-style-type: disc; }
.prose ol { list-style-type: decimal; }
.prose li { margin: .5em 0; }
.prose li::marker { color: var(--ghdi-azure, #0081d2); }
.prose blockquote {
  border-left: 3px solid var(--ghdi-accent, #eb0160);
  padding-left: 1rem; font-style: italic;
  color: var(--ghdi-text-muted, #5a6b87);
}
.prose code {
  font-size: .875em; background: var(--ghdi-surface-3, #eef2f9);
  padding: .15em .4em; border-radius: .25rem;
}
.prose pre {
  background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: .5rem;
  overflow-x: auto; font-size: .875rem;
}
.prose pre code { background: transparent; padding: 0; color: inherit; }
.prose hr { border: 0; border-top: 1px solid var(--ghdi-border, #dfe6f2); }
.prose img { border-radius: .5rem; }
.prose table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.prose th, .prose td {
  border-bottom: 1px solid var(--ghdi-border, #dfe6f2);
  padding: .5rem .75rem; text-align: left;
}
.prose th { font-weight: 700; }
""")

parts.append("")

wr("static/css/ghdi-compat.css", "\n".join(parts))
out("   written: static/css/ghdi-compat.css (%d bytes)"
    % os.path.getsize("static/css/ghdi-compat.css"))

out("")
out("3. WRITING static/css/ghdi-theme.css")

THEME_HEAD = """/* ==========================================================================
   GHDI premium theme layer. Load AFTER bootstrap.min.css.
   Provides brand tokens, premium surfaces and dark/light mode support.
   ========================================================================== */
:root,
[data-bs-theme="light"] {
  --ghdi-navy:           #011f5b;
  --ghdi-navy-700:       #032a76;
  --ghdi-navy-600:       #0a3a92;
  --ghdi-accent:         #eb0160;
  --ghdi-accent-600:     #c80052;
  --ghdi-azure:          #0081d2;
  --ghdi-amber:          #fd9a01;

  --ghdi-surface:        #ffffff;
  --ghdi-surface-2:      #f6f8fc;
  --ghdi-surface-3:      #eef2f9;
  --ghdi-border:         #dfe6f2;
  --ghdi-text:           #0d1b33;
  --ghdi-text-muted:     #5a6b87;
  --ghdi-shadow:         3, 10, 24;

  --bs-primary:          #011f5b;
  --bs-primary-rgb:      1, 31, 91;
  --bs-link-color:       #0081d2;
  --bs-link-hover-color: #011f5b;
  --bs-body-color:       #0d1b33;
  --bs-body-bg:          #f6f8fc;
  --bs-border-color:     #dfe6f2;
  --bs-body-font-family: sans-serif;
}

[data-bs-theme="dark"] {
  --ghdi-surface:        #0b1424;
  --ghdi-surface-2:      #070e1a;
  --ghdi-surface-3:      #121e33;
  --ghdi-border:         #1d2c47;
  --ghdi-text:           #e8eefb;
  --ghdi-text-muted:     #93a4c3;
  --ghdi-shadow:         0, 0, 0;

  --bs-body-color:       #e8eefb;
  --bs-body-bg:          #070e1a;
  --bs-border-color:     #1d2c47;
  --bs-secondary-bg:     #0b1424;
  --bs-tertiary-bg:      #121e33;
  --bs-emphasis-color:   #ffffff;
  --bs-link-color:       #5eb3ef;
  --bs-link-hover-color: #9cd2f7;
}

body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ---------- premium buttons ---------- */
.ghdi-btn {
  --bs-btn-padding-y: .58rem;
  --bs-btn-padding-x: 1.15rem;
  --bs-btn-font-weight: 600;
  --bs-btn-border-radius: .625rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  letter-spacing: .01em;
  transition: transform .16s cubic-bezier(.4, 0, .2, 1),
              box-shadow .16s cubic-bezier(.4, 0, .2, 1),
              background-color .16s ease, color .16s ease;
}
.ghdi-btn:active { transform: translateY(1px); }
.ghdi-btn--sm { --bs-btn-padding-y: .36rem; --bs-btn-padding-x: .7rem; font-size: .8125rem; }
.ghdi-btn--lg { --bs-btn-padding-y: .78rem; --bs-btn-padding-x: 1.5rem; font-size: 1.0625rem; }

.ghdi-btn--primary {
  background: var(--ghdi-navy); border-color: var(--ghdi-navy); color: #fff;
  box-shadow: 0 6px 18px -8px rgba(1, 31, 91, .65);
}
.ghdi-btn--primary:hover,
.ghdi-btn--primary:focus-visible {
  background: var(--ghdi-navy-600); border-color: var(--ghdi-navy-600); color: #fff;
  box-shadow: 0 12px 26px -10px rgba(1, 31, 91, .7);
}
.ghdi-btn--accent {
  background: var(--ghdi-accent); border-color: var(--ghdi-accent); color: #fff;
  box-shadow: 0 6px 18px -8px rgba(235, 1, 96, .6);
}
.ghdi-btn--accent:hover,
.ghdi-btn--accent:focus-visible {
  background: var(--ghdi-accent-600); border-color: var(--ghdi-accent-600); color: #fff;
}
.ghdi-btn--azure {
  background: var(--ghdi-azure); border-color: var(--ghdi-azure); color: #fff;
}
.ghdi-btn--azure:hover,
.ghdi-btn--azure:focus-visible {
  background: #0169ab; border-color: #0169ab; color: #fff;
}
.ghdi-btn--amber {
  background: var(--ghdi-amber); border-color: var(--ghdi-amber);
  color: #201400; font-weight: 700;
}
.ghdi-btn--amber:hover,
.ghdi-btn--amber:focus-visible {
  background: #e08800; border-color: #e08800; color: #201400;
}
.ghdi-btn--ghost {
  background: transparent; border-color: var(--ghdi-border); color: var(--ghdi-text);
}
.ghdi-btn--ghost:hover,
.ghdi-btn--ghost:focus-visible {
  background: var(--ghdi-surface-3); border-color: var(--ghdi-border);
  color: var(--ghdi-navy);
}
[data-bs-theme="dark"] .ghdi-btn--ghost:hover,
[data-bs-theme="dark"] .ghdi-btn--ghost:focus-visible { color: #fff; }
"""

THEME_TAIL = """
/* ---------- surfaces ---------- */
.ghdi-panel {
  background: var(--ghdi-surface);
  border: 1px solid var(--ghdi-border);
  border-radius: .875rem;
  box-shadow: 0 1px 2px rgba(var(--ghdi-shadow), .04),
              0 12px 32px -24px rgba(var(--ghdi-shadow), .4);
}
.ghdi-panel__head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--ghdi-border);
}
.ghdi-panel__title {
  font-size: .95rem; font-weight: 700; margin: 0; letter-spacing: -.01em;
}
.ghdi-panel__body { padding: 1.25rem; }

.ghdi-stat {
  background: var(--ghdi-surface);
  border: 1px solid var(--ghdi-border);
  border-radius: .875rem;
  padding: 1.25rem;
}
.ghdi-stat__value {
  font-size: 1.75rem; font-weight: 800; line-height: 1.1;
  letter-spacing: -.03em; color: var(--ghdi-text);
}
.ghdi-stat__label {
  font-size: .75rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .08em; color: var(--ghdi-text-muted);
}

.ghdi-divider { height: 1px; background: var(--ghdi-border); border: 0; }

.ghdi-scroll-x { overflow-x: auto; -webkit-overflow-scrolling: touch; }

/* ---------- focus visibility (a11y) ---------- */
:focus-visible {
  outline: 2px solid var(--ghdi-azure);
  outline-offset: 2px;
  border-radius: .25rem;
}

/* ---------- page-load progress bar ---------- */
#ghdi-progress {
  position: fixed;
  top: 0; left: 0; right: auto; bottom: auto;
  height: 3px; width: 0;
  background: linear-gradient(90deg, var(--ghdi-navy), var(--ghdi-azure) 55%,
              var(--ghdi-accent));
  z-index: 3000;
  opacity: 0;
  transition: width .25s ease, opacity .3s ease;
  box-shadow: 0 0 12px rgba(0, 129, 210, .7);
  pointer-events: none;
}
#ghdi-progress.is-active { opacity: 1; }
#ghdi-progress.is-done { width: 100%; opacity: 0; }

/* ---------- reduced motion ---------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
"""

wr("static/css/ghdi-theme.css", THEME_HEAD + THEME_TAIL)
out("   written: static/css/ghdi-theme.css (%d bytes)"
    % os.path.getsize("static/css/ghdi-theme.css"))

out("")
out("4. WRITING static/js/ghdi-ui.js")

UI_HEAD = """/* ==========================================================================
   GHDI shell UI. Requires static/js/bootstrap.bundle.min.js.
   - top page-load progress bar
   - dark / light theme toggle (persisted, respects prefers-color-scheme)
   - bootstrap toasts + auto-dismiss alerts
   ========================================================================== */
(function () {
  "use strict";

  var THEME_KEY = "ghdi-theme";

  function getStoredTheme() {
    try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
  }

  function setStoredTheme(theme) {
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* ignore */ }
  }

  function preferredTheme() {
    var stored = getStoredTheme();
    if (stored === "dark" || stored === "light") { return stored; }
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function syncToggleButtons(theme) {
    var dark = theme === "dark";
    var nodes = document.querySelectorAll("[data-ghdi-theme-toggle]");
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].setAttribute("aria-pressed", dark ? "true" : "false");
      nodes[i].setAttribute("aria-label",
        dark ? "Switch to light mode" : "Switch to dark mode");
      var icon = nodes[i].querySelector("i");
      if (icon) {
        icon.className = dark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
      }
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    setStoredTheme(theme);
    syncToggleButtons(theme);
  }

  window.ghdiApplyTheme = applyTheme;
  window.ghdiToggleTheme = function () {
    var current = document.documentElement.getAttribute("data-bs-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  };

  /* ---------- progress bar ---------- */
  var bar = null;

  function progressBar() {
    if (bar) { return bar; }
    bar = document.getElementById("ghdi-progress");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "ghdi-progress";
      bar.setAttribute("aria-hidden", "true");
      (document.body || document.documentElement).appendChild(bar);
    }
    return bar;
  }

  var pct = 0;
  var timer = null;

  function step() {
    pct += (92 - pct) * 0.12;
    progressBar().style.width = pct.toFixed(2) + "%";
  }

  function startProgress() {
    var el = progressBar();
    pct = 6;
    el.classList.remove("is-done");
    el.classList.add("is-active");
    step();
    if (timer) { clearInterval(timer); }
    timer = window.setInterval(step, 180);
  }

  function finishProgress() {
    var el = progressBar();
    if (timer) { clearInterval(timer); timer = null; }
    el.classList.add("is-done");
    window.setTimeout(function () {
      el.classList.remove("is-active");
      el.classList.remove("is-done");
      el.style.width = "0";
    }, 420);
  }

  window.ghdiStartProgress = startProgress;
  window.ghdiFinishProgress = finishProgress;

  function isInternalLink(anchor) {
    var href = anchor.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#") { return false; }
    if (/^(mailto:|tel:|javascript:|data:)/i.test(href)) { return false; }
    if (anchor.hasAttribute("download")) { return false; }
    if (anchor.getAttribute("target") === "_blank") { return false; }
    if (anchor.host && anchor.host !== window.location.host) { return false; }
    if (anchor.hasAttribute("data-bs-toggle") ||
        anchor.hasAttribute("data-ghdi-theme-toggle")) { return false; }
    return true;
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest
      ? event.target.closest("[data-ghdi-theme-toggle]") : null;
    if (toggle) {
      event.preventDefault();
      window.ghdiToggleTheme();
      return;
    }
    var anchor = event.target.closest ? event.target.closest("a[href]") : null;
    if (anchor && isInternalLink(anchor)) { startProgress(); }
  });

  document.addEventListener("submit", function (event) {
    if (event.target && event.target.getAttribute("data-ghdi-no-progress") === null) {
      startProgress();
    }
  });

  window.addEventListener("pageshow", finishProgress);
  window.addEventListener("pagehide", startProgress);
"""

UI_TAIL = """
  /* ---------- bootstrap toasts ---------- */
  window.ghdiToast = function (message, variant) {
    var wrap = document.getElementById("ghdi-toasts");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "ghdi-toasts";
      wrap.className = "toast-container position-fixed top-0 end-0 p-3";
      wrap.style.zIndex = "2500";
      document.body.appendChild(wrap);
    }
    var el = document.createElement("div");
    el.className = "toast align-items-center border-0 mb-2 text-bg-" +
      (variant || "dark");
    el.setAttribute("role", "alert");
    el.setAttribute("aria-live", "assertive");
    el.setAttribute("aria-atomic", "true");
    el.innerHTML = '<div class="d-flex"><div class="toast-body"></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" ' +
      'data-bs-dismiss="toast" aria-label="Close"></button></div>';
    el.querySelector(".toast-body").textContent = message;
    wrap.appendChild(el);
    if (window.bootstrap && window.bootstrap.Toast) {
      var toast = new window.bootstrap.Toast(el, { delay: 4200 });
      toast.show();
      el.addEventListener("hidden.bs.toast", function () { el.remove(); });
    } else {
      window.setTimeout(function () { el.remove(); }, 4200);
    }
  };

  function autoDismiss() {
    var nodes = document.querySelectorAll("[data-ghdi-autodismiss]");
    for (var i = 0; i < nodes.length; i++) {
      (function (el) {
        window.setTimeout(function () {
          el.style.transition = "opacity .4s ease";
          el.style.opacity = "0";
          window.setTimeout(function () { el.remove(); }, 450);
        }, 6000);
      })(nodes[i]);
    }
  }

  /* ---------- init ---------- */
  function init() {
    applyTheme(document.documentElement.getAttribute("data-bs-theme") ||
      preferredTheme());
    autoDismiss();
    // make every server-rendered bootstrap tooltip live
    if (window.bootstrap && window.bootstrap.Tooltip) {
      var tips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
      for (var i = 0; i < tips.length; i++) {
        new window.bootstrap.Tooltip(tips[i]);
      }
    }
  }

  // theme must be correct before first paint
  applyTheme(document.documentElement.getAttribute("data-bs-theme") ||
    preferredTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
"""

wr("static/js/ghdi-ui.js", UI_HEAD + UI_TAIL)
out("   written: static/js/ghdi-ui.js (%d bytes)"
    % os.path.getsize("static/js/ghdi-ui.js"))

out("")
out("5. SUMMARY")
out("   compat rules generated : %d" % len(RULES))
out("   state variants         : %d" % sum(len(v) for v in state_rules.values()))
out("   responsive variants    : %d" % sum(len(v) for v in media_rules.values()))
out("   truly missing tokens   : %d" % len(real_missing))
out("")
out("   Assets ready. Templates are NOT modified by this script.")

wr("MIGRATION_REPORT.txt", "\n".join(LOG))
print("")
print("Report written to MIGRATION_REPORT.txt")










