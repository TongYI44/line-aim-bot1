"""
ส่งข้อความแจ้งเตือน "งานประจำวัน" พร้อมรูปภาพ ไปยัง LINE
ผ่าน LINE Messaging API (push message)

การตั้งค่า:
1. ตั้งค่า environment variables (หรือ GitHub Secrets):
   - LINE_CHANNEL_ACCESS_TOKEN : Channel access token ของ LINE OA
   - LINE_USER_ID              : userId ของคนที่จะรับข้อความ (หรือ groupId)
2. แก้ไขไฟล์ tasks.json เพื่อกำหนดงาน + รูปภาพของแต่ละวัน
"""

import os
import sys
import json
import datetime
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

# วันในสัปดาห์ (ภาษาไทย) เรียงตาม datetime.weekday(): จันทร์=0 ... อาทิตย์=6
THAI_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def load_today_task(tasks_path: str) -> dict:
    """โหลดงานของวันนี้จาก tasks.json"""
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    today_key = THAI_WEEKDAYS[datetime.datetime.now().weekday()]
    today_task = tasks.get(today_key)

    if not today_task:
        raise ValueError(f"ไม่พบงานของวัน '{today_key}' ใน tasks.json")

    return today_task


def build_messages(task: dict) -> list:
    """สร้าง message payload: ข้อความ + รูปภาพ (ถ้ามี)"""
    today_str = datetime.datetime.now().strftime("%d/%m/%Y")
    text = f"📌 งานวันนี้ ({today_str})\n\n{task['text']}"

    messages = [{"type": "text", "text": text}]

    image_url = task.get("image_url")
    if image_url:
        messages.append(
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": task.get("preview_url", image_url),
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
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")

    if not access_token or not user_id:
        print(
            "[ERROR] กรุณาตั้งค่า LINE_CHANNEL_ACCESS_TOKEN และ LINE_USER_ID "
            "เป็น environment variable ก่อนรันสคริปต์นี้",
            file=sys.stderr,
        )
        sys.exit(1)

    tasks_path = os.path.join(os.path.dirname(__file__), "tasks.json")
    task = load_today_task(tasks_path)
    messages = build_messages(task)
    send_line_push(access_token, user_id, messages)


if __name__ == "__main__":
    main()
