"""ชิ้นส่วน UI ที่ใช้ซ้ำ + CSS กลางของแอป"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from config.constants import CHART_HEIGHT

CUSTOM_CSS = """
<style>
    header {visibility: hidden;}
    .main {background-color: #f4f6f9;}

    .hero-banner {
        background: linear-gradient(135deg, #0e2a47 0%, #1a4a75 100%);
        border-radius: 12px; padding: 24px 30px; color: #fff;
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,.08);
    }
    .hero-title    {font-size: 24px; font-weight: 700; margin-bottom: 6px;}
    .hero-subtitle {font-size: 14px; color: #b0c4de;}

    .stat-card {
        background: #fff; border-radius: 12px; padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,.04); border: 1px solid #eef2f6;
        display: flex; align-items: center; gap: 15px; height: 100%;
    }
    .stat-icon {
        width: 48px; height: 48px; border-radius: 10px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .stat-label {font-size: 13px; color: #64748b; font-weight: 500;}
    .stat-value {font-size: 22px; font-weight: 700; color: #1e293b; margin-top: 2px;}

    .chart-header {font-size: 15px; font-weight: 700; color: #1e293b; margin-bottom: 12px;}
</style>
"""

HERO_BANNER = """
<div class="hero-banner">
    <div class="hero-title">ระบบบริหารจัดการสวนและผลผลิตเกษตรอัจฉริยะ</div>
    <div class="hero-subtitle">ขับเคลื่อนการบริหารต้นทุน ปาล์มน้ำมัน ยางพารา ทุเรียน และไม้ผล อย่างแม่นยำ ครบวงจร</div>
</div>
"""


def inject_css() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def show_flash() -> None:
    """แสดงข้อความสำเร็จที่ฝากไว้ก่อน rerun (ไม่งั้นข้อความจะหายทันที)."""
    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg, icon="✅")


def has_cols(df: pd.DataFrame, cols: Iterable[str]) -> bool:
    """เช็กว่า DataFrame ไม่ว่างและมีคอลัมน์ครบตามที่ต้องใช้."""
    return not df.empty and all(c in df.columns for c in cols)


def safe_sum(df: pd.DataFrame, col: str, mask: pd.Series | None = None) -> float:
    """รวมค่าคอลัมน์แบบไม่พัง แม้คอลัมน์ไม่มีอยู่หรือมี NaN/ข้อความปน."""
    if df.empty or col not in df.columns:
        return 0.0
    series = df[col] if mask is None else df.loc[mask, col]
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def kpi_card(container, icon: str, bg: str, fg: str, label: str, value: str) -> None:
    """การ์ดสถิติ 1 ใบ — เรียกซ้ำแทนการ copy HTML 5 รอบ."""
    container.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-icon" style="background:{bg}; color:{fg};">{icon}</div>
            <div>
                <div class="stat-label">{label}</div>
                <div class="stat-value">{value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_box(title: str):
    """กรอบกราฟที่ 'ครอบติดจริง' — ใช้ st.container(border=True) แทน div ลอย."""
    box = st.container(border=True)
    box.markdown(f'<div class="chart-header">{title}</div>', unsafe_allow_html=True)
    return box


def compact_layout(fig, height: int = CHART_HEIGHT):
    """ตัดขอบกราฟให้พอดีกับการ์ด."""
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=height)
    return fig


def empty_state(message: str) -> None:
    st.info(message)
