import streamlit as st
import pandas as pd
from datetime import date
from utils.supabase_client import get_supabase_client

st.set_page_config(page_title="ระบบจัดการสวน", page_icon="🌴", layout="wide")

supabase = get_supabase_client()

# ---------- เมนูนำทางหลัก ----------
st.sidebar.title("🌴 ระบบจัดการสวน")
menu = st.sidebar.radio(
    "เลือกเมนู",
    [
        "1. ภาพรวม (Overview)",
        "2. การจัดการแปลง",
        "3. บัญชีรายรับ-รายจ่าย",
        "4. การบำรุงรักษา & ปัจจัยการผลิต",
    ],
)


# =========================================================
# ดึงรายชื่อแปลงมาใช้ทั่วทั้งแอป
# =========================================================
@st.cache_data(ttl=60)
def get_plots():
    res = supabase.table("plots").select("*").execute()
    return pd.DataFrame(res.data)


plots_df = get_plots()


# =========================================================
# 1. ภาพรวม (Overview)
# =========================================================
if menu == "1. ภาพรวม (Overview)":
    st.header("📊 แดชบอร์ดภาพรวม")

    tx_res = supabase.table("transactions").select("*").execute()
    tx_df = pd.DataFrame(tx_res.data)

    if not tx_df.empty:
        total_income = tx_df.loc[tx_df["tx_type"] == "รายรับ", "total_amount"].sum()
        total_expense = tx_df.loc[tx_df["tx_type"] == "รายจ่าย", "total_amount"].sum()
        profit = total_income - total_expense

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("รายรับรวม", f"{total_income:,.2f} บาท")
        col2.metric("รายจ่ายรวม", f"{total_expense:,.2f} บาท")
        col3.metric("กำไร-ขาดทุน", f"{profit:,.2f} บาท")
        col4.metric("จำนวนแปลงทั้งหมด", f"{len(plots_df)} แปลง")

        st.subheader("รายการล่าสุด")
        st.dataframe(tx_df.sort_values("tx_date", ascending=False).head(20))
    else:
        st.info("ยังไม่มีข้อมูลรายรับ-รายจ่าย")

    st.subheader("📍 พิกัดแปลงบน Longdo Map")
    st.markdown(
        "ดูแผนที่แปลงทั้งหมดที่ [longdo](https://map.longdo.com/) "
        "(สามารถฝัง iframe แผนที่จริงได้ในเวอร์ชันถัดไป)"
    )
    if not plots_df.empty and "lat" in plots_df.columns:
        st.map(plots_df.rename(columns={"lat": "latitude", "lng": "longitude"}))


# =========================================================
# 2. การจัดการแปลง
# =========================================================
elif menu == "2. การจัดการแปลง":
    st.header("🗂️ การจัดการแปลง")
    tab1, tab2 = st.tabs(["รายชื่อแปลง", "เพิ่ม/แก้ไขแปลง"])

    with tab1:
        st.dataframe(plots_df)

    with tab2:
        with st.form("plot_form"):
            plot_name = st.text_input("ชื่อแปลง")
            crop_type = st.selectbox("ชนิดพืช", ["ปาล์มน้ำมัน", "ยางพารา", "อื่นๆ"])
            area_rai = st.number_input("ขนาด (ไร่)", min_value=0.0, step=0.1)
            lat = st.number_input("Latitude", format="%.6f")
            lng = st.number_input("Longitude", format="%.6f")
            deed_no = st.text_input("เลขที่เอกสารสิทธิ์")
            submitted = st.form_submit_button("บันทึกแปลง")

            if submitted:
                supabase.table("plots").insert(
                    {
                        "plot_name": plot_name,
                        "crop_type": crop_type,
                        "area_rai": area_rai,
                        "lat": lat,
                        "lng": lng,
                        "deed_no": deed_no,
                    }
                ).execute()
                st.success(f"บันทึกแปลง '{plot_name}' เรียบร้อยแล้ว")
                st.cache_data.clear()
                st.rerun()


# =========================================================
# 3. บัญชีรายรับ-รายจ่าย (จุดสำคัญ: ปาล์มน้ำมันแบบยืดหยุ่น)
# =========================================================
elif menu == "3. บัญชีรายรับ-รายจ่าย":
    st.header("💰 บันทึกรายรับ-รายจ่ายอัจฉริยะ")

    if plots_df.empty:
        st.warning("กรุณาเพิ่มแปลงในเมนู 'การจัดการแปลง' ก่อน")
        st.stop()

    plot_name_selected = st.selectbox("เลือกแปลง", plots_df["plot_name"])
    selected_plot = plots_df[plots_df["plot_name"] == plot_name_selected].iloc[0]
    plot_id = int(selected_plot["id"])
    crop_type = selected_plot["crop_type"]

    tx_date = st.date_input("วันที่ทำรายการ", value=date.today())

    # ---------------- ปาล์มน้ำมัน ----------------
    if crop_type == "ปาล์มน้ำมัน":
        st.subheader("🌴 บันทึกผลผลิตปาล์มน้ำมัน")

        mode = st.radio(
            "เลือกวิธีคำนวณน้ำหนัก",
            ["คำนวณจากน้ำหนักเข้า-ออก (อัตโนมัติ)", "กรอกน้ำหนักสุทธิเอง"],
            horizontal=True,
        )

        weight_in, weight_out, net_weight = None, None, 0.0

        if mode == "คำนวณจากน้ำหนักเข้า-ออก (อัตโนมัติ)":
            col1, col2 = st.columns(2)
            weight_in = col1.number_input("น้ำหนักขาเข้า (กก.)", min_value=0.0, step=1.0)
            weight_out = col2.number_input("น้ำหนักขาออก (กก.)", min_value=0.0, step=1.0)
            net_weight = max(weight_in - weight_out, 0.0)
            st.info(f"น้ำหนักสุทธิที่คำนวณได้: **{net_weight:,.2f} กก.**")
        else:
            net_weight = st.number_input("น้ำหนักสุทธิ (กก.)", min_value=0.0, step=1.0)

        price_per_kg = st.number_input("ราคาต่อกิโลกรัม (บาท)", min_value=0.0, step=0.1)
        cutting_wage = st.number_input("ค่าจ้างตัด (บาท) — คำนวณตามน้ำหนัก หรือกรอกเอง", min_value=0.0, step=1.0)
        fuel_cost = st.number_input("ค่าน้ำมัน (บาท)", min_value=0.0, step=1.0)
        other_cost = st.number_input("ค่าใช้จ่ายอื่นๆ (บาท)", min_value=0.0, step=1.0)

        gross_income = net_weight * price_per_kg
        total_deduction = cutting_wage + fuel_cost + other_cost
        net_income = gross_income - total_deduction

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("รายรับรวม (ก่อนหัก)", f"{gross_income:,.2f} บาท")
        col2.metric("หักค่าใช้จ่ายรวม", f"{total_deduction:,.2f} บาท")
        col3.metric("รายรับสุทธิ", f"{net_income:,.2f} บาท")

        note = st.text_area("หมายเหตุ")

        if st.button("💾 บันทึกรายการปาล์มน้ำมัน", type="primary"):
            supabase.table("transactions").insert(
                {
                    "plot_id": plot_id,
                    "tx_date": str(tx_date),
                    "crop_type": "ปาล์มน้ำมัน",
                    "tx_type": "รายรับ",
                    "category": "ขายปาล์ม",
                    "weight_in": weight_in,
                    "weight_out": weight_out,
                    "net_weight": net_weight,
                    "price_per_kg": price_per_kg,
                    "cutting_wage": cutting_wage,
                    "fuel_cost": fuel_cost,
                    "other_cost": other_cost,
                    "total_amount": net_income,
                    "note": note,
                }
            ).execute()
            st.success("บันทึกข้อมูลปาล์มน้ำมันเรียบร้อยแล้ว ✅")
            st.balloons()

    # ---------------- ยางพารา ----------------
    elif crop_type == "ยางพารา":
        st.subheader("🌳 บันทึกผลผลิตยางพารา")
        volume_kg = st.number_input("ปริมาณยาง (กก.)", min_value=0.0, step=1.0)
        price_per_kg = st.number_input("ราคาต่อกิโลกรัม (บาท)", min_value=0.0, step=0.1)
        owner_share = st.slider("ส่วนแบ่งเจ้าของ (%)", 0, 100, 60)

        total_amount = volume_kg * price_per_kg
        owner_income = total_amount * owner_share / 100
        cutter_income = total_amount - owner_income

        col1, col2, col3 = st.columns(3)
        col1.metric("รายรับรวม", f"{total_amount:,.2f} บาท")
        col2.metric(f"ส่วนเจ้าของ ({owner_share}%)", f"{owner_income:,.2f} บาท")
        col3.metric(f"ส่วนคนกรีด ({100-owner_share}%)", f"{cutter_income:,.2f} บาท")

        note = st.text_area("หมายเหตุ")

        if st.button("💾 บันทึกรายการยางพารา", type="primary"):
            supabase.table("transactions").insert(
                {
                    "plot_id": plot_id,
                    "tx_date": str(tx_date),
                    "crop_type": "ยางพารา",
                    "tx_type": "รายรับ",
                    "category": "ขายยาง",
                    "net_weight": volume_kg,
                    "price_per_kg": price_per_kg,
                    "total_amount": owner_income,
                    "note": note,
                }
            ).execute()
            st.success("บันทึกข้อมูลยางพาราเรียบร้อยแล้ว ✅")

    # ---------------- รายจ่ายทั่วไป ----------------
    st.markdown("---")
    st.subheader("🧾 บันทึกรายจ่ายทั่วไป")
    with st.form("expense_form"):
        exp_category = st.selectbox("หมวดหมู่", ["ค่าปุ๋ย", "ค่าจ้างตัดหญ้า", "ค่าอุปกรณ์", "อื่นๆ"])
        exp_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1.0)
        exp_note = st.text_area("หมายเหตุรายจ่าย")
        exp_submit = st.form_submit_button("บันทึกรายจ่าย")

        if exp_submit:
            supabase.table("transactions").insert(
                {
                    "plot_id": plot_id,
                    "tx_date": str(tx_date),
                    "crop_type": crop_type,
                    "tx_type": "รายจ่าย",
                    "category": exp_category,
                    "total_amount": exp_amount,
                    "note": exp_note,
                }
            ).execute()
            st.success("บันทึกรายจ่ายเรียบร้อยแล้ว ✅")

    # ---------------- สรุปกำไร-ขาดทุน ----------------
    st.markdown("---")
    st.subheader("📈 สรุปกำไร-ขาดทุน")
    tx_res = supabase.table("transactions").select("*").eq("plot_id", plot_id).execute()
    tx_df = pd.DataFrame(tx_res.data)
    if not tx_df.empty:
        summary = tx_df.groupby("tx_type")["total_amount"].sum()
        st.write(summary)
        st.dataframe(tx_df.sort_values("tx_date", ascending=False))


# =========================================================
# 4. การบำรุงรักษา & ปัจจัยการผลิต
# =========================================================
elif menu == "4. การบำรุงรักษา & ปัจจัยการผลิต":
    st.header("🛠️ การบำรุงรักษา & ปัจจัยการผลิต")
    tab1, tab2, tab3 = st.tabs(
        ["บันทึกการปฏิบัติงาน", "สืบราคาปุ๋ย", "ทะเบียนผู้รับจ้าง"]
    )

    with tab1:
        st.info("บันทึกการทำงานจริง เช่น ใส่ปุ๋ย ตัดหญ้า (เชื่อมกับต้นทุนในหน้ารายจ่าย)")

    with tab2:
        st.subheader("💰 สืบราคาและเปรียบเทียบปุ๋ย")
        with st.form("fert_form"):
            shop_name = st.text_input("ชื่อร้านค้า")
            product_name = st.text_input("ชื่อปุ๋ย/สินค้า")
            price = st.number_input("ราคา (บาท)", min_value=0.0, step=1.0)
            checked_date = st.date_input("วันที่สืบราคา", value=date.today())
            submitted = st.form_submit_button("บันทึกราคา")

            if submitted:
                supabase.table("fertilizer_prices").insert(
                    {
                        "shop_name": shop_name,
                        "product_name": product_name,
                        "price": price,
                        "checked_date": str(checked_date),
                    }
                ).execute()
                st.success("บันทึกราคาปุ๋ยเรียบร้อยแล้ว")

        fert_res = supabase.table("fertilizer_prices").select("*").execute()
        st.dataframe(pd.DataFrame(fert_res.data))

    with tab3:
        st.subheader("👷 ทะเบียนผู้รับจ้าง")
        with st.form("contractor_form"):
            c_name = st.text_input("ชื่อผู้รับจ้าง")
            c_phone = st.text_input("เบอร์โทร")
            c_note = st.text_area("หมายเหตุ")
            submitted = st.form_submit_button("บันทึกผู้รับจ้าง")

            if submitted:
                supabase.table("contractors").insert(
                    {"name": c_name, "phone": c_phone, "note": c_note}
                ).execute()
                st.success("บันทึกผู้รับจ้างเรียบร้อยแล้ว")

        c_res = supabase.table("contractors").select("*").execute()
        st.dataframe(pd.DataFrame(c_res.data))
