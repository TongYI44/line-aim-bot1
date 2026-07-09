# VERSION 5 - ULTIMATE CLEANING & DEBUG
"""
ดึงกิจกรรมจาก Google Calendar ส่งเข้า LINE
เวอร์ชันแก้ไขปัญหา InvalidHeader (ช่องว่างใน Token) แบบเด็ดขาด
"""

import os
import sys
import json
import datetime
import requests
import re
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- การตั้งค่าพื้นฐาน ---
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
THAI_MONTHS = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

def clean_secret(value):
    """ฟังก์ชันล้างค่าขยะใน Token แบบถอนรากถอนโคน"""
    if not value:
        return ""
    # 1. ตัดช่องว่าง หน้า-หลัง
    value = value.strip()
    # 2. ลบตัวอักษรควบคุม (Control Characters) เช่น \n, \r, \t ที่อาจแฝงมา
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    # 3. ลบช่องว่างที่อาจจะติดมาในตัว string (ถ้ามี)
    value = value.replace(" ", "")
    return value

def now_in_bangkok():
    return datetime.datetime.now(BANGKOK_TZ)

def fetch_todays_events(service_account_json, calendar_id):
    creds_info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("calendar", "v3", credentials=credentials)
    
    now = now_in_bangkok()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = (now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)).isoformat()
    
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return events_result.get("items", [])

def extract_room(event):
    """
    หาชื่อ 'ห้อง' ของกิจกรรม โดยลองตามลำดับนี้:
    1. ห้องที่ถูกจองผ่าน Google Calendar Rooms/Resources
       (ปรากฏใน attendees ที่มี resource: true)
    2. รูปแบบคำว่า 'ห้อง...' ที่ปรากฏใน location / summary / description
    """
    for attendee in event.get("attendees", []):
        if attendee.get("resource"):
            return attendee.get("displayName") or attendee.get("email", "-")

    text_fields = [
        event.get("location", ""),
        event.get("summary", ""),
        event.get("description", ""),
    ]
    room_pattern = re.compile(r"ห้อง\s*[\wก-๙\.\-/]+")
    for text in text_fields:
        if not text:
            continue
        match = room_pattern.search(text)
        if match:
            return match.group(0).strip()

    return "-"


def build_message(events):
    now = now_in_bangkok()
    thai_date = f"{now.day} {THAI_MONTHS[now.month]} {now.year + 543}"
    
    if not events:
        return f"📅 แจ้งเตือนตารางงาน\n\n📆 วันที่ {thai_date}\n\nไม่มีตารางงานสำหรับวันนี้"
    
    msg = f"📅 แจ้งเตือนตารางงาน\n\n📆 วันที่ {thai_date}\n\n"
    for event in events:
        summary = event.get("summary", "(ไม่มีชื่อกิจกรรม)")
        location = event.get("location", "-")
        room = extract_room(event)
        start = event.get("start", {})
        if "dateTime" in start:
            st = datetime.datetime.fromisoformat(start["dateTime"]).astimezone(BANGKOK_TZ)
            time_str = st.strftime('%H:%M น.')
        else:
            time_str = "ตลอดทั้งวัน"
        msg += (
            f"📌 กิจกรรม: {summary}\n"
            f"🚪 ห้อง: {room}\n"
            f"📍 สถานที่: {location}\n"
            f"🕒 เวลา: {time_str}\n\n"
        )
    return msg.strip()

def send_line(token, user_id, text):
    # ล้างค่าอีกครั้งก่อนส่งเพื่อความชัวร์
    token = clean_secret(token)
    user_id = clean_secret(user_id)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    
    # เพิ่มรูปภาพ (ถ้ามี)
    img_url = os.environ.get("REMINDER_IMAGE_URL", "").strip()
    if img_url:
        payload["messages"].append({
            "type": "image",
            "originalContentUrl": img_url,
            "previewImageUrl": img_url
        })

    print(f"[DEBUG] กำลังส่งข้อความ... (Token Length: {len(token)})")
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
    
    if resp.status_code != 200:
        print(f"[ERROR] LINE API ตอบกลับ {resp.status_code}: {resp.text}")
        sys.exit(1)
    print("[OK] ส่งข้อความสำเร็จ!")

def main():
    print("--- เริ่มทำงาน (VERSION 5) ---")
    
    # ดึงค่าและล้างทันที
    token = clean_secret(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""))
    user_id = clean_secret(os.environ.get("LINE_USER_ID", ""))
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    cal_id = os.environ.get("GOOGLE_CALENDAR_ID", "").strip()

    if not all([token, user_id, sa_json, cal_id]):
        print("[ERROR] ข้อมูล Environment Variables ไม่ครบ")
        sys.exit(1)

    try:
        events = fetch_todays_events(sa_json, cal_id)
        msg_text = build_message(events)
        send_line(token, user_id, msg_text)
    except Exception as e:
        print(f"[ERROR] เกิดข้อผิดพลาด: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
