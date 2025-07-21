import urllib
import os

WHATSAPP_PHONE_NUMBER = os.environ.get("WHATSAPP_PHONE_NUMBER")

def format_response(coupon_id, coupon_data, is_new, is_shared=False):    
    body_lines = []
    
    if coupon_data.get("coupon_code"):
        body_lines.append(f"🔖 *קוד קופון:* {coupon_data['coupon_code']}")
    if coupon_data.get("expiration_date"):
        body_lines.append(f"📅 *תוקף:* {coupon_data['expiration_date']}")
    if coupon_data.get("discount_value"):
        body_lines.append(f"💸 *הנחה:* {coupon_data['discount_value']}")
    if coupon_data.get("value"):
        body_lines.append(f"🎁 *ערך:* {coupon_data['value']}")
    if coupon_data.get("terms_and_conditions"):
        body_lines.append(f"📜 *תנאים:* {coupon_data['terms_and_conditions']}")
    if coupon_data.get("url"):
        body_lines.append(f"🔗 *URL:* {coupon_data['url']}")

    if coupon_data.get("store"):
        title = f"*קופון ל-{coupon_data['store']}*"
    else:
        title = "*פרטי הקופון:*"

    if is_shared:
        title += " 👥 "

    body_text = title + "\n\n" + "\n".join(body_lines)
    footer_text = (coupon_data.get("misc", "") or "")[:60]

    buttons = []

    # show cancel option only for new coupon
    if is_new:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"update_coupon_details:{coupon_id}",
                "title": "עדכן פרטים"
            }
        })
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"cancel_coupon:{coupon_id}",
                "title": "בטל קופון"
            }
        })
        # show sharing options only for new coupon 
        if not is_shared:
            if (coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."):
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"cancel_share:{coupon_id}",
                        "title": "בטל שיתוף"
                    }
                })                
            else:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"share_coupon:{coupon_id}",
                        "title": "שתף קופון"
                    }
                }) 
    else:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"update_coupon:{coupon_id}",
                "title": "עדכן קופון"
            }
        })
        # show mark as used option only for existing coupon   
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"mark_as_used:{coupon_data["client_id"]}:{coupon_id}",
                "title": "סמן כנוצל"
            }
        })
        if not is_shared:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"show_coupon:{coupon_id}",
                    "title": "הצג קופון מקורי"
                }
            })

    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "footer": {
                "text": footer_text
            } if footer_text else {},
            "action": {
                "buttons": buttons
            }
        }
    }

def format_share_coupon_interactive(coupon_data, sharing_token):
    # Generate WhatsApp deep link
    import_coupon_text = f"/add_shared_coupon {sharing_token}"
    import_coupon_text_encoded = urllib.parse.quote(import_coupon_text)
    import_couopn_deep_link = f"https://wa.me/{WHATSAPP_PHONE_NUMBER}?text={import_coupon_text_encoded}"

    parts = ["היי! 👋", "רציתי לשתף אותך בקופון שקיבלתי 💌"]

    if coupon_data.get('store') and coupon_data['store'] != None:
        parts.append(f"\n📍 הקופון מיועד ל־{coupon_data['store']}")
    
    if coupon_data.get('value') and coupon_data['value'] != None:
        parts.append(f"💸 שווי הקופון: {coupon_data['value']}")
    elif coupon_data.get("discount_value") and coupon_data["discount_value"] != None:
        parts.append(f"💸 {coupon_data['discount_value']} הנחה")

    parts.append(f"\nכדי להוסיף אותו לרשימת הקופונים שלך, פשוט לחץ על הקישור הבא👇\n{import_couopn_deep_link}")
    share_coupon_text = "\n".join(parts)
    share_coupon_text_encoded = urllib.parse.quote(share_coupon_text)
    share_coupon_deep_link = f'https://wa.me/?text={share_coupon_text_encoded}'

    return {
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {
                "text": "*👥 שיתוף קופון בודד*\n\nבחר איש קשר לשיתוף ואז לחץ על כפתור השליחה.\nאיש הקשר יקבל הודעה שבה יוכל להצטרף ולצפות בקופון ששותף"
            },
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "בחר איש קשר",
                    "url": share_coupon_deep_link
                }
            }
        }
    }

def format_share_list_interactive(my_number):
    # Generate WhatsApp deep link
    import_coupon_text = f"/share_list {my_number}"
    import_coupon_text_encoded = urllib.parse.quote(import_coupon_text)
    import_couopn_deep_link = f"https://wa.me/{WHATSAPP_PHONE_NUMBER}?text={import_coupon_text_encoded}"

    parts = ["היי! 👋", "בוא ננהל רשימת קופונים משותפת ביחד 💌"]    
    parts.append(f"\nכדי לשתף קופונים יחד, לחץ על הקישור👇\n{import_couopn_deep_link}")
    share_coupon_text = "\n".join(parts)
    share_coupon_text_encoded = urllib.parse.quote(share_coupon_text)
    share_coupon_deep_link = f'https://wa.me/?text={share_coupon_text_encoded}'

    share_message = (
        "*👥 שיתוף עם חבר*\n\n"
        "בחר חבר מרשימת אנשי הקשר שלך ולחץ על כפתור שליחת ההודעה.\n\n"
        "החבר יקבל ממני הודעה שמציעה להצטרף אליך לשיתוף קופונים קבוע.\n\n"
        "ברגע שהוא יאשר – כל קופון או שובר שתשמרו, יהיה גלוי גם לשני.\n"
        "כך תמיד תהיו מעודכנים, בלי להעביר ידנית כל קופון 😎"
    )
    return {
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {
                "text": share_message
            },
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "בחר איש קשר לשיתוף",
                    "url": share_coupon_deep_link
                }
            }
        }
    }

def format_coupons_list(coupons):
    if not coupons:
        return "לא נמצאו קופונים."

    lines = []
    for idx, coupon in enumerate(coupons, start=1):
        store = coupon.get("store", "חנות לא ידועה")
        code = coupon.get("coupon_code", "-")
        exp = coupon.get("expiration_date")
        
        line = f"*{idx}. {store}* — `{code}`"
        if exp:
            line += f" (בתוקף עד {exp})"

        lines.append(line)

    return "\n".join(lines)

def format_coupon_list_inline(coupons, shared_coupons):
    lines = []
    RTL = "\u200F"

    # my coupons
    if coupons:
        for i, coupon in enumerate(coupons, 1):
            store = coupon.get("store") or "חנות לא ידועה"
            code = coupon.get("coupon_code")
            exp = coupon.get("expiration_date")

            parts = [f"{RTL}{i}. 🏷️ {store}\n"]
            if code:
                parts.append(f"{RTL}🔢 קוד קופון: {code}\n")            

            if exp:
                parts.append(f"{RTL}⏳ תוקף: {exp}\n")

            line = "".join(parts)
            lines.append(line)

    # shared coupons
    if shared_coupons:
        if lines:
            lines.append("")  # שורה ריקה לפני הכותרת
        lines.append("👥 קופונים ששותפו איתי:\n")
        for i, coupon in enumerate(shared_coupons, 1):
            store = coupon.get("store") or "חנות לא ידועה"
            code = coupon.get("coupon_code")
            exp = coupon.get("expiration_date")

            parts = [f"{RTL}{i}. 🏷️ {store}\n"]
            if code:
                parts.append(f"{RTL}🔢 קוד קופון: {code}\n")            

            if exp:
                parts.append(f"{RTL}⏳ תוקף: {exp}\n")

            line = "".join(parts)
            lines.append(line)

    if not lines:
        return "לא נמצאו קופונים 😕"

    return "\n".join(lines)


def format_coupons_list_interactive(coupons, shared_coupons, title= "📋 רשימת הקופונים שלך:", footer = "בחר קופון כדי להציג או לבצע פעולה"):
    sections = [{
        "title": "הקופונים שלי",
        "rows": []
    }]
    
    for idx, coupon in enumerate(coupons, start=1):
        store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
        code = coupon.get("coupon_code", "-") or "(ללא קוד קופון)"
        exp = coupon.get("expiration_date")
        desc = f"{store} - {code} - בתוקף עד {exp}" if exp else "ללא תאריך תפוגה"
        
        sections[0]["rows"].append({
            "id": f"coupon:{coupon.get("client_id")}:{coupon.get("coupon_id")}",
            "title": f"{store}"[:24],
            "description": desc
        })
    
    if (len(shared_coupons) > 0):
        sections.append({
        "title": "קופונים ששותפו איתי",
        "rows": []})
        for idx, shared_coupons in enumerate(shared_coupons, start=1):
            store = shared_coupons.get("store", "חנות לא ידועה") or "חנות לא ידועה"
            code = shared_coupons.get("coupon_code", "-") or "(ללא קוד קופון)"
            exp = shared_coupons.get("expiration_date")
            desc = f"{store} - {code} - בתוקף עד {exp}" if exp else "ללא תאריך תפוגה"
            
            sections[1]["rows"].append({
                "id": f"coupon:{shared_coupons.get("client_id")}:{shared_coupons.get("coupon_id")}",
                "title": f"{store}"[:24],
                "description": desc
            })
    
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": title
            },
            "body": {
                "text": format_coupon_list_inline(coupons, shared_coupons)
            },
            "footer": {
                "text": footer
            },
            "action": {
                "button": "בחר קופון",
                "sections": sections
            }
        }
    }

def format_welcome_message(new_user=False):
    if new_user:
        welcome_text = "היי! 😊 כאן אפשר לשמור ולנהל קופונים או שוברים שקיבלת — מטקסט, תמונה או קובץ.\nאפשר גם לשתף קופונים עם מישהו קבוע, או רק לשתף שובר בודד. אני אזכיר לפני שפג התוקף ואשמור על הסדר עבורך."
    else:
        welcome_text = "היי שוב! 😊  \n\nכבר שמרת כמה קופונים — מעולה!\nרוצה לראות מה יש לך? או אולי לשתף מישהו מהקופונים?\n\nאפשר לבחור מהכפתורים כאן למטה, או פשוט לשלוח קופון חדש ואני אזהה אותו לבד ✨"
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": welcome_text
            },
            "footer": {
                "text": "בחר אפשרות כדי להתחיל"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "list_coupons",
                            "title": "📋 הצג קופונים שמורים"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "share_list",
                            "title": "👥 שיתוף רשימה עם חבר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "how_to_add",
                            "title": "➕ איך להוסיף קופון"
                        }
                    }
                ]
            }
        }
    }

def build_pairing_confirmation_message(phone_number: str) -> dict:
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": f"האם אתה מאשר שיתוף רשימת הקופונים עם מספר טלפון {phone_number}?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"confirm_pair:{phone_number}",
                            "title": "✅ מאשר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"decline_pair:{phone_number}",
                            "title": "❌ לא מאשר"
                        }
                    }
                ]
            }
        }
    }

def format_update_coupon_message(coupon_data):
    coupon_id = coupon_data.get("coupon_id")
    is_shared = coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."
    buttons = [{
        "type": "reply",
        "reply": {
            "id": f"update_coupon_details:{coupon_id}",
            "title": "עדכן פרטים"
            }
        },{
        "type": "reply",
        "reply": {
            "id": f"cancel_coupon:{coupon_id}",
            "title": "בטל קופון"
            }
        }]
    if not is_shared:
        if (coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."):
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"cancel_share:{coupon_id}",
                    "title": "בטל שיתוף"
                }
            })                
        else:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"share_coupon:{coupon_id}",
                    "title": "שתף קופון"
                }
            }) 

    store_name = coupon_data.get("store")
    if not store_name or not store_name.strip():
        store_name = "חנות לא ידועה"
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "בחר פעולה לביצוע עבור *קופון ל-" + store_name + "*"
            },
            "action": {
                "buttons": buttons
            }
        }
    }

def format_update_coupon_details_message(client_id, coupon_id, text="מה תרצה לעדכן? שלח הודעה בפורמט חופשי או לחץ ❌ לביטול"):
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"cancel_update_coupon:{client_id}:{coupon_id}",
                            "title": "❌ ביטול"
                        }
                    }
                ]
            }
        }
    }
