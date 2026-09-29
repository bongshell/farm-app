"""หน้า 4 — การบำรุงรักษา & ปัจจัยการผลิต"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from config.constants import TBL_CONTRACTORS, TBL_FERT
from services.db import fetch_table, insert_row


def _fertilizer_tab() -> None:
    with st.form("fertilizer_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        shop = col1.text_input("ชื่อร้านค้า *")
        product = col2.text_input("สูตรปุ๋ย / ชื่อสินค้า *")
        price = col3.number_input("ราคาต่อกระสอบ/หน่วย (บาท)", min_value=0.0, step=10.0)

        if st.form_submit_button("บันทึกราคาปุ๋ย", type="primary"):
            if not shop.strip() or not product.strip():
                st.warning("กรุณากรอกชื่อร้านค้าและชื่อสินค้า")
            elif price <= 0:
                st.warning("กรุณาระบุราคามากกว่า 0 บาท")
            else:
                insert_row(
                    TBL_FERT,
                    {
                        "shop_name": shop.strip(),
                        "product_name": product.strip(),
                        "price": price,
                        "checked_date": str(date.today()),
                    },
                    "บันทึกราคาปุ๋ยเรียบร้อย!",
                )

    df = fetch_table(TBL_FERT)
    if df.empty:
        st.info("ยังไม่มีข้อมูลราคาปุ๋ย")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def _contractor_tab() -> None:
    with st.form("contractor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("ชื่อคนงาน / ผู้รับจ้าง *")
        phone = col2.text_input("เบอร์โทรศัพท์")
        skill = st.text_input("ความเชี่ยวชาญ", placeholder="เช่น กรีดยาง, ตัดหญ้า, ขุดหลุม")

        if st.form_submit_button("บันทึกผู้รับจ้าง", type="primary"):
            if not name.strip():
                st.warning("กรุณากรอกชื่อผู้รับจ้าง")
            else:
                insert_row(
                    TBL_CONTRACTORS,
                    {
                        "name": name.strip(),
                        "phone": phone.strip() or None,
                        "note": skill.strip() or None,
                    },
                    "บันทึกผู้รับจ้างเรียบร้อย!",
                )

    df = fetch_table(TBL_CONTRACTORS)
    if df.empty:
        st.info("ยังไม่มีข้อมูลผู้รับจ้าง")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render(_plots_df: pd.DataFrame | None = None) -> None:
    """รับ plots_df ไว้เฉย ๆ เพื่อให้ signature ตรงกับหน้าอื่นใน router."""
    st.header("🛠️ การบำรุงรักษา & ปัจจัยการผลิต")

    tab_fert, tab_contractor = st.tabs(
        ["💰 บันทึกสืบราคาปุ๋ย", "👷 ทะเบียนผู้รับจ้าง/ช่าง"]
    )
    with tab_fert:
        _fertilizer_tab()
    with tab_contractor:
        _contractor_tab()
