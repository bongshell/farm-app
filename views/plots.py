"""หน้า 2 — การจัดการแปลง"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import empty_state
from config.constants import CROP_OPTIONS, TBL_PLOTS
from services.db import insert_row


def _plot_list(plots_df: pd.DataFrame) -> None:
    if plots_df.empty:
        empty_state("ยังไม่มีข้อมูลแปลง — เพิ่มได้ที่แท็บ 'เพิ่มแปลงใหม่'")
        return
    st.dataframe(plots_df, use_container_width=True, hide_index=True)
    st.caption(f"ทั้งหมด {len(plots_df)} แปลง")


def _plot_form() -> None:
    with st.form("plot_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        plot_name = col_a.text_input("ชื่อแปลง *", placeholder="เช่น แปลงหน้าบ้าน, สวนเนินเขา")
        crop_type = col_b.selectbox("ชนิดพืชหลัก *", CROP_OPTIONS)
        variety = col_a.text_input("สายพันธุ์", placeholder="เช่น หมอนทอง, ชะนี, RRIM 600")
        area_rai = col_b.number_input("ขนาดพื้นที่ (ไร่) *", min_value=0.0, step=0.5)

        col_lat, col_lng = st.columns(2)
        lat = col_lat.number_input("ละติจูด", value=0.0, format="%.6f", help="เช่น 8.123456")
        lng = col_lng.number_input("ลองจิจูด", value=0.0, format="%.6f", help="เช่น 99.123456")

        deed_no = st.text_input("เลขที่โฉนด / เอกสารสิทธิ์ (ถ้ามี)")

        if not st.form_submit_button("💾 บันทึกข้อมูลแปลง", type="primary"):
            return

        name = plot_name.strip()
        if not name:
            st.warning("กรุณากรอกชื่อแปลง")
            return
        if area_rai <= 0:
            st.warning("กรุณาระบุขนาดพื้นที่มากกว่า 0 ไร่")
            return

        insert_row(
            TBL_PLOTS,
            {
                "plot_name": name,
                "crop_type": crop_type,
                "variety": variety.strip() or None,   # ← บั๊กเดิม: เก็บค่าแล้วไม่ได้บันทึก
                "area_rai": area_rai,
                "lat": lat or None,                   # 0.0 = ยังไม่ระบุพิกัด
                "lng": lng or None,
                "deed_no": deed_no.strip() or None,
            },
            f"บันทึกแปลง '{name}' สำเร็จแล้ว!",
        )


def render(plots_df: pd.DataFrame) -> None:
    st.header("🗂️ การจัดการแปลงเกษตรกรรม")
    tab_list, tab_add = st.tabs(["รายชื่อแปลงทั้งหมด", "➕ เพิ่มแปลงใหม่"])

    with tab_list:
        _plot_list(plots_df)
    with tab_add:
        _plot_form()
