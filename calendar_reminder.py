"""
ดึงกิจกรรม/งานของ "วันนี้" จาก Google Calendar แล้วส่งแจ้งเตือนพร้อมรูปภาพ ไปยัง LINE
ผ่าน LINE Messaging API (push message)

การตั้งค่า (environment variables / GitHub Secrets):
  - LINE_CHANNEL_ACCESS_TOKEN : Channel access token ของ LINE OA
  - LINE_USER_ID              : userId ของคนที่จะรับข้อความ
  - GOOGLE_SERVICE_ACCOUNT_JSON : เนื้อหาไฟล์ credentials.json ของ Service Account (ทั้งไฟล์ เป็น string)
  - GOOGLE_CALENDAR_ID        : Calendar ID ที่จะดึงกิจกรรม (เช่น your_email@gmail.com หรือ id ของปฏิทินที่แชร์ไว้)
  - REMINDER_IMAGE_URL        : (ไม่บังคับ) URL รูปภาพที่จะแนบไปกับข้อความทุกวัน
                                ถ้าไม่ตั้งค่า จะดึงจาก image_by_weekday.json แทน (ถ้ามีไฟล์)
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
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
THAI_MONTHS=["","มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน","กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]



def now_in_bangkok() -> datetime.datetime:
    """เวลาปัจจุบัน อ้างอิงโซนเวลาไทยเสมอ ไม่ว่าเครื่องที่รันจะตั้งโซนเวลาอะไรก็ตาม
    (สำคัญเพราะ GitHub Actions runner ใช้ UTC เป็นค่าเริ่มต้น)"""
    return datetime.datetime.now(BANGKOK_TZ)


def get_today_range():
    """คืนค่าช่วงเวลาเริ่มต้น-สิ้นสุดของวันนี้ (เที่ยงคืนถึงเที่ยงคืน เวลาไทย) แบบ RFC3339"""
    now = now_in_bangkok()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1)
    return start_of_day.isoformat(), end_of_day.isoformat()


def fetch_todays_events(service_account_json: str, calendar_id: str) -> list:
    """ดึงกิจกรรมของวันนี้จาก Google Calendar"""
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


def format_event_line(event: dict) -> str:
    """แปลง event หนึ่งรายการเป็นข้อความ 1 บรรทัด
    ถ้ามีเวลาสิ้นสุด: '- 13:00-16:00 น. ประชุมทีม (ห้อง 302-303)'
    ถ้าไม่มีเวลาสิ้นสุด: '- 09:00 น. ประชุมทีม (ห้อง 302-303)'"""
    start = event.get("start", {})
    end = event.get("end", {})
    summary = event.get("summary", "(ไม่มีชื่อกิจกรรม)")
    location = event.get("location", "").strip()
    location_str = f" ({location})" if location else ""

    if "dateTime" in start:
        # กิจกรรมที่มีเวลาเริ่มต้น
        start_dt = datetime.datetime.fromisoformat(start["dateTime"])
        start_str = start_dt.strftime("%H:%M")

        end_str = None
        if "dateTime" in end:
            end_dt = datetime.datetime.fromisoformat(end["dateTime"])
            candidate = end_dt.strftime("%H:%M")
            if candidate != start_str:  # มีเวลาสิ้นสุดจริง ไม่ใช่ค่าเดียวกับเวลาเริ่ม
                end_str = candidate

        if end_str:
            time_str = f"{start_str}-{end_str}"
        else:
            time_str = start_str

        return f"- {time_str} น. {summary}{location_str}"
    else:
        # กิจกรรมแบบทั้งวัน (all-day event)
        return f"- (ทั้งวัน) {summary}{location_str}"


def build_task_text(events: list) -> str:
    now=now_in_bangkok()
    thai_date=f"{now.day} {THAI_MONTHS[now.month]} {now.year+543}"
    if not events:
        return f"📅 แจ้งเตือนตารางงาน

📆 วันที่ {thai_date}

ไม่มีตารางงานที่กำหนดไว้สำหรับวันนี้"
    msg=f"📅 แจ้งเตือนตารางงาน

📆 วันที่ {thai_date}

"
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
    """หา URL รูปภาพที่จะแนบ: จาก env var ก่อน แล้วค่อย fallback ไปที่ image_by_weekday.json"""
    fixed_url = os.environ.get("REMINDER_IMAGE_URL")
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
        messages.append(
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        )

    return messages


def send_line_push(access_token: str, to: str, messages: list) -> None:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    payload = {"to": to, "messages": messages}

    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)

    if resp.status_code != 200:
        print(f"[ERROR] LINE API ตอบกลับ {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    print("[OK] ส่งข้อความแจ้งเตือนสำเร็จ")


def main():
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("LINE_USER_ID", "").strip()
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "").strip()

    missing = [
        name
        for name, val in [
            ("LINE_CHANNEL_ACCESS_TOKEN", access_token),
            ("LINE_USER_ID", user_id),
            ("GOOGLE_SERVICE_ACCOUNT_JSON", service_account_json),
            ("GOOGLE_CALENDAR_ID", calendar_id),
        ]
        if not val
    ]
    if missing:
        print(f"[ERROR] ยังไม่ได้ตั้งค่า environment variable: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    events = fetch_todays_events(service_account_json, calendar_id)

    # DEBUG: พิมพ์ข้อมูลดิบของแต่ละ event เพื่อเช็คว่า Google Calendar ส่ง location มาจริงไหม
    for e in events:
        print(f"[DEBUG] summary={e.get('summary')!r} location={e.get('location')!r}", file=sys.stderr)

    task_text = build_task_text(events)
    messages = build_messages(task_text)
    send_line_push(access_token, user_id, messages)


if __name__ == "__main__":
    main()
