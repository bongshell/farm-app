"""หน้า 2 — การจัดการแปลง (รองรับพืชผสมหลายชนิด + เอกสารสิทธิ์ราชการ)"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import empty_state
from config.constants import (
    CROP_OPTIONS,
    DEED_NONE,
    DEED_NOTES,
    DEED_TYPES,
    DEFAULT_PROVINCE,
    PROVINCES,
    TBL_PLOT_CROPS,
    TBL_PLOTS,
)
from services.db import fetch_table, finish, insert_many, insert_returning

CROP_EDITOR_KEY = "plot_crop_editor"
FORM_KEYS = [
    "plot_name", "plot_rai", "plot_ngan", "plot_wa", "plot_lat", "plot_lng",
    "deed_type", "prov", "district", "subdistrict", "moo", "village", "plot_note",
    CROP_EDITOR_KEY,
] + [f"deed_{k}" for k in ("deed_no", "deed_book", "deed_page", "land_no", "survey_page", "map_sheet")]

EMPTY_CROPS = pd.DataFrame(
    [{"ชนิดพืช": None, "สายพันธุ์": "", "พื้นที่ (ไร่)": 0.0, "จำนวนต้น": 0, "ปีที่ปลูก (พ.ศ.)": None}]
)


# ---------------------------------------------------------
# แท็บ 1 — รายชื่อแปลง
# ---------------------------------------------------------
def _crop_summary(crops_df: pd.DataFrame) -> dict[int, str]:
    """รวมชนิดพืชของแต่ละแปลงเป็นข้อความเดียว"""
    if crops_df.empty or "plot_id" not in crops_df.columns:
        return {}
    summary: dict[int, str] = {}
    for plot_id, grp in crops_df.groupby("plot_id"):
        parts = []
        for _, row in grp.iterrows():
            label = str(row.get("crop_type", ""))
            area = row.get("area_rai")
            if pd.notna(area) and float(area or 0) > 0:
                label += f" {float(area):.1f} ไร่"
            parts.append(label)
        summary[int(plot_id)] = " • ".join(parts)
    return summary


def _plot_list(plots_df: pd.DataFrame) -> None:
    if plots_df.empty:
        empty_state("ยังไม่มีข้อมูลแปลง — เพิ่มได้ที่แท็บ 'เพิ่มแปลงใหม่'")
        return

    crops_df = fetch_table(TBL_PLOT_CROPS)
    summary = _crop_summary(crops_df)

    view = plots_df.copy()
    view["พืชในแปลง"] = view["id"].map(summary).fillna("—") if "id" in view.columns else "—"

    cols_map = {
        "plot_name": "ชื่อแปลง",
        "พืชในแปลง": "พืชในแปลง",
        "area_rai": "เนื้อที่ (ไร่)",
        "deed_type": "ประเภทเอกสารสิทธิ์",
        "deed_no": "เลขที่เอกสาร",
        "subdistrict": "ตำบล",
        "district": "อำเภอ",
        "province": "จังหวัด",
    }
    show = [c for c in cols_map if c in view.columns]
    st.dataframe(
        view[show].rename(columns=cols_map),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"ทั้งหมด {len(plots_df)} แปลง • รวม {view.get('area_rai', pd.Series(dtype=float)).sum():,.2f} ไร่")

    with st.expander("📋 ดูรายละเอียดพืชรายแปลง"):
        if crops_df.empty:
            st.info("ยังไม่มีข้อมูลพืชในแปลง")
        else:
            merged = crops_df.merge(
                plots_df[["id", "plot_name"]].rename(columns={"id": "plot_id"}),
                on="plot_id", how="left",
            )
            detail_map = {
                "plot_name": "ชื่อแปลง", "crop_type": "ชนิดพืช", "variety": "สายพันธุ์",
                "area_rai": "พื้นที่ (ไร่)", "tree_count": "จำนวนต้น", "planted_year": "ปีที่ปลูก",
            }
            cols = [c for c in detail_map if c in merged.columns]
            st.dataframe(merged[cols].rename(columns=detail_map),
                         use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# แท็บ 2 — ส่วนย่อยของฟอร์มเพิ่มแปลง
# ---------------------------------------------------------
def _section_basic() -> tuple[str, float, float, float, float]:
    st.markdown("##### 📌 ข้อมูลทั่วไป")
    plot_name = st.text_input("ชื่อแปลง *", key="plot_name",
                              placeholder="เช่น สวนเขาบางเนียง, แปลงหน้าบ้าน")

    st.caption("เนื้อที่ตามเอกสารสิทธิ์ (กรอกตามหน้าเอกสารจริง)")
    c1, c2, c3, c4 = st.columns(4)
    rai = c1.number_input("ไร่", min_value=0.0, step=1.0, key="plot_rai")
    ngan = c2.number_input("งาน", min_value=0.0, max_value=3.0, step=1.0, key="plot_ngan")
    wa = c3.number_input("ตารางวา", min_value=0.0, max_value=99.0, step=1.0, key="plot_wa")
    total_rai = rai + ngan / 4 + wa / 400
    c4.metric("รวมเป็นไร่", f"{total_rai:,.3f}")
    return plot_name, rai, ngan, wa, total_rai


def _section_crops() -> pd.DataFrame:
    st.markdown("##### 🌱 ชนิดพืชในแปลง (ใส่ได้หลายชนิด)")
    st.caption("กดที่แถวว่างด้านล่างเพื่อเพิ่มพืชชนิดถัดไป • ลบแถวด้วยการเลือกแถวแล้วกด Delete")

    edited = st.data_editor(
        EMPTY_CROPS,
        key=CROP_EDITOR_KEY,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ชนิดพืช": st.column_config.SelectboxColumn(options=CROP_OPTIONS, width="medium"),
            "สายพันธุ์": st.column_config.TextColumn(
                help="เช่น หมอนทอง, ชะนี, RRIM 600, เทเนอรา", width="medium"),
            "พื้นที่ (ไร่)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "จำนวนต้น": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            "ปีที่ปลูก (พ.ศ.)": st.column_config.NumberColumn(
                min_value=2500, max_value=2600, step=1, format="%d"),
        },
    )
    return edited


def _section_location() -> dict[str, str]:
    st.markdown("##### 🏠 ที่ตั้งแปลง")
    c1, c2, c3 = st.columns(3)
    province = c1.selectbox(
        "จังหวัด", PROVINCES, key="prov",
        index=PROVINCES.index(DEFAULT_PROVINCE) if DEFAULT_PROVINCE in PROVINCES else 0,
    )
    district = c2.text_input("อำเภอ", key="district", placeholder="เช่น ตะกั่วป่า")
    subdistrict = c3.text_input("ตำบล", key="subdistrict", placeholder="เช่น คึกคัก")

    c4, c5 = st.columns(2)
    moo = c4.text_input("หมู่ที่", key="moo", placeholder="เช่น 5")
    village = c5.text_input("ชื่อหมู่บ้าน", key="village", placeholder="เช่น บ้านบางเนียง")

    return {
        "province": province, "district": district.strip(),
        "subdistrict": subdistrict.strip(), "moo": moo.strip(), "village": village.strip(),
    }


def _section_deed() -> dict[str, str]:
    st.markdown("##### 📜 เอกสารสิทธิ์ที่ดิน")
    deed_type = st.selectbox("ประเภทเอกสารสิทธิ์", list(DEED_TYPES.keys()), key="deed_type")

    note = DEED_NOTES.get(deed_type)
    if note:
        st.caption(note)

    data: dict[str, str] = {}
    fields = DEED_TYPES[deed_type]
    if fields:
        for i in range(0, len(fields), 3):
            chunk = fields[i:i + 3]
            cols = st.columns(len(chunk))
            for col, (key, label, hint) in zip(cols, chunk):
                data[key] = col.text_input(label, key=f"deed_{key}", placeholder=hint).strip()

    return {"deed_type": None if deed_type == DEED_NONE else deed_type, **data}


def _section_coords() -> tuple[float, float]:
    st.markdown("##### 📍 พิกัดแปลง (ไม่บังคับ)")
    c1, c2 = st.columns(2)
    lat = c1.number_input("ละติจูด", value=0.0, format="%.6f", key="plot_lat", help="เช่น 8.123456")
    lng = c2.number_input("ลองจิจูด", value=0.0, format="%.6f", key="plot_lng", help="เช่น 98.123456")
    return lat, lng


# ---------------------------------------------------------
def _clean_crop_rows(edited: pd.DataFrame) -> list[dict]:
    """แปลงตารางที่ผู้ใช้กรอกเป็น list พร้อมบันทึก"""
    rows: list[dict] = []
    for _, r in edited.iterrows():
        crop = r.get("ชนิดพืช")
        if not crop or (isinstance(crop, float) and pd.isna(crop)):
            continue
        rows.append({
            "crop_type": str(crop),
            "variety": (str(r.get("สายพันธุ์") or "").strip() or None),
            "area_rai": float(r.get("พื้นที่ (ไร่)") or 0) or None,
            "tree_count": int(r.get("จำนวนต้น") or 0) or None,
            "planted_year": int(r["ปีที่ปลูก (พ.ศ.)"]) if pd.notna(r.get("ปีที่ปลูก (พ.ศ.)")) else None,
        })
    return rows


def _main_crop(rows: list[dict]) -> str:
    """พืชหลัก = พืชที่ใช้พื้นที่มากที่สุด (ใช้กับกราฟและรายงานเดิม)"""
    return max(rows, key=lambda r: r["area_rai"] or 0)["crop_type"]


def _plot_form() -> None:
    plot_name, rai, ngan, wa, total_rai = _section_basic()
    st.divider()
    edited = _section_crops()
    st.divider()
    location = _section_location()
    st.divider()
    deed = _section_deed()
    st.divider()
    lat, lng = _section_coords()

    st.divider()
    if not st.button("💾 บันทึกข้อมูลแปลง", type="primary", use_container_width=True):
        return

    # ---------- ตรวจความถูกต้อง ----------
    name = plot_name.strip()
    crop_rows = _clean_crop_rows(edited)

    if not name:
        st.warning("กรุณากรอกชื่อแปลง")
        return
    if not crop_rows:
        st.warning("กรุณาเลือกชนิดพืชอย่างน้อย 1 ชนิด")
        return
    if total_rai <= 0:
        st.warning("กรุณาระบุเนื้อที่แปลง (ไร่/งาน/ตารางวา)")
        return

    crop_area = sum(r["area_rai"] or 0 for r in crop_rows)
    if crop_area > total_rai + 0.01:
        st.warning(f"พื้นที่พืชรวม {crop_area:,.2f} ไร่ มากกว่าเนื้อที่แปลง {total_rai:,.2f} ไร่ กรุณาตรวจสอบ")
        return

    # ---------- บันทึกแปลง ----------
    payload = {
        "plot_name": name,
        "crop_type": _main_crop(crop_rows),
        "is_mixed": len(crop_rows) > 1,
        "area_rai": round(total_rai, 3),
        "rai": rai or None, "ngan": ngan or None, "wa": wa or None,
        "lat": lat or None, "lng": lng or None,
        **location, **deed,
    }

    created = insert_returning(TBL_PLOTS, payload)
    if not created:
        return

    crops_payload = [{**r, "plot_id": created["id"]} for r in crop_rows]
    if not insert_many(TBL_PLOT_CROPS, crops_payload):
        st.warning("บันทึกแปลงสำเร็จ แต่บันทึกรายการพืชไม่สำเร็จ กรุณาเพิ่มพืชอีกครั้ง")
        return

    finish(
        f"บันทึกแปลง '{name}' พร้อมพืช {len(crop_rows)} ชนิด สำเร็จแล้ว!",
        reset_keys=FORM_KEYS,
    )


# ---------------------------------------------------------
def render(plots_df: pd.DataFrame) -> None:
    st.header("🗂️ การจัดการแปลงเกษตรกรรม")
    tab_list, tab_add = st.tabs(["รายชื่อแปลงทั้งหมด", "➕ เพิ่มแปลงใหม่"])

    with tab_list:
        _plot_list(plots_df)
    with tab_add:
        _plot_form()
