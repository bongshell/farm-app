"""Data layer — ทุกการคุยกับฐานข้อมูลผ่านไฟล์นี้ไฟล์เดียว"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config.constants import CACHE_TTL
from utils.supabase_client import get_supabase_client


@st.cache_resource(show_spinner=False)
def get_client():
    """สร้าง client ครั้งเดียวแล้วใช้ซ้ำทั้ง session."""
    return get_supabase_client()


@st.cache_data(ttl=CACHE_TTL, show_spinner="กำลังโหลดข้อมูล...")
def fetch_table(table: str) -> pd.DataFrame:
    """ดึงข้อมูลทั้งตารางแบบปลอดภัย — ถ้า error คืน DataFrame ว่าง ไม่ทำให้แอปพัง."""
    try:
        res = get_client().table(table).select("*").execute()
        return pd.DataFrame(res.data or [])
    except Exception as exc:  # noqa: BLE001
        st.error(f"โหลดข้อมูลตาราง `{table}` ไม่สำเร็จ: {exc}")
        return pd.DataFrame()


def insert_row(table: str, payload: dict[str, Any], success_msg: str) -> None:
    """บันทึก 1 แถว + ล้าง cache + ฝากข้อความไว้แสดงหลัง rerun."""
    clean = {k: v for k, v in payload.items() if v is not None}

    try:
        get_client().table(table).insert(clean).execute()
    except Exception as exc:  # noqa: BLE001
        st.error(f"บันทึกไม่สำเร็จ: {exc}")
        return

    st.cache_data.clear()
    st.session_state["flash"] = success_msg
    st.rerun()


def delete_row(table: str, row_id: int, success_msg: str = "ลบข้อมูลเรียบร้อย") -> None:
    """ลบแถวตาม id (เตรียมไว้ใช้กับปุ่มลบในอนาคต)."""
    try:
        get_client().table(table).delete().eq("id", row_id).execute()
    except Exception as exc:  # noqa: BLE001
        st.error(f"ลบไม่สำเร็จ: {exc}")
        return

    st.cache_data.clear()
    st.session_state["flash"] = success_msg
    st.rerun()

def _clean(payload: dict[str, Any]) -> dict[str, Any]:
    """ตัดค่าว่างออกก่อนส่งเข้าฐานข้อมูล"""
    return {k: v for k, v in payload.items() if v not in (None, "")}


def insert_returning(table: str, payload: dict[str, Any]) -> dict | None:
    """บันทึก 1 แถวแล้วคืนแถวที่เพิ่งสร้าง (เพื่อเอา id ไปใช้ต่อ)"""
    try:
        res = get_client().table(table).insert(_clean(payload)).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        st.error(f"บันทึกตาราง `{table}` ไม่สำเร็จ: {exc}")
        return None


def insert_many(table: str, rows: list[dict[str, Any]]) -> bool:
    """บันทึกหลายแถวพร้อมกัน"""
    if not rows:
        return True
    try:
        get_client().table(table).insert([_clean(r) for r in rows]).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        st.error(f"บันทึกตาราง `{table}` ไม่สำเร็จ: {exc}")
        return False


def finish(success_msg: str, reset_keys: list[str] | None = None) -> None:
    for key in reset_keys or []:
        st.session_state.pop(key, None)
    st.cache_data.clear()
    st.session_state["flash"] = success_msg
    st.rerun()

