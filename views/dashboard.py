"""หน้า 1 — แดชบอร์ดภาพรวม"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.ui import (
    HERO_BANNER,
    chart_box,
    compact_layout,
    empty_state,
    has_cols,
    kpi_card,
    safe_sum,
)
from config.constants import (
    COLOR_EXPENSE,
    COLOR_INCOME,
    RECENT_TX_LIMIT,
    TBL_TX,
    TX_EXPENSE,
    TX_INCOME,
)
from services.db import fetch_table

TX_DISPLAY_COLS = [
    "tx_date", "crop_type", "tx_type", "category",
    "net_weight", "total_amount", "note",
]


def _render_kpis(
    income: float, expense: float, profit: float,
    yield_kg: float, plot_count: int, area: float,
) -> None:
    cols = st.columns(5)
    kpi_card(cols[0], "💰", "#e0f2fe", "#0284c7", "รายรับรวมทั้งหมด", f"{income:,.0f} ฿")
    kpi_card(cols[1], "💸", "#fee2e2", "#dc2626", "รายจ่ายสะสม", f"{expense:,.0f} ฿")
    kpi_card(cols[2], "📈", "#dcfce7", "#16a34a", "กำไรสุทธิ", f"{profit:,.0f} ฿")
    kpi_card(cols[3], "⚖️", "#fef3c7", "#d97706", "ผลผลิตรวม (กก.)", f"{yield_kg:,.0f}")
    kpi_card(cols[4], "🌴", "#ede9fe", "#7c3aed", "แปลงทั้งหมด", f"{plot_count} แปลง / {area:,.1f} ไร่")


def _chart_income_expense(income: float, expense: float) -> None:
    with chart_box("สัดส่วนรายรับ vs รายจ่าย"):
        if income <= 0 and expense <= 0:
            empty_state("ไม่มีข้อมูลทางการเงิน")
            return
        fig = px.pie(
            values=[income, expense],
            names=[TX_INCOME, TX_EXPENSE],
            hole=0.6,
            color=[TX_INCOME, TX_EXPENSE],
            color_discrete_map={TX_INCOME: COLOR_INCOME, TX_EXPENSE: COLOR_EXPENSE},
        )
        st.plotly_chart(compact_layout(fig), use_container_width=True)


def _chart_crop_mix(plots_df: pd.DataFrame) -> None:
    with chart_box("สัดส่วนแปลงตามชนิดพืช"):
        if not has_cols(plots_df, ["crop_type"]):
            empty_state("ยังไม่มีข้อมูลแปลง")
            return
        counts = (
            plots_df["crop_type"]
            .value_counts()
            .rename_axis("crop_type")
            .reset_index(name="count")
        )
        fig = px.bar(
            counts, x="count", y="crop_type",
            orientation="h", color="crop_type", text="count",
        )
        compact_layout(fig).update_layout(
            showlegend=False, yaxis_title="", xaxis_title="จำนวนแปลง"
        )
        st.plotly_chart(fig, use_container_width=True)


def _chart_expense_breakdown(tx_df: pd.DataFrame) -> None:
    with chart_box("หมวดหมู่ค่าใช้จ่ายหลัก"):
        if not has_cols(tx_df, ["tx_type", "category", "total_amount"]):
            empty_state("ยังไม่มีรายการ")
            return
        grouped = (
            tx_df[tx_df["tx_type"] == TX_EXPENSE]
            .groupby("category", as_index=False)["total_amount"]
            .sum()
        )
        if grouped.empty:
            empty_state("ยังไม่มีรายการค่าใช้จ่าย")
            return
        fig = px.pie(grouped, values="total_amount", names="category", hole=0.4)
        st.plotly_chart(compact_layout(fig), use_container_width=True)


def _recent_transactions(tx_df: pd.DataFrame) -> None:
    with chart_box("📋 รายการเดินบัญชีล่าสุด"):
        available = [c for c in TX_DISPLAY_COLS if c in tx_df.columns]
        if tx_df.empty or not available:
            empty_state("ยังไม่มีประวัติการบันทึกรายการ")
            return
        view = tx_df[available]
        if "tx_date" in available:
            view = view.sort_values("tx_date", ascending=False)
        st.dataframe(
            view.head(RECENT_TX_LIMIT),
            use_container_width=True,
            hide_index=True,
        )


def render(plots_df: pd.DataFrame) -> None:
    st.markdown(HERO_BANNER, unsafe_allow_html=True)

    tx_df = fetch_table(TBL_TX)
    has_type = "tx_type" in tx_df.columns

    income = safe_sum(tx_df, "total_amount", tx_df["tx_type"] == TX_INCOME if has_type else None)
    expense = safe_sum(tx_df, "total_amount", tx_df["tx_type"] == TX_EXPENSE if has_type else None)

    _render_kpis(
        income=income,
        expense=expense,
        profit=income - expense,
        yield_kg=safe_sum(tx_df, "net_weight"),
        plot_count=len(plots_df),
        area=safe_sum(plots_df, "area_rai"),
    )

    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1:
        _chart_income_expense(income, expense)
    with c2:
        _chart_crop_mix(plots_df)
    with c3:
        _chart_expense_breakdown(tx_df)

    st.write("")
    _recent_transactions(tx_df)
