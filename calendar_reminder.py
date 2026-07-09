"""
ดึงกิจกรรม/งานของ "วันนี้" จาก Google Calendar แล้วส่งแจ้งเตือนพร้อมรูปภาพ ไปยัง LINE
ผ่าน LINE Messaging API (push message)
"""

from __future__ import annotations

import os
import sys
import json
import datetime
import requests
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

THAI_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
BANGKOK_TZ = ZoneInfo("Asia/Bangkok" )
THAI_MONTHS = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

def now_in_bangkok() -> datetime.datetime:
    return datetime.datetime.now(BANGKOK_TZ)

def get_today_range():
    now = now_in_bangkok()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1)
    return start_of_day.isoformat(), end_of_day.isoformat()

def fetch_todays_events(service_account_json: str, calendar_id: str) -> list:
    creds_info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("calendar", "v3", credentials=credentials)
    time_min, time_max = get_today_range()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return events_result.get("items", [])

def build_task_text(events: list) -> str:
    now = now_in_bangkok()
    thai_date = f"{now.day} {THAI_MONTHS[now.month]} {now.year + 543}"
    if not events:
        return f"📅 แจ้งเตือนตารางงาน\n\n📆 วันที่ {thai_date}\n\nไม่มีตารางงานที่กำหนดไว้สำหรับวันนี้"
    
    msg = f"📅 แจ้งเตือนตารางงาน\n\n📆 วันที่ {thai_date}\n\n"
    for event in events:
        summary = event.get("summary", "(ไม่มีชื่อกิจกรรม)")
        location = event.get("location", "-")
        if "dateTime" in event["start"]:
            st = datetime.datetime.fromisoformat(event["start"]["dateTime"]).astimezone(BANGKOK_TZ)
            en = datetime.datetime.fromisoformat(event["end"]["dateTime"]).astimezone(BANGKOK_TZ)
            time_str = f"{st.strftime('%H:%M')} - {en.strftime('%H:%M')} น."
        else:
            time_str = "ตลอดทั้งวัน"
        msg += f"📌 กิจกรรม: {summary}\n📍 สถานที่: {location}\n🕒 เวลา: {time_str}\n\n"
    return msg.strip()

def get_image_url() -> str | None:
    fixed_url = os.environ.get("REMINDER_IMAGE_URL", "").strip()
    if fixed_url:
        return fixed_url
    image_map_path = os.path.join(os.path.dirname(__file__), "image_by_weekday.json")
    if os.path.exists(image_map_path):
        with open(image_map_path, "r", encoding="utf-8") as f:
            image_map = json.load(f)
        today_key = THAI_WEEKDAYS[now_in_bangkok().weekday()]
        return image_map.get(today_key)
    return None

def build_messages(task_text: str) -> list:
    messages = [{"type": "text", "text": task_text}]
    image_url = get_image_url()
    if image_url:
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url,
        })
    return messages

def send_line_push(access_token: str, to: str, messages: list) -> None:
    # ล้างค่าช่องว่างหรือตัวอักษรแปลกปลอมใน Token และ ID อีกครั้งก่อนส่ง
    clean_token = access_token.strip()
    clean_to = to.strip()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {clean_token}",
    }
    payload = {"to": clean_to, "messages": messages}
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        print(f"[ERROR] LINE API ตอบกลับ {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("[OK] ส่งข้อความแจ้งเตือนสำเร็จ")

def main():
    # ดึงค่าและทำความสะอาดข้อมูลทันที
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("LINE_USER_ID", "").strip()
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "").strip()

    if not all([access_token, user_id, service_account_json, calendar_id]):
        print(f"[ERROR] ตั้งค่า Environment Variables ไม่ครบถ้วน", file=sys.stderr)
        sys.exit(1)

    events = fetch_todays_events(service_account_json, calendar_id)
    task_text = build_task_text(events)
    messages = build_messages(task_text)
    send_line_push(access_token, user_id, messages)

if __name__ == "__main__":
    main()
