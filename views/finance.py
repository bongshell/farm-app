"""หน้า 3 — บัญชีรายรับ-รายจ่าย"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.ui import has_cols
from config.constants import (
    CROP_PALM,
    CROP_RUBBER,
    EXPENSE_CATEGORIES,
    FRUIT_CROPS,
    FRUIT_GRADES,
    TBL_TX,
    TX_EXPENSE,
    TX_INCOME,
)
from services.db import insert_row

WEIGH_MODE_AUTO = "ชั่งรถเข้า-ออก (อัตโนมัติ)"
WEIGH_MODE_MANUAL = "ระบุน้ำหนักสุทธิ"


# ---------------------------------------------------------
# ฟอร์มรายรับแยกตามชนิดพืช
# ---------------------------------------------------------
def _income_palm(plot_id: int, tx_date: date) -> None:
    st.subheader("🌴 ขายผลผลิตปาล์มน้ำมัน")

    mode = st.radio(
        "รูปแบบการคำนวณน้ำหนัก",
        [WEIGH_MODE_AUTO, WEIGH_MODE_MANUAL],
        horizontal=True,
    )

    if mode == WEIGH_MODE_AUTO:
        c_in, c_out = st.columns(2)
        weight_in = c_in.number_input("น้ำหนักขาเข้า (กก.)", min_value=0.0, step=10.0)
        weight_out = c_out.number_input("น้ำหนักขาออก (กก.)", min_value=0.0, step=10.0)
        if weight_out > weight_in:
            st.warning("น้ำหนักขาออกมากกว่าขาเข้า กรุณาตรวจสอบตัวเลข")
        net_weight = max(weight_in - weight_out, 0.0)
    else:
        weight_in = weight_out = None
        net_weight = st.number_input("น้ำหนักสุทธิ (กก.)", min_value=0.0, step=10.0)

    price = st.number_input("ราคาต่อ กก. (บาท)", min_value=0.0, step=0.1)
    wage = st.number_input("ค่าแทง/ค่าจ้างตัด (บาท)", min_value=0.0, step=50.0)
    fuel = st.number_input("ค่าน้ำมันขนส่ง (บาท)", min_value=0.0, step=50.0)

    net_income = net_weight * price - (wage + fuel)
    st.info(f"รายรับสุทธิหลังหักค่าใช้จ่าย: **{net_income:,.2f} บาท** (น้ำหนัก {net_weight:,.0f} กก.)")

    if st.button("💾 บันทึกขายปาล์ม", type="primary", disabled=net_weight <= 0 or price <= 0):
        insert_row(
            TBL_TX,
            {
                "plot_id": plot_id,
                "tx_date": str(tx_date),
                "crop_type": CROP_PALM,
                "tx_type": TX_INCOME,
                "category": "ขายปาล์ม",
                "weight_in": weight_in,
                "weight_out": weight_out,
                "net_weight": net_weight,
                "price_per_kg": price,
                "cutting_wage": wage,
                "fuel_cost": fuel,
                "total_amount": net_income,
            },
            "บันทึกรายการขายปาล์มสำเร็จ!",
        )


def _income_fruit(plot_id: int, tx_date: date, crop_type: str) -> None:
    st.subheader(f"🍈 ขายผลผลิต{crop_type} (คัดเกรด)")

    grade = st.selectbox("เกรดผลผลิต", FRUIT_GRADES)
    weight = st.number_input("น้ำหนักรวม (กก.)", min_value=0.0, step=1.0)
    price = st.number_input("ราคาต่อ กก. (บาท)", min_value=0.0, step=1.0)
    harvest_wage = st.number_input("ค่าแรงเก็บเกี่ยว/ขนย้าย (บาท)", min_value=0.0, step=50.0)

    net_amount = weight * price - harvest_wage
    st.info(f"ยอดเงินสุทธิ: **{net_amount:,.2f} บาท**")

    if st.button(f"💾 บันทึกขาย{crop_type}", type="primary", disabled=weight <= 0 or price <= 0):
        insert_row(
            TBL_TX,
            {
                "plot_id": plot_id,
                "tx_date": str(tx_date),
                "crop_type": crop_type,
                "tx_type": TX_INCOME,
                "category": f"ขาย{crop_type} ({grade})",
                "grade": grade,
                "net_weight": weight,
                "price_per_kg": price,
                "cutting_wage": harvest_wage,
                "total_amount": net_amount,
            },
            f"บันทึกรายการขาย{crop_type}สำเร็จ!",
        )


def _income_rubber(plot_id: int, tx_date: date) -> None:
    st.subheader("🌳 ขายน้ำยาง / ขี้ยาง")

    weight = st.number_input("ปริมาณเนื้อยาง (กก.)", min_value=0.0, step=1.0)
    price = st.number_input("ราคาต่อ กก. (บาท)", min_value=0.0, step=0.5)
    owner_share = st.slider("ส่วนแบ่งเจ้าของสวน (%)", 0, 100, 60)

    total_value = weight * price
    owner_value = total_value * owner_share / 100
    st.info(
        f"ส่วนแบ่งเจ้าของ ({owner_share}%): **{owner_value:,.2f} บาท** "
        f"(คนกรีดได้ {total_value - owner_value:,.2f} บาท)"
    )

    if st.button("💾 บันทึกขายยาง", type="primary", disabled=weight <= 0 or price <= 0):
        insert_row(
            TBL_TX,
            {
                "plot_id": plot_id,
                "tx_date": str(tx_date),
                "crop_type": CROP_RUBBER,
                "tx_type": TX_INCOME,
                "category": "ขายยาง",
                "net_weight": weight,
                "price_per_kg": price,
                "owner_share_pct": owner_share,
                "total_amount": owner_value,
            },
            "บันทึกรายการขายยางสำเร็จ!",
        )


INCOME_FORMS = {CROP_PALM: _income_palm, CROP_RUBBER: _income_rubber}


# ---------------------------------------------------------
# ฟอร์มรายจ่าย (ใช้ร่วมทุกพืช)
# ---------------------------------------------------------
def _expense_form(plot_id: int, tx_date: date, crop_type: str) -> None:
    st.markdown("---")
    st.subheader("🧾 บันทึกค่าใช้จ่ายแปลง (ปุ๋ย, ยา, ตัดหญ้า)")

    with st.form("expense_form", clear_on_submit=True):
        col_cat, col_amt = st.columns(2)
        category = col_cat.selectbox("หมวดหมู่ค่าใช้จ่าย", EXPENSE_CATEGORIES)
        amount = col_amt.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=50.0)
        note = st.text_input("หมายเหตุ / ชื่อร้านค้า")

        if not st.form_submit_button("บันทึกรายจ่าย"):
            return

        if amount <= 0:
            st.warning("กรุณาระบุจำนวนเงินมากกว่า 0 บาท")
            return

        insert_row(
            TBL_TX,
            {
                "plot_id": plot_id,
                "tx_date": str(tx_date),
                "crop_type": crop_type,
                "tx_type": TX_EXPENSE,
                "category": category,
                "total_amount": amount,
                "note": note.strip() or None,
            },
            "บันทึกรายจ่ายเรียบร้อย!",
        )


# ---------------------------------------------------------
def render(plots_df: pd.DataFrame) -> None:
    st.header("💰 บันทึกรายรับ-รายจ่าย")

    if not has_cols(plots_df, ["id", "plot_name", "crop_type"]):
        st.warning("กรุณาเพิ่มแปลงที่เมนู 'การจัดการแปลง' ก่อนทำการบันทึกข้อมูลครับ")
        st.stop()

    selected_name = st.selectbox("เลือกแปลงที่ต้องการบันทึก", plots_df["plot_name"])
    plot = plots_df.loc[plots_df["plot_name"] == selected_name].iloc[0]
    plot_id = int(plot["id"])
    crop_type = str(plot["crop_type"])
    tx_date = st.date_input("วันที่ทำรายการ", value=date.today())

    st.markdown(f"**พืชประจำแปลง:** `{crop_type}`")

    if crop_type in INCOME_FORMS:
        INCOME_FORMS[crop_type](plot_id, tx_date)
    elif crop_type in FRUIT_CROPS:
        _income_fruit(plot_id, tx_date, crop_type)
    else:
        st.info("พืชชนิดนี้ยังไม่มีแบบฟอร์มรายรับเฉพาะ — บันทึกได้เฉพาะรายจ่ายด้านล่าง")

    _expense_form(plot_id, tx_date, crop_type)
