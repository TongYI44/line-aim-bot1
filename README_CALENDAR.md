# ดึงงานจาก Google Calendar ส่งเข้า LINE ทุกวัน

ไฟล์ `calendar_reminder.py` จะดึงกิจกรรมของ "วันนี้" จาก Google Calendar โดยอัตโนมัติ
แล้วสร้างเป็นข้อความ + แนบรูปภาพ ส่งเข้า LINE (ใช้ workflow `daily-reminder-calendar.yml`)

## ขั้นตอนการตั้งค่า

### 1. สร้าง Google Service Account
Service Account คือ "บัญชีหุ่นยนต์" ที่ใช้ให้สคริปต์เข้าถึง Google Calendar โดยไม่ต้อง login ด้วยบัญชีจริงทุกครั้ง

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. สร้างโปรเจกต์ใหม่ (หรือใช้โปรเจกต์เดิม)
3. เปิดใช้งาน **Google Calendar API** ที่เมนู APIs & Services > Library
4. ไปที่ APIs & Services > Credentials > Create Credentials > **Service Account**
5. ตั้งชื่อ แล้วกด Done
6. เปิด Service Account ที่สร้าง > แท็บ Keys > Add Key > Create new key > เลือก **JSON**
   จะได้ไฟล์ credentials `.json` ดาวน์โหลดมา — เก็บไว้ให้ดี (ห้ามแชร์ต่อสาธารณะ)
7. เปิดไฟล์ JSON นั้น จะเห็นอีเมลของ service account อยู่ในฟิลด์ `client_email`
   เช่น `xxxx@your-project.iam.gserviceaccount.com`

### 2. แชร์ปฏิทินให้ Service Account อ่านได้
1. เปิด [Google Calendar](https://calendar.google.com/) ของคุณ
2. ไปที่ Settings ของปฏิทินที่ต้องการดึงข้อมูล (ปฏิทินหลักหรือปฏิทินอื่นที่สร้างไว้)
3. ที่หัวข้อ "Share with specific people" ให้เพิ่มอีเมลของ service account (จากขั้นตอนที่ 1)
   โดยให้สิทธิ์อย่างน้อย **"See all event details"**
4. คัดลอก **Calendar ID** จากหน้า Settings เดียวกัน (สำหรับปฏิทินหลักมักเป็นอีเมล Gmail ของคุณเอง)

### 3. ตั้งค่า GitHub Secrets เพิ่มเติม
นอกจาก `LINE_CHANNEL_ACCESS_TOKEN` และ `LINE_USER_ID` ที่มีอยู่แล้ว ให้เพิ่ม:

| Name | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | เนื้อหาทั้งหมดของไฟล์ credentials `.json` (copy-paste เป็น string) |
| `GOOGLE_CALENDAR_ID` | Calendar ID จากขั้นตอนที่ 2 |
| `REMINDER_IMAGE_URL` | (ไม่บังคับ) URL รูปภาพที่จะแนบไปกับข้อความทุกวัน |

> ถ้าไม่ตั้งค่า `REMINDER_IMAGE_URL` สคริปต์จะลองอ่านจาก `image_by_weekday.json` แทน
> (แก้ไข URL รูปในไฟล์นั้นให้เป็นรูปของคุณเอง)

### 4. ทดสอบรัน
ไปที่แท็บ **Actions** > เลือก workflow "Daily LINE Reminder (Google Calendar)" > กด **Run workflow**

ถ้าสำเร็จ จะมีข้อความสรุปกิจกรรมของวันนี้ (ดึงจาก Google Calendar จริง) พร้อมรูปภาพ เด้งเข้า LINE ทันที

## ทดสอบในเครื่องตัวเอง

```bash
pip install requests google-auth google-api-python-client

export LINE_CHANNEL_ACCESS_TOKEN="your_token_here"
export LINE_USER_ID="your_user_id_here"
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat credentials.json)"
export GOOGLE_CALENDAR_ID="your_email@gmail.com"
export REMINDER_IMAGE_URL="https://your-image-url.jpg"   # ไม่บังคับ

python calendar_reminder.py
```

## หมายเหตุ
- สคริปต์นี้ดึงเฉพาะกิจกรรมของ "วันนี้" (เที่ยงคืนถึงเที่ยงคืน ตามเวลาเครื่องที่รัน — บน GitHub Actions จะเป็น UTC
  แต่สคริปต์คำนวณจากเวลาปัจจุบันของเครื่องนั้น จึงควรตรวจสอบว่าผลลัพธ์ตรงกับวันที่ไทยที่ต้องการ)
- ถ้าอยากดึงจากหลายปฏิทินพร้อมกัน หรือกรองเฉพาะบาง keyword แจ้งได้ ปรับสคริปต์เพิ่มได้
