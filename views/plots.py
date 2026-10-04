"""หน้า 2 — การจัดการแปลง (พืชผสมหลายชนิด + เอกสารสิทธิ์ราชการ)"""

from __future__ import annotations

from typing import Any

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
from services.db import (
    delete_row,
    delete_silent,
    fetch_table,
    finish,
    insert_many,
    insert_returning,
    replace_crops,
    update_row_silent,
)

VERSION_KEY = "plot_form_version"

EMPTY_CROPS = pd.DataFrame(
    [{"ชนิดพืช": None, "สายพันธุ์": "", "พื้นที่ (ไร่)": None,
      "จำนวนต้น": None, "ปีที่ปลูก (พ.ศ.)": None}]
)


# ---------------------------------------------------------
# ตัวช่วย
# ---------------------------------------------------------
def _k(name: str) -> str:
    """key ที่มีเลขเวอร์ชันต่อท้าย — เพิ่มเวอร์ชัน = ฟอร์มว่างใหม่ทั้งชุด"""
    return f"{name}_v{st.session_state.get(VERSION_KEY, 0)}"


def _is_blank(val: Any) -> bool:
    if val is None or val == "":
        return True
    try:
        return bool(pd.isna(val))
    except (TypeError, ValueError):
        return False


def _safe_float(val: Any) -> float | None:
    if _is_blank(val):
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(num) else num


def _safe_int(val: Any) -> int | None:
    num = _safe_float(val)
    return None if num is None else int(num)


# ---------------------------------------------------------
# แท็บ 1 — รายชื่อแปลง
# ---------------------------------------------------------
def _crop_summary(crops_df: pd.DataFrame) -> dict[int, str]:
    if crops_df.empty or "plot_id" not in crops_df.columns:
        return {}

    summary: dict[int, str] = {}
    for plot_id, grp in crops_df.groupby("plot_id"):
        parts = []
        for _, row in grp.iterrows():
            label = str(row.get("crop_type", ""))
            area = _safe_float(row.get("area_rai"))
            if area:
                label += f" {area:.1f} ไร่"
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
    if "id" in view.columns:
        view["พืชในแปลง"] = view["id"].map(summary).fillna("—")
    else:
        view["พืชในแปลง"] = "—"

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

    total_area = pd.to_numeric(view.get("area_rai"), errors="coerce").fillna(0).sum()
    st.caption(f"ทั้งหมด {len(plots_df)} แปลง • รวม {total_area:,.2f} ไร่")

    if "deed_note" in view.columns:
        noted = view[
            view["deed_note"].notna() & (view["deed_note"].astype(str).str.strip() != "")
        ]
        if not noted.empty:
            with st.expander(f"📝 หมายเหตุการครอบครอง ({len(noted)} แปลง)"):
                for _, row in noted.iterrows():
                    st.markdown(f"**{row.get('plot_name', '-')}**")
                    st.caption(str(row["deed_note"]))
                    st.divider()

    with st.expander("📋 ดูรายละเอียดพืชรายแปลง"):
        if crops_df.empty:
            st.info("ยังไม่มีข้อมูลพืชในแปลง")
        else:
            merged = crops_df.merge(
                plots_df[["id", "plot_name"]].rename(columns={"id": "plot_id"}),
                on="plot_id",
                how="left",
            )
            detail_map = {
                "plot_name": "ชื่อแปลง",
                "crop_type": "ชนิดพืช",
                "variety": "สายพันธุ์",
                "area_rai": "พื้นที่ (ไร่)",
                "tree_count": "จำนวนต้น",
                "planted_year": "ปีที่ปลูก",
            }
            cols = [c for c in detail_map if c in merged.columns]
            st.dataframe(
                merged[cols].rename(columns=detail_map),
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------
# แท็บ 2 — ฟอร์มเพิ่มแปลง
# ---------------------------------------------------------
def _section_basic() -> tuple[str, float, float, float, float]:
    st.markdown("##### 📌 ข้อมูลทั่วไป")
    plot_name = st.text_input(
        "ชื่อแปลง *",
        key=_k("plot_name"),
        placeholder="เช่น สวนเขาบางเนียง, แปลงหน้าบ้าน",
    )

    st.caption("เนื้อที่แปลง — ไม่บังคับ เว้นว่างไว้ได้ถ้ายังไม่ทราบ (1 ไร่ = 4 งาน = 400 ตร.ว.)")
    c1, c2, c3, c4 = st.columns(4)
    rai = c1.number_input("ไร่", min_value=0.0, step=1.0, key=_k("rai"))
    ngan = c2.number_input("งาน", min_value=0.0, max_value=3.0, step=1.0, key=_k("ngan"))
    wa = c3.number_input("ตารางวา", min_value=0.0, max_value=99.0, step=1.0, key=_k("wa"))

    total_rai = rai + ngan / 4 + wa / 400
    c4.metric("รวมเป็นไร่", f"{total_rai:,.3f}" if total_rai > 0 else "ยังไม่ระบุ")

    return plot_name, rai, ngan, wa, total_rai


def _section_crops() -> pd.DataFrame:
    st.markdown("##### 🌱 ชนิดพืชในแปลง (ใส่ได้หลายชนิด)")
    st.caption("กดแถวว่างด้านล่างเพื่อเพิ่มพืชชนิดถัดไป • เว้นช่องตัวเลขว่างไว้ได้ถ้ายังไม่ทราบ")

    return st.data_editor(
        EMPTY_CROPS,
        key=_k("crop_editor"),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ชนิดพืช": st.column_config.SelectboxColumn(options=CROP_OPTIONS, width="medium"),
            "สายพันธุ์": st.column_config.TextColumn(
                help="เช่น หมอนทอง, ชะนี, RRIM 600, เทเนอรา", width="medium"
            ),
            "พื้นที่ (ไร่)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "จำนวนต้น": st.column_config.NumberColumn(min_value=0, step=1),
            "ปีที่ปลูก (พ.ศ.)": st.column_config.NumberColumn(
                min_value=2500, max_value=2600, step=1
            ),
        },
    )


def _section_location() -> dict[str, Any]:
    st.markdown("##### 🏠 ที่ตั้งแปลง")
    c1, c2, c3 = st.columns(3)
    province = c1.selectbox(
        "จังหวัด",
        PROVINCES,
        key=_k("prov"),
        index=PROVINCES.index(DEFAULT_PROVINCE) if DEFAULT_PROVINCE in PROVINCES else 0,
    )
    district = c2.text_input("อำเภอ", key=_k("district"), placeholder="เช่น ตะกั่วป่า")
    subdistrict = c3.text_input("ตำบล", key=_k("subdistrict"), placeholder="เช่น คึกคัก")

    c4, c5 = st.columns(2)
    moo = c4.text_input("หมู่ที่", key=_k("moo"), placeholder="เช่น 5")
    village = c5.text_input("ชื่อหมู่บ้าน", key=_k("village"), placeholder="เช่น บ้านบางเนียง")

    return {
        "province": province,
        "district": district.strip() or None,
        "subdistrict": subdistrict.strip() or None,
        "moo": moo.strip() or None,
        "village": village.strip() or None,
    }


def _section_deed() -> dict[str, Any]:
    st.markdown("##### 📜 การถือครอง / เอกสารสิทธิ์ที่ดิน")
    deed_type = st.selectbox("ประเภทการถือครอง", list(DEED_TYPES.keys()), key=_k("deed_type"))

    note_hint = DEED_NOTES.get(deed_type)
    if note_hint:
        st.caption(note_hint)

    data: dict[str, Any] = {}
    fields = DEED_TYPES[deed_type]
    for i in range(0, len(fields), 3):
        chunk = fields[i:i + 3]
        cols = st.columns(len(chunk))
        for col, (key, label, hint) in zip(cols, chunk):
            value = col.text_input(label, key=_k(f"deed_{key}"), placeholder=hint)
            data[key] = value.strip() or None

    no_deed = deed_type == DEED_NONE
    if no_deed:
        st.info(
            "ไม่มีเอกสารสิทธิ์ — แนะนำให้บันทึกรายละเอียดการครอบครองไว้ในช่องด้านล่าง "
            "เพื่อใช้อ้างอิงภายในครอบครัวและวางแผนดำเนินการต่อ"
        )

    deed_note = st.text_area(
        "✍️ รายละเอียด / หมายเหตุการครอบครอง" + (" *" if no_deed else " (ถ้ามี)"),
        key=_k("deed_note"),
        height=120,
        placeholder=(
            "เช่น ด้านบนติดเขตอุทยาน ลุงวีให้ทำกิน 5 ไร่\n"
            "ด้านล่างทำกินอยู่ใน ส.ค.1 ชื่อลุงหนุ่ย อยู่ระหว่างขอออกโฉนดในชื่อแม่"
        ),
        help="พิมพ์ได้อิสระหลายบรรทัด — ใช้บันทึกที่มา ผู้ให้ทำกิน แนวเขต หรือสถานะการดำเนินเรื่อง",
    )

    return {
        "deed_type": None if no_deed else deed_type,
        "deed_note": deed_note.strip() or None,
        **data,
    }


def _section_coords() -> tuple[float, float]:
    st.markdown("##### 📍 พิกัดแปลง (ไม่บังคับ)")
    c1, c2 = st.columns(2)
    lat = c1.number_input("ละติจูด", value=0.0, format="%.6f", key=_k("lat"), help="เช่น 8.123456")
    lng = c2.number_input("ลองจิจูด", value=0.0, format="%.6f", key=_k("lng"), help="เช่น 98.123456")
    return lat, lng


# ---------------------------------------------------------
def _clean_crop_rows(edited: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for _, r in edited.iterrows():
        crop = r.get("ชนิดพืช")
        if _is_blank(crop):
            continue
        rows.append(
            {
                "crop_type": str(crop).strip(),
                "variety": (str(r.get("สายพันธุ์") or "").strip() or None),
                "area_rai": _safe_float(r.get("พื้นที่ (ไร่)")),
                "tree_count": _safe_int(r.get("จำนวนต้น")),
                "planted_year": _safe_int(r.get("ปีที่ปลูก (พ.ศ.)")),
            }
        )
    return rows


def _main_crop(rows: list[dict]) -> str:
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

    name = plot_name.strip()
    crop_rows = _clean_crop_rows(edited)

    if not name:
        st.warning("กรุณากรอกชื่อแปลง")
        return

    if not crop_rows:
        st.warning("กรุณาเลือกชนิดพืชอย่างน้อย 1 ชนิดในตารางพืช")
        return

    if deed["deed_type"] is None and not deed["deed_note"]:
        st.warning("แปลงที่ไม่มีเอกสารสิทธิ์ กรุณาระบุรายละเอียดการครอบครองด้วยครับ")
        return

    crop_area = sum(r["area_rai"] or 0 for r in crop_rows)

    if total_rai > 0 and crop_area > total_rai + 0.01:
        st.warning(
            f"พื้นที่พืชรวม {crop_area:,.2f} ไร่ มากกว่าเนื้อที่แปลง {total_rai:,.2f} ไร่ กรุณาตรวจสอบ"
        )
        return

    effective_area = total_rai if total_rai > 0 else crop_area

    payload = {
        "plot_name": name,
        "crop_type": _main_crop(crop_rows),
        "is_mixed": len(crop_rows) > 1,
        "area_rai": round(effective_area, 3) if effective_area > 0 else None,
        "rai": rai or None,
        "ngan": ngan or None,
        "wa": wa or None,
        "lat": lat or None,
        "lng": lng or None,
        **location,
        **deed,
    }

    created = insert_returning(TBL_PLOTS, payload)
    if not created:
        return

    crops_payload = [{**r, "plot_id": created["id"]} for r in crop_rows]
    if not insert_many(TBL_PLOT_CROPS, crops_payload):
        delete_silent(TBL_PLOTS, created["id"])   # ย้อนกลับ ไม่ให้เหลือแปลงค้าง
        st.error("บันทึกรายการพืชไม่สำเร็จ — ยกเลิกการบันทึกแปลงทั้งหมดแล้ว กรุณาลองใหม่")
        return


    st.session_state[VERSION_KEY] = st.session_state.get(VERSION_KEY, 0) + 1
    finish(f"บันทึกแปลง '{name}' พร้อมพืช {len(crop_rows)} ชนิด สำเร็จแล้ว!")

def _edit_form(plots_df: pd.DataFrame) -> None:
    st.markdown("##### เลือกแปลงที่ต้องการแก้ไข")

    if plots_df.empty:
        empty_state("ยังไม่มีแปลงให้แก้ไข")
        return

    selected_name = st.selectbox(
        "แปลง", plots_df["plot_name"], key="edit_select_plot"
    )
    plot = plots_df.loc[plots_df["plot_name"] == selected_name].iloc[0]
    plot_id = int(plot["id"])

    st.divider()

    # ---- ข้อมูลทั่วไป ----
    name = st.text_input("ชื่อแปลง *", value=str(plot.get("plot_name") or ""))

    c1, c2, c3 = st.columns(3)
    rai = c1.number_input("ไร่", min_value=0.0, step=1.0, value=float(plot.get("rai") or 0))
    ngan = c2.number_input("งาน", min_value=0.0, max_value=3.0, step=1.0, value=float(plot.get("ngan") or 0))
    wa = c3.number_input("ตารางวา", min_value=0.0, max_value=99.0, step=1.0, value=float(plot.get("wa") or 0))

    st.divider()

    # ---- พืชในแปลง ----
    st.markdown("##### 🌱 ชนิดพืชในแปลง")
    crops_df = fetch_table(TBL_PLOT_CROPS)
    current_crops = crops_df[crops_df["plot_id"] == plot_id] if not crops_df.empty else pd.DataFrame()

    if current_crops.empty:
        edit_table = EMPTY_CROPS.copy()
    else:
        edit_table = pd.DataFrame({
            "ชนิดพืช": current_crops["crop_type"].values,
            "สายพันธุ์": current_crops.get("variety", pd.Series(dtype=str)).fillna("").values,
            "พื้นที่ (ไร่)": current_crops.get("area_rai"),
            "จำนวนต้น": current_crops.get("tree_count"),
            "ปีที่ปลูก (พ.ศ.)": current_crops.get("planted_year"),
        })

    edited = st.data_editor(
        edit_table,
        key=f"edit_crop_editor_{plot_id}",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ชนิดพืช": st.column_config.SelectboxColumn(options=CROP_OPTIONS, width="medium"),
            "พื้นที่ (ไร่)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "จำนวนต้น": st.column_config.NumberColumn(min_value=0, step=1),
            "ปีที่ปลูก (พ.ศ.)": st.column_config.NumberColumn(min_value=2500, max_value=2600, step=1),
        },
    )

    st.divider()

    # ---- เอกสารสิทธิ์ / หมายเหตุ ----
    deed_note = st.text_area(
        "✍️ รายละเอียด / หมายเหตุการครอบครอง",
        value=str(plot.get("deed_note") or ""),
        height=100,
    )

    st.divider()
    col_save, col_delete = st.columns([3, 1])

    if col_save.button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True):
        crop_rows = _clean_crop_rows(edited)
        if not name.strip():
            st.warning("กรุณากรอกชื่อแปลง")
            return
        if not crop_rows:
            st.warning("กรุณามีชนิดพืชอย่างน้อย 1 ชนิด")
            return

        total_rai = rai + ngan / 4 + wa / 400
        crop_area = sum(r["area_rai"] or 0 for r in crop_rows)
        effective_area = total_rai if total_rai > 0 else crop_area

        update_row(
            TBL_PLOTS, plot_id,
            {
                "plot_name": name.strip(),
                "crop_type": crop_rows[0]["crop_type"],
                "is_mixed": len(crop_rows) > 1,
                "area_rai": round(effective_area, 3) if effective_area > 0 else None,
                "rai": rai or None, "ngan": ngan or None, "wa": wa or None,
                "deed_note": deed_note.strip() or None,
            },
            "",  # ยังไม่ finish ตรงนี้ รอทำ replace_crops ก่อน
        )
        crops_payload = [{**r, "plot_id": plot_id} for r in crop_rows]
        if replace_crops(plot_id, crops_payload):
            finish(f"แก้ไขแปลง '{name.strip()}' สำเร็จแล้ว!")

    if col_delete.button("🗑️ ลบแปลงนี้", use_container_width=True):
        st.session_state[f"confirm_delete_{plot_id}"] = True

    if st.session_state.get(f"confirm_delete_{plot_id}"):
        st.error(f"ยืนยันลบแปลง '{selected_name}' พร้อมข้อมูลพืชทั้งหมด? การลบนี้กู้คืนไม่ได้")
        cc1, cc2 = st.columns(2)
        if cc1.button("✅ ยืนยันลบ", type="primary"):
            delete_row(TBL_PLOTS, plot_id, f"ลบแปลง '{selected_name}' เรียบร้อยแล้ว")
        if cc2.button("❌ ยกเลิก"):
            st.session_state[f"confirm_delete_{plot_id}"] = False
            st.rerun()

# ---------------------------------------------------------
def render(plots_df: pd.DataFrame) -> None:
    st.header("🗂️ การจัดการแปลงเกษตรกรรม")
    tab_list, tab_add, tab_edit = st.tabs(
        ["รายชื่อแปลงทั้งหมด", "➕ เพิ่มแปลงใหม่", "✏️ แก้ไข/ลบแปลง"]
    )
    with tab_list:
        _plot_list(plots_df)
    with tab_add:
        _plot_form()
    with tab_edit:
        _edit_form(plots_df)


