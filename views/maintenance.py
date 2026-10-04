"""หน้า 4 — การบำรุงรักษา & ปัจจัยการผลิต"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.ui import empty_state
from config.constants import (
    PRICE_UNITS,
    PRODUCT_CATEGORIES,
    TBL_CONTRACTORS,
    TBL_FERT,
    TBL_SHOPS,
)
from services.db import (
    delete_row,
    fetch_table,
    finish,
    insert_returning,
    insert_row,
    update_row_silent,
)

VERSION_KEY = "maint_form_version"


def _k(name: str) -> str:
    return f"{name}_v{st.session_state.get(VERSION_KEY, 0)}"


def _bump_version() -> None:
    st.session_state[VERSION_KEY] = st.session_state.get(VERSION_KEY, 0) + 1


# =========================================================
# แท็บ 1 — ร้านค้า (ข้อมูลหลัก: ชื่อ / เบอร์โทร / ที่อยู่)
# =========================================================
def _shop_form() -> None:
    st.markdown("##### ➕ เพิ่มร้านค้าใหม่")
    with st.form("shop_form", clear_on_submit=True):
        name = st.text_input("ชื่อร้านค้า *", placeholder="เช่น ร้านเกษตรรุ่งเรือง")
        c1, c2 = st.columns(2)
        phone = c1.text_input("เบอร์โทรศัพท์", placeholder="เช่น 081-234-5678")
        address = c2.text_input("ที่อยู่ / ทำเล", placeholder="เช่น ตลาดตะกั่วป่า อ.ตะกั่วป่า")

        if st.form_submit_button("💾 บันทึกร้านค้า", type="primary"):
            if not name.strip():
                st.warning("กรุณากรอกชื่อร้านค้า")
            else:
                insert_row(
                    TBL_SHOPS,
                    {
                        "shop_name": name.strip(),
                        "phone": phone.strip() or None,
                        "address": address.strip() or None,
                    },
                    f"เพิ่มร้านค้า '{name.strip()}' สำเร็จแล้ว!",
                )


def _shop_edit(shops_df: pd.DataFrame) -> None:
    st.markdown("##### ✏️ แก้ไข / ลบร้านค้า")
    if shops_df.empty:
        empty_state("ยังไม่มีร้านค้าในระบบ")
        return

    selected = st.selectbox("เลือกร้านค้า", shops_df["shop_name"], key=_k("shop_select"))
    shop = shops_df.loc[shops_df["shop_name"] == selected].iloc[0]
    shop_id = int(shop["id"])

    name = st.text_input("ชื่อร้านค้า *", value=str(shop.get("shop_name") or ""), key=_k("edit_shop_name"))
    c1, c2 = st.columns(2)
    phone = c1.text_input("เบอร์โทรศัพท์", value=str(shop.get("phone") or ""), key=_k("edit_shop_phone"))
    address = c2.text_input("ที่อยู่ / ทำเล", value=str(shop.get("address") or ""), key=_k("edit_shop_address"))

    col_save, col_del = st.columns([3, 1])
    if col_save.button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True, key=_k("save_shop")):
        if not name.strip():
            st.warning("กรุณากรอกชื่อร้านค้า")
        else:
            ok = update_row_silent(
                TBL_SHOPS, shop_id,
                {"shop_name": name.strip(), "phone": phone.strip() or None, "address": address.strip() or None},
            )
            if ok:
                finish(f"แก้ไขร้านค้า '{name.strip()}' สำเร็จแล้ว!")

    if col_del.button("🗑️ ลบร้าน", use_container_width=True, key=_k("del_shop")):
        st.session_state[f"confirm_del_shop_{shop_id}"] = True

    if st.session_state.get(f"confirm_del_shop_{shop_id}"):
        st.error(f"ยืนยันลบร้าน '{selected}'? ประวัติราคาที่เคยบันทึกไว้จะยังอยู่ แต่จะไม่ผูกกับร้านนี้อีก")
        cc1, cc2 = st.columns(2)
        if cc1.button("✅ ยืนยันลบ", key=_k("confirm_del_shop_yes")):
            delete_row(TBL_SHOPS, shop_id, f"ลบร้าน '{selected}' เรียบร้อยแล้ว")
        if cc2.button("❌ ยกเลิก", key=_k("confirm_del_shop_no")):
            st.session_state[f"confirm_del_shop_{shop_id}"] = False
            st.rerun()


def _shop_tab(shops_df: pd.DataFrame) -> None:
    sub_add, sub_list = st.tabs(["➕ เพิ่มร้านค้า", "✏️ แก้ไข/ลบร้านค้า"])
    with sub_add:
        _shop_form()
        st.divider()
        if shops_df.empty:
            empty_state("ยังไม่มีร้านค้าในระบบ")
        else:
            show_cols = {"shop_name": "ชื่อร้าน", "phone": "เบอร์โทร", "address": "ที่อยู่"}
            cols = [c for c in show_cols if c in shops_df.columns]
            st.dataframe(shops_df[cols].rename(columns=show_cols), use_container_width=True, hide_index=True)
    with sub_list:
        _shop_edit(shops_df)


# =========================================================
# แท็บ 2 — บันทึกสืบราคา
# =========================================================
def _price_form(shops_df: pd.DataFrame) -> None:
    st.markdown("##### ➕ บันทึกราคาที่สืบมา")

    if shops_df.empty:
        st.warning("กรุณาเพิ่มร้านค้าก่อนที่แท็บ '🏪 ร้านค้า' จึงจะบันทึกราคาได้ครับ")
        return

    with st.form("price_form", clear_on_submit=True):
        shop_name = st.selectbox("ร้านค้า *", shops_df["shop_name"])

        c1, c2 = st.columns(2)
        category = c1.selectbox("หมวดหมู่สินค้า *", PRODUCT_CATEGORIES)
        unit = c2.selectbox("หน่วยราคา *", PRICE_UNITS)

        c3, c4 = st.columns(2)
        product_name = c3.text_input("ชื่อสินค้า / ยี่ห้อ *", placeholder="เช่น ปุ๋ยตรากระต่าย สูตร 15-15-15")
        variety = c4.text_input("สายพันธุ์ (ถ้ามี)", placeholder="เช่น ปาล์มลูกผสมเทเนอรา, ยาง RRIM 600")

        c5, c6 = st.columns(2)
        price = c5.number_input("ราคา (บาท) *", min_value=0.0, step=1.0)
        price_date = c6.date_input("วันที่สืบราคา *", value=date.today(), max_value=date.today())

        note = st.text_input("หมายเหตุ", placeholder="เช่น ราคาช่วงโปรโมชั่น, ซื้อยกลังลดเพิ่ม")

        if st.form_submit_button("💾 บันทึกราคา", type="primary"):
            if not product_name.strip():
                st.warning("กรุณากรอกชื่อสินค้า")
            elif price <= 0:
                st.warning("กรุณาระบุราคามากกว่า 0 บาท")
            else:
                shop_id = int(shops_df.loc[shops_df["shop_name"] == shop_name, "id"].iloc[0])
                insert_row(
                    TBL_FERT,
                    {
                        "shop_id": shop_id,
                        "category": category,
                        "product_name": product_name.strip(),
                        "variety": variety.strip() or None,
                        "price": price,
                        "unit": unit,
                        "price_date": str(price_date),
                        "note": note.strip() or None,
                    },
                    f"บันทึกราคา '{product_name.strip()}' สำเร็จแล้ว!",
                )


def _price_edit(shops_df: pd.DataFrame, prices_df: pd.DataFrame) -> None:
    st.markdown("##### ✏️ แก้ไข / ลบประวัติราคา")

    if prices_df.empty:
        empty_state("ยังไม่มีประวัติราคาที่บันทึกไว้")
        return

    merged = prices_df.merge(
        shops_df[["id", "shop_name"]].rename(columns={"id": "shop_id"}), on="shop_id", how="left"
    )
    merged["label"] = (
        merged.get("price_date", "").astype(str) + " | "
        + merged.get("shop_name", "").fillna("-") + " | "
        + merged.get("product_name", "").fillna("-")
    )

    selected_label = st.selectbox("เลือกรายการ", merged["label"], key=_k("price_select"))
    row = merged.loc[merged["label"] == selected_label].iloc[0]
    price_id = int(row["id"])

    shop_names = shops_df["shop_name"].tolist()
    current_shop_name = row.get("shop_name") or (shop_names[0] if shop_names else "")

    shop_name = st.selectbox(
        "ร้านค้า", shop_names,
        index=shop_names.index(current_shop_name) if current_shop_name in shop_names else 0,
        key=_k("edit_price_shop"),
    )

    c1, c2 = st.columns(2)
    category = c1.selectbox(
        "หมวดหมู่สินค้า", PRODUCT_CATEGORIES,
        index=PRODUCT_CATEGORIES.index(row["category"]) if row.get("category") in PRODUCT_CATEGORIES else 0,
        key=_k("edit_price_cat"),
    )
    unit = c2.selectbox(
        "หน่วยราคา", PRICE_UNITS,
        index=PRICE_UNITS.index(row["unit"]) if row.get("unit") in PRICE_UNITS else 0,
        key=_k("edit_price_unit"),
    )

    c3, c4 = st.columns(2)
    product_name = c3.text_input("ชื่อสินค้า / ยี่ห้อ", value=str(row.get("product_name") or ""), key=_k("edit_price_name"))
    variety = c4.text_input("สายพันธุ์", value=str(row.get("variety") or ""), key=_k("edit_price_variety"))

    c5, c6 = st.columns(2)
    price = c5.number_input("ราคา (บาท)", min_value=0.0, step=1.0, value=float(row.get("price") or 0), key=_k("edit_price_val"))
    try:
        default_date = pd.to_datetime(row.get("price_date")).date()
    except Exception:
        default_date = date.today()
    price_date = c6.date_input("วันที่สืบราคา", value=default_date, max_value=date.today(), key=_k("edit_price_date"))

    note = st.text_input("หมายเหตุ", value=str(row.get("note") or ""), key=_k("edit_price_note"))

    col_save, col_del = st.columns([3, 1])
    if col_save.button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True, key=_k("save_price")):
        if not product_name.strip():
            st.warning("กรุณากรอกชื่อสินค้า")
        else:
            shop_id = int(shops_df.loc[shops_df["shop_name"] == shop_name, "id"].iloc[0])
            ok = update_row_silent(
                TBL_FERT, price_id,
                {
                    "shop_id": shop_id, "category": category,
                    "product_name": product_name.strip(), "variety": variety.strip() or None,
                    "price": price, "unit": unit, "price_date": str(price_date),
                    "note": note.strip() or None,
                },
            )
            if ok:
                finish("แก้ไขประวัติราคาสำเร็จแล้ว!")

    if col_del.button("🗑️ ลบรายการ", use_container_width=True, key=_k("del_price")):
        delete_row(TBL_FERT, price_id, "ลบประวัติราคาเรียบร้อยแล้ว")


def _price_history(shops_df: pd.DataFrame, prices_df: pd.DataFrame) -> None:
    st.markdown("##### 📋 ประวัติราคาทั้งหมด")
    if prices_df.empty:
        empty_state("ยังไม่มีประวัติราคา")
        return

    merged = prices_df.merge(
        shops_df[["id", "shop_name"]].rename(columns={"id": "shop_id"}), on="shop_id", how="left"
    )

    f1, f2 = st.columns(2)
    filter_shop = f1.selectbox("กรองตามร้านค้า", ["ทั้งหมด"] + shops_df["shop_name"].tolist())
    filter_cat = f2.selectbox("กรองตามหมวดหมู่", ["ทั้งหมด"] + PRODUCT_CATEGORIES)

    view = merged.copy()
    if filter_shop != "ทั้งหมด":
        view = view[view["shop_name"] == filter_shop]
    if filter_cat != "ทั้งหมด":
        view = view[view["category"] == filter_cat]

    show_cols = {
        "price_date": "วันที่สืบราคา", "shop_name": "ร้านค้า", "category": "หมวดหมู่",
        "product_name": "สินค้า", "variety": "สายพันธุ์", "price": "ราคา", "unit": "หน่วย", "note": "หมายเหตุ",
    }
    cols = [c for c in show_cols if c in view.columns]
    view_sorted = view.sort_values("price_date", ascending=False) if "price_date" in view.columns else view
    st.dataframe(view_sorted[cols].rename(columns=show_cols), use_container_width=True, hide_index=True)
    st.caption(f"พบ {len(view)} รายการ")


def _price_tab(shops_df: pd.DataFrame) -> None:
    prices_df = fetch_table(TBL_FERT)
    sub_add, sub_edit, sub_hist = st.tabs(["➕ บันทึกราคาใหม่", "✏️ แก้ไข/ลบ", "📋 ประวัติทั้งหมด"])
    with sub_add:
        _price_form(shops_df)
    with sub_edit:
        _price_edit(shops_df, prices_df)
    with sub_hist:
        _price_history(shops_df, prices_df)


# =========================================================
# แท็บ 3 — ผู้รับจ้าง/ช่าง (คงเดิม)
# =========================================================
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
                    {"name": name.strip(), "phone": phone.strip() or None, "note": skill.strip() or None},
                    "บันทึกผู้รับจ้างเรียบร้อย!",
                )

    df = fetch_table(TBL_CONTRACTORS)
    if df.empty:
        st.info("ยังไม่มีข้อมูลผู้รับจ้าง")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# =========================================================
def render(_plots_df: pd.DataFrame | None = None) -> None:
    st.header("🛠️ การบำรุงรักษา & ปัจจัยการผลิต")

    shops_df = fetch_table(TBL_SHOPS)

    tab_price, tab_shop, tab_contractor = st.tabs(
        ["💰 สืบราคา", "🏪 ร้านค้า", "👷 ทะเบียนผู้รับจ้าง/ช่าง"]
    )
    with tab_price:
        _price_tab(shops_df)
    with tab_shop:
        _shop_tab(shops_df)
    with tab_contractor:
        _contractor_tab()
