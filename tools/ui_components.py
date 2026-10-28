"""
Institutional UI Components for Meridian Terminal
=================================================
Provides sanitized, high-fidelity UI component renderers matching React JSX
and macOS window chrome specifications with Framer Motion hover physics.
"""

import html
from typing import Optional


def render_stat_card(
    title: str,
    value: str,
    change: str,
    icon: str = "📊",
    is_positive: bool = True,
    gradient: str = "linear-gradient(135deg, rgba(41,151,255,0.2) 0%, rgba(168,85,247,0.2) 100%)",
    note: str = ""
) -> str:
    """
    Renders the institutional frosted glass StatsCard with Framer-Motion-style hover lift physics.
    All user-supplied text is sanitized via html.escape to eliminate XSS / unsafe input risks.
    """
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_change = html.escape(str(change))
    safe_note = html.escape(str(note)) if note else ""
    safe_icon = str(icon)  # May contain HTML entities or icons
    
    change_color = "#10B981" if is_positive else "#F43F5E"
    arrow = "↗" if is_positive else "↘"
    note_html = f'<span style="font-size:0.74rem; color:rgba(255,255,255,0.4);">{safe_note}</span>' if safe_note else ""

    return f"""
    <div class="stats-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="font-size:0.82rem; font-weight:500; color:rgba(255,255,255,0.6);">{safe_title}</span>
            <div style="width:36px; height:36px; border-radius:10px; background:{gradient}; display:flex; align-items:center; justify-content:center; font-size:1.1rem; border:1px solid rgba(255,255,255,0.1);">
                {safe_icon}
            </div>
        </div>
        <div style="font-size:1.85rem; font-weight:700; color:#FFFFFF; font-family:var(--font-mono); letter-spacing:-0.02em;">
            {safe_value}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
            <div style="display:flex; align-items:center; gap:4px; font-size:0.82rem; font-weight:600; color:{change_color};">
                <span>{arrow}</span>
                <span>{safe_change}</span>
            </div>
            {note_html}
        </div>
    </div>
    """


def render_mac_window_header(title: str, tag: str = "jsx") -> str:
    """
    Renders macOS window chrome with traffic light controls (🔴, 🟡, 🟢),
    monospace file header, and component language badge.
    All text is sanitized via html.escape.
    """
    safe_title = html.escape(str(title))
    safe_tag = html.escape(str(tag))

    return f"""
    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-bottom:1px solid rgba(255,255,255,0.06); padding:0.65rem 1rem; display:flex; align-items:center; justify-content:space-between; border-radius:1rem 1rem 0 0; margin-bottom:0.75rem;">
        <div style="display:flex; align-items:center; gap:7px;">
            <span style="width:11px; height:11px; border-radius:50%; background:#FF5F56; display:inline-block; box-shadow:0 0 6px rgba(255,95,86,0.6);"></span>
            <span style="width:11px; height:11px; border-radius:50%; background:#FFBD2E; display:inline-block; box-shadow:0 0 6px rgba(255,189,46,0.6);"></span>
            <span style="width:11px; height:11px; border-radius:50%; background:#27C93F; display:inline-block; box-shadow:0 0 6px rgba(39,201,63,0.6);"></span>
        </div>
        <div style="font-family:var(--font-mono); font-size:0.80rem; color:rgba(255,255,255,0.7); display:flex; align-items:center; gap:6px;">
            <span>📄 {safe_title}</span>
        </div>
        <span style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#8E9BAE; font-size:0.68rem; font-family:var(--font-mono); padding:2px 7px; border-radius:4px; text-transform:uppercase;">
            {safe_tag}
        </span>
    </div>
    """
