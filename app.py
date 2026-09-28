"""ระบบบริหารจัดการสวนและผลผลิตเกษตรอัจฉริยะ (Streamlit + Supabase)."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.supabase_client import get_supabase_client

# =========================================================
# CONFIG & CONSTANTS
# =========================================================
st.set_page_config(
    page_title="ระบบบริหารจัดการสวนอัจฉริยะ",
    page_icon="🌴",
    layout="wide",
)

TX_INCOME = "รายรับ"
TX_EXPENSE = "รายจ่าย"

CROP_PALM = "ปาล์มน้ำมัน"
CROP_RUBBER = "ยางพารา"
FRUIT_CROPS = ("ทุเรียน", "ลองกอง", "มังคุด", "เงาะ")
CROP_OPTIONS = [CROP_PALM, CROP_RUBBER, *FRUIT_CROPS, "อื่นๆ"]

EXPENSE_CATEGORIES = [
    "ค่าปุ๋ยเคมี/อินทรีย์",
    "ค่ายาฆ่าหญ้า/สารกำจัดศัตรูพืช",
    "ค่าจ้างตัดหญ้า/กำจัดวัชพืช",
    "ค่าน้ำมันเชื้อเพลิง",
    "ค่าอุปกรณ์ซ่อมบำรุง",
    "อื่นๆ",
]

FRUIT_GRADES = ["เกรด AB (ส่งออก)", "เกรด C", "ตกเกรด/โบ๊ะ", "เหมาคละไซส์"]

TBL_PLOTS = "plots"
TBL_TX = "transactions"
TBL_FERT = "fertilizer_prices"
TBL_CONTRACTORS = "contractors"

MENU_DASHBOARD = "1. แดชบอร์ดภาพรวม"
MENU_PLOTS = "2. การจัดการแปลง"
MENU_FINANCE = "3. บัญชีรายรับ-รายจ่าย"
MENU_MAINTENANCE = "4. การบำรุงรักษา & ปัจจัยการผลิต"
MENU_MAP = "5. แผนที่แปลงเกษตร"

CACHE_TTL = 60  # วินาที

CUSTOM_CSS = """
<style>
    header {visibility: hidden;}
    .main {background-color: #f4f6f9;}

    .hero-banner {
        background: linear-gradient(135deg, #0e2a47 0%, #1a4a75 100%);
        border-radius: 12px; padding: 24px 30px; color: #fff;
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,.08);
    }
    .hero-title    {font-size: 24px; font-weight: 700; margin-bottom: 6px;}
    .hero-subtitle {font-size: 14px; color: #b0c4de;}

    .stat-card {
        background: #fff; border-radius: 12px; padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,.04); border: 1px solid #eef2f6;
        display: flex; align-items: center; gap: 15px; height: 100%;
    }
    .stat-icon {
        width: 48px; height: 48px; border-radius: 10px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .stat-label {font-size: 13px; color: #64748b; font-weight: 500;}
    .stat-value {font-size: 22px; font-weight: 700; color: #1e293b; margin-top: 2px;}

    .chart-header {font-size: 15px; font-weight: 700; color: #1e293b; margin-bottom: 12px;}
</style>
"""


# =========================================================
# DATA LAYER
# =========================================================
@st.cache_resource
def get_client():
    """สร้าง Supabase client ครั้งเดียวต่อ session."""
    return get_supabase_client()


@st.cache_data(ttl=CACHE_TTL, show_spinner="กำลังโหลดข้อมูล...")
def fetch_table(table: str) -> pd.DataFrame:
    """ดึงข้อมูลทั้งตารางแบบปลอดภัย — error แล้วคืน DataFrame ว่าง."""
    try:
        res = get_client().table(table).select("*").execute()
        return pd.DataFrame(res.data or [])
    except Exception as exc:  # noqa: BLE001
        st.error(f"โหลดข้อมูลตาราง `{table}` ไม่สำเร็จ: {exc}")
        return pd.DataFrame()


def insert_row(table: str, payload: dict[str, Any], success_msg: str) -> None:
    """บันทึกข้อมูล + ล้าง cache + แจ้งผลหลัง rerun."""
    try:
        get_client().table(table).insert(payload).execute()
    except Exception as exc:  # noqa: BLE001
        st.error(f"บันทึกไม่สำเร็จ: {exc}")
        return

    st.cache_data.clear()
    st.session_state["flash"] = success_msg
    st.rerun()


# =========================================================
# HELPERS
# =========================================================
def show_flash() -> None:
    """แสดงข้อความสำเร็จที่ค้างมาจาก rerun ก่อนหน้า."""
    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg, icon="✅")
        st.success(msg)


def has_cols(df: pd.DataFrame, cols: Iterable[str]) -> bool:
    return not df.empty and all(c in df.columns for c in cols)


def safe_sum(df: pd.DataFrame, col: str, mask: pd.Series | None = None) -> float:
    """รวมค่าคอลัมน์แบบไม่พังถ้าคอลัมน์ไม่มี/เป็น NaN."""
    if df.empty or col not in df.columns:
        return 0.0
    series = df[col] if mask is None else df.loc[mask, col]
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def kpi_card(container, icon: str, bg: str, fg: str, label: str, value: str) -> None:
    container.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-icon" style="background:{bg}; color:{fg};">{icon}</div>
            <div>
                <div class="stat-label">{label}</div>
                <div class="stat-value">{value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_box(title: str):
    """คืน container ที่มีกรอบจริง (แทน div ครอบที่ Streamlit ไม่รองรับ)."""
    box = st.container(border=True)
    box.markdown(f'<div class="chart-header">{title}</div>', unsafe_allow_html=True)
    return box


def compact_layout(fig, height: int = 230):
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=height)
    return fig


# =========================================================
# PAGE 1 — DASHBOARD
# =========================================================
def render_dashboard(plots_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-title">ระบบบริหารจัดการสวนและผลผลิตเกษตรอัจฉริยะ</div>
            <div class="hero-subtitle">ขับเคลื่อนการบริหารต้นทุน ปาล์มน้ำมัน ยางพารา ทุเรียน และไม้ผล อย่างแม่นยำ ครบวงจร</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tx_df = fetch_table(TBL_TX)

    is_income = tx_df["tx_type"] == TX_INCOME if "tx_type" in tx_df.columns else None
    is_expense = tx_df["tx_type"] == TX_EXPENSE if "tx_type" in tx_df.columns else None

    total_income = safe_sum(tx_df, "total_amount", is_income)
    total_expense = safe_sum(tx_df, "total_amount", is_expense)
    profit = total_income - total_expense
    total_yield = safe_sum(tx_df, "net_weight")

    total_plots = len(plots_df)
    total_area = safe_sum(plots_df, "area_rai")

    # ---- KPI ----
    cols = st.columns(5)
    kpi_card(cols[0], "💰", "#e0f2fe", "#0284c7", "รายรับรวมทั้งหมด", f"{total_income:,.0f} ฿")
    kpi_card(cols[1], "💸", "#fee2e2", "#dc2626", "รายจ่ายสะสม", f"{total_expense:,.0f} ฿")
    kpi_card(cols[2], "📈", "#dcfce7", "#16a34a", "กำไรสุทธิ", f"{profit:,.0f} ฿")
    kpi_card(cols[3], "⚖️", "#fef3c7", "#d97706", "ผลผลิตรวม (กก.)", f"{total_yield:,.0f}")
    kpi_card(cols[4], "🌴", "#ede9fe", "#7c3aed", "แปลงทั้งหมด", f"{total_plots} แปลง / {total_area:,.1f} ไร่")

    st.write("")

    # ---- CHARTS ----
    c1, c2, c3 = st.columns(3)

    with c1:
        box = chart_box("สัดส่วนรายรับ vs รายจ่าย")
        with box:
            if total_income > 0 or total_expense > 0:
                fig = px.pie(
                    values=[total_income, total_expense],
                    names=[TX_INCOME, TX_EXPENSE],
                    hole=0.6,
                    color=[TX_INCOME, TX_EXPENSE],
                    color_discrete_map={TX_INCOME: "#10b981", TX_EXPENSE: "#f43f5e"},
                )
                st.plotly_chart(compact_layout(fig), use_container_width=True)
            else:
                st.info("ไม่มีข้อมูลทางการเงิน")

    with c2:
        box = chart_box("สัดส่วนแปลงตามชนิดพืช")
        with box:
            if has_cols(plots_df, ["crop_type"]):
                crop_counts = (
                    plots_df["crop_type"].value_counts().rename_axis("crop_type")
                    .reset_index(name="count")
                )
                fig = px.bar(
                    crop_counts, x="count", y="crop_type",
                    orientation="h", color="crop_type", text="count",
                )
                compact_layout(fig).update_layout(
                    showlegend=False, yaxis_title="", xaxis_title="จำนวนแปลง"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลแปลง")

    with c3:
        box = chart_box("หมวดหมู่ค่าใช้จ่ายหลัก")
        with box:
            if has_cols(tx_df, ["tx_type", "category", "total_amount"]):
                exp_grp = (
                    tx_df[tx_df["tx_type"] == TX_EXPENSE]
                    .groupby("category", as_index=False)["total_amount"].sum()
                )
                if not exp_grp.empty:
                    fig = px.pie(exp_grp, values="total_amount", names="category", hole=0.4)
                    st.plotly_chart(compact_layout(fig), use_container_width=True)
                else:
                    st.info("ยังไม่มีรายการค่าใช้จ่าย")
            else:
                st.info("ยังไม่มีรายการ")

    # ---- LATEST TRANSACTIONS ----
    st.write("")
    box = chart_box("📋 รายการเดินบัญชีล่าสุด")
    with box:
        wanted = ["tx_date", "crop_type", "tx_type", "category",
                  "net_weight", "total_amount", "note"]
        available = [c for c in wanted if c in tx_df.columns]
        if not tx_df.empty and available:
            display_df = tx_df[available]
            if "tx_date" in available:
                display_df = display_df.sort_values("tx_date", ascending=False)
            st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการบันทึกรายการ")


# =========================================================
# PAGE 2 — PLOT MANAGEMENT
# =========================================================
def render_plot_management(plots_df: pd.DataFrame) -> None:
    st.header("🗂️ การจัดการแปลงเกษตรกรรม")
    tab_list, tab_add = st.tabs(["รายชื่อแปลงทั้งหมด", "➕ เพิ่มแปลงใหม่"])

    with tab_list:
        if plots_df.empty:
            st.info("ยังไม่มีข้อมูลแปลง")
        else:
            st.dataframe(plots_df, use_container_width=True, hide_index=True)

    with tab_add:
        with st.form("plot_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            plot_name = col_a.text_input("ชื่อแปลง *", placeholder="เช่น แปลงหน้าบ้าน, สวนเนินเขา")
            crop_type = col_b.selectbox("ชนิดพืชหลัก *", CROP_OPTIONS)
            variety = col_a.text_input("สายพันธุ์", placeholder="เช่น หมอนทอง, ชะนี, RRIM 600")
            area_rai = col_b.number_input("ขนาดพื้นที่ (ไร่)", min_value=0.0, step=0.5)

            col_lat, col_lng = st.columns(2)
            lat = col_lat.number_input("ละติจูด", value=0.0, format="%.6f", help="เช่น 8.123456")
            lng = col_lng.number_input("ลองจิจูด", value=0.0, format="%.6f", help="เช่น 99.123456")
            deed_no = st.text_input("เลขที่โฉนด / เอกสารสิทธิ์ (ถ้ามี)")

            if st.form_submit_button("💾 บันทึกข้อมูลแปลง", type="primary"):
                if not plot_name.strip():
                    st.warning("กรุณากรอกชื่อแปลง")
                elif area_rai <= 0:
                    st.warning("กรุณาระบุขนาดพื้นที่มากกว่า 0 ไร่")
                else:
                    insert_row(
                        TBL_PLOTS,
                        {
                            "plot_name": plot_name.strip(),
                            "crop_type": crop_type,
                            "variety": variety.strip() or None,   # ← เดิมหายไป
                            "area_rai": area_rai,
                            "lat": lat or None,                   # 0.0 = ยังไม่ระบุ
                            "lng": lng or None,
                            "deed_no": deed_no.strip() or None,
                        },
                        f"บันทึกแปลง '{plot_name.strip()}' สำเร็จแล้ว!",
                    )


# =========================================================
# PAGE 3 — FINANCE
# =========================================================
def _income_form_palm(plot_id: int, tx_date: date) -> None:
    st.subheader("🌴 ขายผลผลิตปาล์มน้ำมัน")
    mode = st.radio(
        "รูปแบบการคำนวณน้ำหนัก",
        ["ชั่งรถเข้า-ออก (อัตโนมัติ)", "ระบุน้ำหนักสุทธิ"],
        horizontal=True,
    )

    if mode.startswith("ชั่งรถ"):
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
                "plot_id": plot_id, "tx_date": str(tx_date), "crop_type": CROP_PALM,
                "tx_type": TX_INCOME, "category": "ขายปาล์ม",
                "weight_in": weight_in, "weight_out": weight_out,
                "net_weight": net_weight, "price_per_kg": price,
                "cutting_wage": wage, "fuel_cost": fuel, "total_amount": net_income,
            },
            "บันทึกรายการขายปาล์มสำเร็จ!",
        )


def _income_form_fruit(plot_id: int, tx_date: date, crop_type: str) -> None:
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
                "plot_id": plot_id, "tx_date": str(tx_date), "crop_type": crop_type,
                "tx_type": TX_INCOME, "category": f"ขาย{crop_type} ({grade})",
                "net_weight": weight, "price_per_kg": price,
                "cutting_wage": harvest_wage, "total_amount": net_amount,
            },
            f"บันทึกรายการขาย{crop_type}สำเร็จ!",
        )


def _income_form_rubber(plot_id: int, tx_date: date) -> None:
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
                "plot_id": plot_id, "tx_date": str(tx_date), "crop_type": CROP_RUBBER,
                "tx_type": TX_INCOME, "category": "ขายยาง",
                "net_weight": weight, "price_per_kg": price,
                "owner_share_pct": owner_share, "total_amount": owner_value,
            },
            "บันทึกรายการขายยางสำเร็จ!",
        )


def _expense_form(plot_id: int, tx_date: date, crop_type: str) -> None:
    st.markdown("---")
    st.subheader("🧾 บันทึกค่าใช้จ่ายแปลง (ปุ๋ย, ยา, ตัดหญ้า)")
    with st.form("expense_form", clear_on_submit=True):
        col_cat, col_amt = st.columns(2)
        category = col_cat.selectbox("หมวดหมู่ค่าใช้จ่าย", EXPENSE_CATEGORIES)
        amount = col_amt.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=50.0)
        expense_note = st.text_input("หมายเหตุ/ชื่อร้านค้า")

        if st.form_submit_button("บันทึกรายจ่าย"):
            if amount <= 0:
                st.warning("กรุณาระบุจำนวนเงินมากกว่า 0 บาท")
            else:
                insert_row(
                    TBL_TX,
                    {
                        "plot_id": plot_id, "tx_date": str(tx_date), "crop_type": crop_type,
                        "tx_type": TX_EXPENSE, "category": category,
                        "total_amount": amount, "note": expense_note.strip() or None,
                    },
                    "บันทึกรายจ่ายเรียบร้อย!",
                )


def render_finance(plots_df: pd.DataFrame) -> None:
    st.header("💰 บันทึกรายรับ-รายจ่าย")

    if not has_cols(plots_df, ["plot_name", "crop_type", "id"]):
        st.warning("กรุณาเพิ่มแปลงที่เมนู 'การจัดการแปลง' ก่อนทำการบันทึกข้อมูลครับ")
        st.stop()

    selected_name = st.selectbox("เลือกแปลงที่ต้องการบันทึก", plots_df["plot_name"])
    plot = plots_df.loc[plots_df["plot_name"] == selected_name].iloc[0]
    plot_id = int(plot["id"])
    crop_type = str(plot["crop_type"])
    tx_date = st.date_input("วันที่ทำรายการ", value=date.today())

    st.markdown(f"**พืชประจำแปลง:** `{crop_type}`")

    if crop_type == CROP_PALM:
        _income_form_palm(plot_id, tx_date)
    elif crop_type in FRUIT_CROPS:
        _income_form_fruit(plot_id, tx_date, crop_type)
    elif crop_type == CROP_RUBBER:
        _income_form_rubber(plot_id, tx_date)
    else:
        st.info("พืชชนิดนี้ยังไม่มีแบบฟอร์มรายรับเฉพาะ — บันทึกได้เฉพาะรายจ่ายด้านล่าง")

    _expense_form(plot_id, tx_date, crop_type)


# =========================================================
# PAGE 4 — MAINTENANCE & INPUTS
# =========================================================
def render_maintenance() -> None:
    st.header("🛠️ การบำรุงรักษา & ปัจจัยการผลิต")
    tab_fert, tab_contractor = st.tabs(["💰 บันทึกสืบราคาปุ๋ย", "👷 ทะเบียนผู้รับจ้าง/ช่าง"])

    with tab_fert:
        with st.form("fertilizer_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            shop = col1.text_input("ชื่อร้านค้า *")
            product = col2.text_input("สูตรปุ๋ย / ชื่อสินค้า *")
            price = col3.number_input("ราคาต่อกระสอบ/หน่วย (บาท)", min_value=0.0, step=10.0)

            if st.form_submit_button("บันทึกราคาปุ๋ย"):
                if not shop.strip() or not product.strip():
                    st.warning("กรุณากรอกชื่อร้านค้าและชื่อสินค้า")
                else:
                    insert_row(
                        TBL_FERT,
                        {
                            "shop_name": shop.strip(), "product_name": product.strip(),
                            "price": price, "checked_date": str(date.today()),
                        },
                        "บันทึกราคาปุ๋ยเรียบร้อย!",
                    )
        st.dataframe(fetch_table(TBL_FERT), use_container_width=True, hide_index=True)

    with tab_contractor:
        with st.form("contractor_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("ชื่อคนงาน / ผู้รับจ้าง *")
            phone = col2.text_input("เบอร์โทรศัพท์")
            skill = st.text_input("ความเชี่ยวชาญ", placeholder="เช่น กรีดยาง, ตัดหญ้า, ขุดหลุม")

            if st.form_submit_button("บันทึกผู้รับจ้าง"):
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
        st.dataframe(fetch_table(TBL_CONTRACTORS), use_container_width=True, hide_index=True)


# =========================================================
# PAGE 5 — MAP
# =========================================================
def render_map(plots_df: pd.DataFrame) -> None:
    st.header("📍 แผนที่แสดงพิกัดแปลงเกษตรกรรมทั้งหมด")
    st.markdown("ดูตำแหน่งแปลงที่ปักหมุดไว้ เพื่อวางแผนการเดินทางและการจัดการผลผลิต")

    if not has_cols(plots_df, ["lat", "lng"]):
        st.info("ยังไม่มีข้อมูลแปลง หรือยังไม่มีคอลัมน์พิกัด")
        return

    valid_plots = plots_df.dropna(subset=["lat", "lng"])
    valid_plots = valid_plots[(valid_plots["lat"] != 0) & (valid_plots["lng"] != 0)]

    if valid_plots.empty:
        st.info("ยังไม่มีแปลงที่ระบุพิกัด Latitude / Longitude — เพิ่มได้ที่เมนู 'การจัดการแปลง'")
        return

    st.map(
        valid_plots.rename(columns={"lat": "latitude", "lng": "longitude"}),
        zoom=12,
    )

    st.markdown("---")
    st.subheader("ตารางพิกัดแปลง")
    cols = [c for c in ["plot_name", "crop_type", "variety", "area_rai", "lat", "lng", "deed_no"]
            if c in valid_plots.columns]
    st.dataframe(valid_plots[cols], use_container_width=True, hide_index=True)


# =========================================================
# MAIN / ROUTER
# =========================================================
PAGES = {
    MENU_DASHBOARD: render_dashboard,
    MENU_PLOTS: render_plot_management,
    MENU_FINANCE: render_finance,
    MENU_MAINTENANCE: lambda _plots: render_maintenance(),
    MENU_MAP: render_map,
}


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    show_flash()

    st.sidebar.title("🌴 เมนูระบบงาน")
    menu = st.sidebar.radio("เลือกเมนู", list(PAGES.keys()))

    plots_df = fetch_table(TBL_PLOTS)
    PAGES[menu](plots_df)


if __name__ == "__main__":
    main()
