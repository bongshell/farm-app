"""สร้างการเชื่อมต่อไปยัง Supabase จากค่าใน secrets.toml"""

from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


def get_supabase_client() -> Client:
    """อ่าน URL/KEY จาก st.secrets แล้วคืน Supabase client."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError as exc:
        st.error(
            "ไม่พบค่า SUPABASE_URL / SUPABASE_KEY ใน .streamlit/secrets.toml "
            f"(ขาด: {exc})"
        )
        st.stop()

    return create_client(url, key)
