# แจ้งเตือนงานประจำวันผ่าน LINE (พร้อมรูปภาพ)

สคริปต์นี้จะส่งข้อความ "งานที่ต้องทำวันนี้" พร้อมรูปภาพ ไปยัง LINE ของคุณโดยอัตโนมัติทุกวัน
โดยใช้ **LINE Messaging API** + **GitHub Actions** (รันฟรี ไม่ต้องมีเซิร์ฟเวอร์)

## ไฟล์ในโปรเจกต์

- `send_reminder.py` — สคริปต์หลักที่อ่านงานของวันนี้แล้วส่งเข้า LINE
- `tasks.json` — รายการงานของแต่ละวัน (แก้ไขได้ตามต้องการ)
- `.github/workflows/daily-reminder.yml` — ตั้งเวลาให้รันทุกวันอัตโนมัติ

## ขั้นตอนการติดตั้ง

### 1. หา LINE User ID ของตัวเอง
เนื่องจากคุณมี Channel Access Token อยู่แล้ว ขั้นต่อไปคือหา `userId` ที่จะรับข้อความ:

- วิธีง่ายที่สุด: เปิด **Webhook** ของ LINE OA ชั่วคราว แล้วส่งข้อความอะไรก็ได้หา LINE OA ของคุณ 1 ครั้ง
  จากนั้นดูใน webhook event ที่ได้รับ จะมีฟิลด์ `source.userId` — นี่คือ userId ของคุณ
- หรือใช้ LINE Official Account Manager > Settings > ดู "Your user ID" ถ้ามีแสดงในหน้าตั้งค่า

### 2. เตรียมรูปภาพ
LINE กำหนดว่ารูปที่ใช้ในข้อความประเภท image ต้อง:
- เป็น URL แบบ `https://` ที่เข้าถึงได้จากอินเทอร์เน็ตจริง (ไม่ใช่ localhost หรือไฟล์ในเครื่อง)
- เป็นไฟล์ JPEG ขนาดไม่เกิน 10MB

แนะนำให้อัปโหลดรูปไว้ที่ไหนสักที่ เช่น GitHub repo (ใช้ raw.githubusercontent.com), Imgur, หรือ storage อื่น ๆ แล้วนำ URL มาใส่ใน `tasks.json`

### 3. แก้ไข tasks.json
ใส่งานของแต่ละวันและ URL รูปภาพที่ต้องการแนบ:

```json
{
  "monday": {
    "text": "- ประชุมทีมตอน 9:00 น.\n- ส่งรายงานประจำสัปดาห์",
    "image_url": "https://raw.githubusercontent.com/<user>/<repo>/main/images/monday.jpg"
  }
}
```

### 4. อัปโหลดโค้ดขึ้น GitHub
สร้าง repository ใหม่ (ตั้งเป็น private ก็ได้) แล้ว push ไฟล์ทั้งหมดในโฟลเดอร์นี้ขึ้นไป

### 5. ตั้งค่า GitHub Secrets
ในหน้า repository ไปที่ **Settings > Secrets and variables > Actions > New repository secret** แล้วเพิ่ม:

| Name | Value |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | Channel access token ของ LINE OA |
| `LINE_USER_ID` | userId ที่ได้จากขั้นตอนที่ 1 |

### 6. ทดสอบรัน
ไปที่แท็บ **Actions** ในหน้า repo > เลือก workflow "Daily LINE Reminder" > กด **Run workflow** เพื่อทดสอบว่าได้รับข้อความใน LINE จริงหรือไม่

หลังจากทดสอบผ่านแล้ว ระบบจะรันอัตโนมัติทุกวันตามเวลาที่ตั้งไว้ใน `daily-reminder.yml`
(ค่าเริ่มต้นคือ 08:00 น. เวลาไทย — แก้ไขค่า `cron` ในไฟล์นั้นได้ตามต้องการ)

## การรันทดสอบในเครื่องตัวเอง (ก่อนอัปขึ้น GitHub)

```bash
pip install requests
export LINE_CHANNEL_ACCESS_TOKEN="your_token_here"
export LINE_USER_ID="your_user_id_here"
python send_reminder.py
```

หากสำเร็จ จะเห็นข้อความ `[OK] ส่งข้อความแจ้งเตือนสำเร็จ` และมีข้อความ+รูปภาพเด้งเข้า LINE
