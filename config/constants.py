"""ค่าคงที่ทั้งหมดของระบบ — แก้ที่เดียว มีผลทั้งแอป"""

from __future__ import annotations

# ---------- ประเภทรายการ ----------
TX_INCOME = "รายรับ"
TX_EXPENSE = "รายจ่าย"

# ---------- ชนิดพืช ----------
CROP_PALM = "ปาล์มน้ำมัน"
CROP_RUBBER = "ยางพารา"
FRUIT_CROPS: tuple[str, ...] = ("ทุเรียน", "ลองกอง", "มังคุด", "เงาะ")
CROP_OPTIONS: list[str] = [CROP_PALM, CROP_RUBBER, *FRUIT_CROPS, "อื่นๆ"]

# ---------- ตัวเลือกในฟอร์ม ----------
FRUIT_GRADES: list[str] = [
    "เกรด AB (ส่งออก)",
    "เกรด C",
    "ตกเกรด/โบ๊ะ",
    "เหมาคละไซส์",
]

EXPENSE_CATEGORIES: list[str] = [
    "ค่าปุ๋ยเคมี/อินทรีย์",
    "ค่ายาฆ่าหญ้า/สารกำจัดศัตรูพืช",
    "ค่าจ้างตัดหญ้า/กำจัดวัชพืช",
    "ค่าน้ำมันเชื้อเพลิง",
    "ค่าอุปกรณ์ซ่อมบำรุง",
    "อื่นๆ",
]

# ---------- ชื่อตารางใน Supabase ----------
TBL_PLOTS = "plots"
TBL_TX = "transactions"
TBL_FERT = "fertilizer_prices"
TBL_CONTRACTORS = "contractors"

# ---------- เมนู ----------
MENU_DASHBOARD = "1. แดชบอร์ดภาพรวม"
MENU_PLOTS = "2. การจัดการแปลง"
MENU_FINANCE = "3. บัญชีรายรับ-รายจ่าย"
MENU_MAINTENANCE = "4. การบำรุงรักษา & ปัจจัยการผลิต"
MENU_MAP = "5. แผนที่แปลงเกษตร"

# ---------- ตั้งค่าทั่วไป ----------
CACHE_TTL = 60          # วินาที
RECENT_TX_LIMIT = 10    # จำนวนรายการล่าสุดบนแดชบอร์ด
CHART_HEIGHT = 230      # px
MAP_ZOOM = 12

# ---------- สี ----------
COLOR_INCOME = "#10b981"
COLOR_EXPENSE = "#f43f5e"
