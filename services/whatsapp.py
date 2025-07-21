import json
import os
import urllib3

http = urllib3.PoolManager()
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]

def send_whatsapp_message(to_number, message_payload, is_interactive=False, reg_msg=None):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    if is_interactive:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            **message_payload
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message_payload}
        }
        if reg_msg is not None:
            payload["context"] = {"message_id": reg_msg}

    r = http.request("POST", url, headers=headers, body=json.dumps(payload).encode("utf-8"))
    print("Send result:", r.status, r.data.decode())


def send_whatsapp_message_with_button(to_number, message_text, button_id, button_title):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": message_text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": button_id,
                            "title": button_title
                        }
                    }
                ]
            }
        }
    }

    r = http.request("POST", url, headers=headers, body=json.dumps(payload).encode("utf-8"))
    print("Button send result:", r.status, r.data.decode())

def send_reaction(to_number, message_id, emoji):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "reaction",
        "reaction": {
            "message_id": message_id,
            "emoji": emoji
        }
    }

    r = http.request("POST", url, headers=headers, body=json.dumps(payload).encode("utf-8"))
    print("Reaction result:", r.status, r.data.decode())

def send_read_receipt(to_number, message_id):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    r = http.request("POST", url, headers=headers, body=json.dumps(payload).encode("utf-8"))

def download_media(media_id):
    # Step 1: Get the URL of the media using the media ID
    meta_url = f"https://graph.facebook.com/v19.0/{media_id}"
    meta_headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    meta_response = http.request("GET", meta_url, headers=meta_headers)
    if meta_response.status != 200:
        raise Exception(f"Failed to get media URL: {meta_response.status}")
    
    media_url = json.loads(meta_response.data.decode())["url"]

    # Step 2: Download the actual media file
    media_headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    media_response = http.request("GET", media_url, headers=media_headers)
    if media_response.status != 200:
        raise Exception(f"Failed to download media: {media_response.status}")

    return media_response.data  # returns bytes