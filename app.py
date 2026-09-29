"""ระบบบริหารจัดการสวนและผลผลิตเกษตรอัจฉริยะ — จุดเริ่มต้นของแอป"""

from __future__ import annotations

import streamlit as st

from components.ui import inject_css, show_flash
from config.constants import (
    MENU_DASHBOARD,
    MENU_FINANCE,
    MENU_MAINTENANCE,
    MENU_MAP,
    MENU_PLOTS,
    TBL_PLOTS,
)
from services.db import fetch_table
from views import dashboard, finance, maintenance, map_view, plots

st.set_page_config(
    page_title="ระบบบริหารจัดการสวนอัจฉริยะ",
    page_icon="🌴",
    layout="wide",
)

# ทุกหน้าใช้ signature เดียวกัน: render(plots_df)
PAGES = {
    MENU_DASHBOARD: dashboard.render,
    MENU_PLOTS: plots.render,
    MENU_FINANCE: finance.render,
    MENU_MAINTENANCE: maintenance.render,
    MENU_MAP: map_view.render,
}


def _sidebar() -> str:
    st.sidebar.title("🌴 เมนูระบบงาน")
    menu = st.sidebar.radio("เลือกเมนู", list(PAGES.keys()), label_visibility="collapsed")
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    return menu


def main() -> None:
    inject_css()
    show_flash()

    menu = _sidebar()
    plots_df = fetch_table(TBL_PLOTS)
    PAGES[menu](plots_df)


if __name__ == "__main__":
    main()
