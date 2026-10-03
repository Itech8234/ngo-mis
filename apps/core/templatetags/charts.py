"""Template tags: SVG charts rendered server-side (no JS chart library)."""
import math

from django import template
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

register = template.Library()

PALETTE = ["#0d9488", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#10b981", "#64748b", "#f97316"]


def _nice_max(value):
    if value <= 0:
        return 10
    magnitude = 10 ** math.floor(math.log10(value))
    for m in (1, 2, 2.5, 5, 10):
        if value <= m * magnitude:
            return m * magnitude
    return 10 * magnitude


def _fmt(value):
    """Format a chart value with thousands separators, tolerating strings."""
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


@register.simple_tag
def bar_chart(data, height=180, color="#0d9488"):
    """data: list of (label, value). Renders a rounded-bar SVG chart."""
    if not data:
        return mark_safe('<div class="text-sm text-slate-400 py-8 text-center">No data yet</div>')
    max_value = _nice_max(max(v for _, v in data) or 1)
    width = max(320, 40 * len(data))
    bar_w, gap = 26, 14
    chart_h = height - 22
    bars = []
    for i, (label, value) in enumerate(data):
        h = round((value / max_value) * chart_h, 1)
        x = i * (bar_w + gap) + 4
        y = chart_h - h + 4
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{max(h, 2)}" rx="6" fill="{color}" '
            f'opacity="0.85"><title>{label}: {_fmt(value)}</title></rect>'
        )
        if len(data) <= 14:
            bars.append(
                f'<text x="{x + bar_w / 2}" y="{chart_h + 18}" text-anchor="middle" class="chart-label">{label}</text>'
            )
    svg = (
        f'<svg viewBox="0 0 {width} {height}" class="w-full" style="height:{height}px" role="img" '
        f'aria-label="Bar chart">{"".join(bars)}</svg>'
    )
    return mark_safe(svg)


@register.simple_tag
def line_chart(data, height=200, color="#0d9488", fill=True):
    """data: list of (label, value). Renders a polyline + area SVG."""
    if not data:
        return mark_safe('<div class="text-sm text-slate-400 py-8 text-center">No data yet</div>')
    max_value = _nice_max(max(v for _, v in data) or 1)
    w, chart_h = 600, height - 26
    step = w / max(len(data) - 1, 1)
    points = []
    for i, (label, value) in enumerate(data):
        x = round(i * step, 1)
        y = round(chart_h - (value / max_value) * (chart_h - 10) + 4, 1)
        points.append((x, y, label, value))
    polyline = " ".join(f"{x},{y}" for x, y, _, _ in points)
    area_path = f"M0,{chart_h + 4} L" + " L".join(f"{x},{y}" for x, y, _, _ in points) + f" L{w},{chart_h + 4} Z"
    dots = format_html_join(
        "",
        '<circle cx="{}" cy="{}" r="3.5" fill="{}" stroke="white" stroke-width="1.5">'
        "<title>{}: {}</title></circle>",
        ((x, y, color, label, _fmt(value)) for x, y, label, value in points),
    )
    labels = format_html_join(
        "",
        '<text x="{}" y="{}" text-anchor="middle" class="chart-label">{}</text>',
        ((x, height - 6, label) for x, _, label, _ in points),
    )
    svg = (
        f'<svg viewBox="0 0 {w} {height}" class="w-full" style="height:{height}px" role="img" aria-label="Line chart">'
        + (f'<path d="{area_path}" fill="{color}" opacity="0.08"/>' if fill else "")
        + f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>{dots}{labels}</svg>'
    )
    return mark_safe(svg)


@register.simple_tag
def doughnut_chart(data, size=170):
    """data: list of (label, value). Renders an SVG doughnut with a legend."""
    entries = [(label, value) for label, value in data if value]
    total = sum(v for _, v in entries) or 1
    radius = size / 2 - 12
    circumference = 2 * math.pi * radius
    offset = 0.0
    arcs, legend = [], []
    for i, (label, value) in enumerate(entries):
        color = PALETTE[i % len(PALETTE)]
        frac = value / total
        dash = frac * circumference
        arcs.append(
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" stroke="{color}" '
            f'stroke-width="18" stroke-dasharray="{dash:.2f} {circumference - dash:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {size / 2} {size / 2})">'
            f"<title>{label}: {_fmt(value)}</title></circle>"
        )
        legend.append(
            f'<span class="inline-flex items-center gap-1.5 text-xs text-slate-600">'
            f'<span class="h-2.5 w-2.5 rounded-full" style="background:{color}"></span>'
            f"{label} <span class='text-slate-400'>{frac * 100:.0f}%</span></span>"
        )
        offset += dash
    svg = (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img" aria-label="Doughnut chart">'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" stroke="#f1f5f9" stroke-width="18"/>'
        f'{"".join(arcs)}</svg>'
    )
    return mark_safe(
        f'<div class="flex flex-col sm:flex-row items-center gap-4">{svg}'
        f'<div class="flex flex-col gap-1.5">{"".join(legend)}</div></div>'
    )


@register.simple_tag
def progress_bar(value, maximum=100, color="teal", label="", show_value=True):
    """Accessible progress bar used for budget/utilisation indicators."""
    pct = min(100.0, (float(value) / float(maximum) * 100.0) if maximum else 0)
    color_map = {
        "teal": "bg-teal-600", "blue": "bg-sky-600", "amber": "bg-amber-500",
        "red": "bg-red-500", "green": "bg-emerald-600", "gray": "bg-slate-400",
    }
    bg = color_map.get(color, "bg-teal-600")
    label_html = f'<div class="flex justify-between text-xs text-slate-500"><span>{label}</span></div>' if label else ""
    value_html = f'<div class="text-right text-xs text-slate-500">{pct:.0f}%</div>' if show_value else ""
    return mark_safe(
        f'<div class="space-y-1">{label_html}'
        f'<div class="h-2 rounded-full bg-slate-100 overflow-hidden">'
        f'<div class="h-full rounded-full {bg}" style="width:{pct:.1f}%"></div></div>{value_html}</div>'
    )


@register.simple_tag
def sparkline(values, color="#0d9488", height=36):
    """Tiny sparkline for KPI cards."""
    if not values:
        return f'<svg class="w-full" height="{height}"></svg>'
    max_value = max(values) or 1
    min_value = min(values)
    span = (max_value - min_value) or 1
    w = 100
    step = w / max(len(values) - 1, 1)
    pts = " ".join(
        f"{round(i * step, 1)},{round(height - 3 - ((v - min_value) / span) * (height - 8), 1)}"
        for i, v in enumerate(values)
    )
    return mark_safe(
        f'<svg viewBox="0 0 {w} {height}" preserveAspectRatio="none" class="w-full" style="height:{height}px">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


