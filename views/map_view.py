"""หน้า 5 — แผนที่แปลงเกษตร"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import has_cols
from config.constants import MAP_ZOOM

MAP_TABLE_COLS = ["plot_name", "crop_type", "variety", "area_rai", "lat", "lng", "deed_no"]


def _valid_coordinates(plots_df: pd.DataFrame) -> pd.DataFrame:
    """กรองเฉพาะแปลงที่มีพิกัดใช้งานได้จริง (ตัด NaN และ 0,0 กลางทะเล)."""
    df = plots_df.dropna(subset=["lat", "lng"]).copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])
    return df[(df["lat"] != 0) & (df["lng"] != 0)]


def render(plots_df: pd.DataFrame) -> None:
    st.header("📍 แผนที่แสดงพิกัดแปลงเกษตรกรรมทั้งหมด")
    st.markdown("ดูตำแหน่งแปลงที่ปักหมุดไว้ เพื่อวางแผนการเดินทางและการจัดการผลผลิต")

    if not has_cols(plots_df, ["lat", "lng"]):
        st.info("ยังไม่มีข้อมูลแปลง หรือยังไม่มีคอลัมน์พิกัดในฐานข้อมูล")
        return

    valid = _valid_coordinates(plots_df)
    if valid.empty:
        st.info("ยังไม่มีแปลงที่ระบุพิกัด Latitude / Longitude — เพิ่มได้ที่เมนู 'การจัดการแปลง'")
        return

    st.map(
        valid.rename(columns={"lat": "latitude", "lng": "longitude"}),
        zoom=MAP_ZOOM,
    )

    st.markdown("---")
    st.subheader("ตารางพิกัดแปลง")
    cols = [c for c in MAP_TABLE_COLS if c in valid.columns]
    st.dataframe(valid[cols], use_container_width=True, hide_index=True)
    st.caption(f"แสดง {len(valid)} จาก {len(plots_df)} แปลง (แปลงที่ไม่มีพิกัดจะไม่ถูกแสดง)")
