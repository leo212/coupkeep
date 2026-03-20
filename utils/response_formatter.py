import urllib.parse
import config
from datetime import datetime

def get_category_name(category):
    """Get the full name of a category based on its short name."""
    categories = {
        "food_and_drinks": "מזון ושתייה",
        "clothing_and_fashion": "ביגוד ואופנה",
        "electronics": "אלקטרוניקה",
        "beauty_and_health": "יופי ובריאות",
        "home_and_garden": "בית וגן",
        "travel": "נסיעות ונופש",
        "entertainment": "בידור",
        "kids_and_babies": "ילדים ותינוקות",
        "sports_and_outdoors": "ספורט וטיולים",
        "other": "אחר"
    }
    return categories.get(category, category)

def get_category_emoji(category):
    if not category:
        return ""
    
    """Get the emoji associated with a category."""
    emojis = {
        "food_and_drinks": "🍔",
        "clothing_and_fashion": "👗",
        "electronics": "📱",
        "beauty_and_health": "💄",
        "home_and_garden": "🏡",
        "travel": "✈️",
        "entertainment": "🎬",
        "kids_and_babies": "👶",
        "sports_and_outdoors": "⚽",
        "other": ""
    }
    return emojis.get(category, "")

def format_response(coupon_id, coupon_data, is_new, is_shared=False):
    """Format a response with coupon details for WhatsApp."""
    body_lines = []
    
    if coupon_data.get("coupon_code"):
        body_lines.append(f"🔖 *קוד קופון:* {coupon_data['coupon_code']}")
    if coupon_data.get("expiration_date"):
        body_lines.append(f"📅 *תוקף:* {coupon_data['expiration_date']}")
    if coupon_data.get("discount_value"):
        body_lines.append(f"💸 *הנחה:* {coupon_data['discount_value']}")
    if coupon_data.get("value"):
        body_lines.append(f"🎁 *ערך:* {coupon_data['value']}")
    if coupon_data.get("terms"):
        body_lines.append(f"📜 *תנאים:* {coupon_data['terms']}")
    if coupon_data.get("url"):
        body_lines.append(f"🔗 *URL:* {coupon_data['url']}")
    if coupon_data.get("misc"):
        body_lines.append(f"*מידע נוסף:* {coupon_data['misc']}")
    if coupon_data.get("category"):
        category_name = get_category_name(coupon_data["category"])
    else:
        category_name = None

    if coupon_data.get("store"):
        title = f"*קופון ל-{coupon_data['store']}*"
    else:
        title = f"*פרטי הקופון:*"
    
    if category_name:
        title += f" | {get_category_emoji(coupon_data['category'])} {category_name}"
    
    if is_shared:
        title += " 👥 "

    body_text = title + "\n\n" + "\n".join(body_lines)
    if coupon_data.get("expiration_date"):
        now = datetime.now()
        exp_date_str = coupon_data["expiration_date"]
        # Handle both date-only and datetime formats
        if 'T' in exp_date_str:
            expiration_date = datetime.fromisoformat(exp_date_str.split('.')[0])  # Remove microseconds if present
        else:
            expiration_date = datetime.strptime(exp_date_str, "%Y-%m-%d")
        remaining_days_for_expiration = (expiration_date - now).days
        if remaining_days_for_expiration < 0:
            footer_text = "קופון פג תוקף"
        else:
            footer_text = "נותרו " + str(remaining_days_for_expiration) + " ימים לניצול הקופון"
    else:
        footer_text = "ללא תאריך תפוגה"
 
    buttons = []

    # show cancel option only for new coupon
    if is_new:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{config.BUTTON_UPDATE_COUPON_DETAILS_PREFIX}{coupon_id}",
                "title": "📝 עדכן פרטים"
            }
        })
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{config.BUTTON_CANCEL_COUPON_PREFIX}{coupon_id}",
                "title": "🗑️ מחק קופון"
            }
        })
        # show sharing options only for new coupon 
        if not is_shared:
            if (coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."):
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"{config.BUTTON_CANCEL_SHARE_PREFIX}{coupon_id}",
                        "title": "🤝 בטל שיתוף"
                    }
                })                
            else:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"{config.BUTTON_SHARE_COUPON_PREFIX}{coupon_id}",
                        "title": "🤝 שתף קופון"
                    }
                })
    else:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{config.BUTTON_UPDATE_COUPON_DETAILS_PREFIX}{coupon_id}",
                "title": "📝 עדכן פרטים"
            }
        })
        # show mark as used option only for existing coupon   
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{config.BUTTON_MARK_AS_USED_PREFIX}{coupon_data['client_id']}:{coupon_id}",
                "title": "✅ סמן כנוצל"
            }
        })
        if not is_shared:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"show_coupon:{coupon_id}",
                    "title": "👁️ הצג קופון מקורי"
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
            },
            "action": {
                "buttons": buttons
            }
        }
    }

def format_share_coupon_interactive(coupon_data, sharing_token):
    """Format an interactive message for sharing a coupon."""
    # Generate WhatsApp deep link
    import_coupon_text = f"/add_shared_coupon {sharing_token}"
    import_coupon_text_encoded = urllib.parse.quote(import_coupon_text)
    import_couopn_deep_link = f"https://wa.me/{config.WHATSAPP_PHONE_NUMBER}?text={import_coupon_text_encoded}"

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
    """Format an interactive message for sharing a coupon list."""
    # Generate WhatsApp deep link
    import_coupon_text = f"/share_list {my_number}"
    import_coupon_text_encoded = urllib.parse.quote(import_coupon_text)
    import_couopn_deep_link = f"https://wa.me/{config.WHATSAPP_PHONE_NUMBER}?text={import_coupon_text_encoded}"

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
    """Format a simple text list of coupons."""
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
    """Format an inline list of coupons for display in a message body."""
    lines = []
    RTL = "\u200F"

    # merge coupons and shared coupons list
    for coupon in shared_coupons:
        coupon["is_shared"] = True
    
    all_coupons = coupons + shared_coupons

    # organize coupons by category
    categories = {}
    for coupon in all_coupons:
        category = coupon.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append(coupon)

    for category, coupons in categories.items():
        if coupons:
            category_name = get_category_name(category)
            category_emoji = get_category_emoji(category)
            lines.append(f"{category_emoji} *{category_name}*")
            for coupon in coupons:
                store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
                value = coupon.get("value") or coupon.get("discount_value") or ""
                line = f"- {RTL}{store}" + (f" - {value}" if value else "")
                lines.append(line)    
            lines.append("")  # Add a blank line after each category

    if not lines:
        return "לא נמצאו קופונים 😕"

    return "\n".join(lines)

def format_coupons_list_interactive(coupons, shared_coupons, title="📋 רשימת הקופונים שלך:", footer="בחר קופון כדי להציג או לבצע פעולה"):
    max_coupons = 10

    """Format an interactive list of coupons with buttons."""
    sections = [{
        "title": "הקופונים שלי",
        "rows": []
    }]
    
    for idx, coupon in enumerate(coupons[:max_coupons], start=1):
        store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
        code = coupon.get("coupon_code", "-") or "(ללא קוד)"
        value = coupon.get("value") or coupon.get("discount_value") or ""
        desc = (f"{value} - " if value else "") + f"קוד: {code}"
        
        sections[0]["rows"].append({
            "id": f"{config.BUTTON_COUPON_PREFIX}{coupon.get('client_id')}:{coupon.get('coupon_id')}",
            "title": f"{store}"[:24],
            "description": desc
        })
    
    if len(shared_coupons) > 0 and len(sections[0]["rows"]) < max_coupons:
        sections.append({
        "title": "קופונים ששותפו איתי",
        "rows": []})
        for idx, shared_coupon in enumerate(shared_coupons[:max_coupons - len(sections[0]["rows"])], start=1):
            store = shared_coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
            code = shared_coupon.get("coupon_code", "-") or "(ללא קוד)"
            value = shared_coupon.get("value") or shared_coupon.get("discount_value") or ""
            desc = (f"{value} - " if value else "") + f"קוד: {code}"

            sections[1]["rows"].append({
                "id": f"{config.BUTTON_COUPON_PREFIX}{shared_coupon.get('client_id')}:{shared_coupon.get('coupon_id')}",
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
    """Format a welcome message for new or returning users."""
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
                            "id": config.BUTTON_LIST_COUPONS,
                            "title": "📋 הצג קופונים שמורים"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_SHARE_LIST,
                            "title": "👥 שיתוף רשימה עם חבר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_HOW_TO_ADD,
                            "title": "❔ איך להשתמש בקופי"
                        }
                    }
                ]
            }
        }
    }

def build_pairing_confirmation_message(phone_number: str) -> dict:
    """Build a message to confirm pairing with another user."""
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
                            "id": f"{config.BUTTON_CONFIRM_PAIR_PREFIX}{phone_number}",
                            "title": "✅ מאשר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"{config.BUTTON_DECLINE_PAIR_PREFIX}{phone_number}",
                            "title": "❌ לא מאשר"
                        }
                    }
                ]
            }
        }
    }

def format_update_coupon_message(coupon_data):
    """Format a message for updating a coupon."""
    coupon_id = coupon_data.get("coupon_id")
    is_shared = coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."
    buttons = [{
        "type": "reply",
        "reply": {
            "id": f"{config.BUTTON_UPDATE_COUPON_DETAILS_PREFIX}{coupon_id}",
            "title": "📝 עדכן פרטים"
            }
        },{
        "type": "reply",
        "reply": {
            "id": f"{config.BUTTON_CANCEL_COUPON_PREFIX}{coupon_id}",
            "title": "🗑️ מחק קופון"
            }
        }]
    if not is_shared:
        if (coupon_data.get("shared_with") and coupon_data["shared_with"] != "..."):
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"{config.BUTTON_CANCEL_SHARE_PREFIX}{coupon_id}",
                    "title": "בטל שיתוף"
                }
            })                
        else:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"{config.BUTTON_SHARE_COUPON_PREFIX}{coupon_id}",
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
    """Format a message for updating coupon details."""
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
                            "id": f"{config.BUTTON_CANCEL_UPDATE_COUPON_PREFIX}{client_id}:{coupon_id}",
                            "title": "❌ בטל עדכון"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"{config.BUTTON_CANCEL_COUPON_PREFIX}{coupon_id}",
                            "title": "🗑️ מחק קופון"
                        }
                    }
                ]
            }
        }
    }

def format_categories_list(coupons, shared_coupons, title="🎉 צברת אחלה של קופונים!"):
    """Format a list of categories when user has more than 10 coupons."""
    all_coupons = coupons + shared_coupons
    categories = {}
    
    for coupon in all_coupons:
        category = coupon.get("category", "other")
        store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
        if category not in categories:
            categories[category] = {}
        if store not in categories[category]:
            categories[category][store] = 0
        categories[category][store] += 1
    
    sections = [{
        "title": "קטגוריות",
        "rows": []
    }]
    
    for category, stores in categories.items():
        category_name = get_category_name(category)
        category_emoji = get_category_emoji(category)
        
        # Build store list with counts, ensuring we don't cut store names
        store_list = [f"{store} ({count})" if count > 1 else store for store, count in stores.items()]
        desc_parts = []
        current_length = 0
        
        for store_item in store_list:
            item_length = len(store_item) + (2 if desc_parts else 0)  # +2 for ", "
            if current_length + item_length <= 64:
                desc_parts.append(store_item)
                current_length += item_length
            else:
                break
        
        desc = ", ".join(desc_parts)
        if len(desc_parts) < len(store_list):
            desc += " ועוד..."
        
        sections[0]["rows"].append({
            "id": f"{config.BUTTON_CATEGORY_PREFIX}{category}",
            "title": f"{category_emoji} {category_name}",
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
                "text": f"🎁 איזה יופי! צברת כבר {len(all_coupons)} קופונים 🤑\nרוצה למצוא את המתאים לך?\nבחר קטגוריה לפי מה שאתה מחפש 🔍\nאפשר גם לחפש קופון ספציפי — שלח ! ואז את הטקסט לחיפוש, למשל: \"!פיצה\""
            },
            "footer": {
                "text": "בחר קטגוריה כדי לראות את הקופונים"
            },
            "action": {
                "button": "בחר קטגוריה",
                "sections": sections
            }
        }
    }


def format_category_coupons_list(coupons, shared_coupons, category):
    """Format coupons list for a specific category."""
    category_coupons = [c for c in coupons if c.get("category", "other") == category][:10]
    category_shared = [c for c in shared_coupons if c.get("category", "other") == category][:10-len(category_coupons)]
    
    category_name = get_category_name(category)
    category_emoji = get_category_emoji(category)
    
    sections = []
    lines = []
    RTL = "\u200F"

    if category_coupons:
        sections.append({
            "title": "הקופונים שלי",
            "rows": []
        })
        
        for coupon in category_coupons:
            store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
            code = coupon.get("coupon_code", "-") or "(ללא קוד)"
            value = coupon.get("value") or coupon.get("discount_value") or ""
            desc = (f"{value} - " if value else "") + f"קוד: {code}"
            line = f"- {RTL}{store}" + (f" - {value}" if value else "")
            lines.append(line)    
            sections[0]["rows"].append({
                "id": f"{config.BUTTON_COUPON_PREFIX}{coupon.get('client_id')}:{coupon.get('coupon_id')}",
                "title": f"{store}"[:24],
                "description": desc
            })
    
    if category_shared and len(sections) == 0:
        sections.append({
            "title": "קופונים ששותפו איתי",
            "rows": []
        })
        section_idx = 0
    elif category_shared:
        sections.append({
            "title": "קופונים ששותפו איתי",
            "rows": []
        })
        section_idx = 1
    
    if category_shared:
        for coupon in category_shared:
            store = coupon.get("store", "חנות לא ידועה") or "חנות לא ידועה"
            code = coupon.get("coupon_code", "-") or "(ללא קוד)"
            value = coupon.get("value") or coupon.get("discount_value") or ""
            desc = (f"{value} - " if value else "") + f"קוד: {code}"
            line = f"- {RTL}{store}" + (f" - {value}" if value else "") + " 👥 "
            lines.append(line)

            sections[section_idx]["rows"].append({
                "id": f"{config.BUTTON_COUPON_PREFIX}{coupon.get('client_id')}:{coupon.get('coupon_id')}",
                "title": f"{store}"[:24],
                "description": desc
            })
    
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": f"{category_emoji} {category_name}"
            },
            "body": {
                "text": "\n".join(lines) or f"{RTL}אין קופונים בקטגוריה זו."
            },
            "footer": {
                "text": "בחר קופון כדי להציג או לבצע פעולה"
            },
            "action": {
                "button": "בחר קופון",
                "sections": sections
            }
        }
    }

def format_registration_welcome():
    """Format the registration welcome message with all terms, privacy, and agree button."""
    combined_text = (
        "ברוכים הבאים לבוט ניהול הקופונים! 🎉\n\n"
        "לפני שנתחיל, אנא קרא את תנאי השימוש ומדיניות הפרטיות:\n\n"
        "*תנאי שימוש*\n\n"
        "קופי - בוט לניהול קופונים אינו אחראי לאובדן נתונים, נזק או הפסד כלשהו הנובע משימוש בשירות. "
        "המשתמש נושא באחריות מלאה לשמירת מידע הקופונים במקומות חלופיים. "
        "במקרה של מחיקת נתונים ממסד הנתונים של הבוט, המשתמש לא יהיה זכאי לפיצוי או לשחזור הנתונים.\n\n"
        "השימוש בבוט נעשה על אחריותו הבלעדית של המשתמש.\n\n"
        "*מדיניות פרטיות*\n\n"
        "קופי - בוט לניהול קופונים מתחייב שלא להשתמש בנתוני הקופונים לצרכים מסחריים או להעבירם לצדדים שלישיים. "
        "הנתונים מאוחסנים בבסיס נתונים מאובטח בפלטפורמת AWS ומוגנים באמצעים טכניים מתקדמים.\n\n"
        "עם זאת, הבוט עשוי להשתמש בנתונים סטטיסטיים אנונימיים (ללא פרטים מזהים או קודי קופונים) לצורך שיפור השירות, ניתוח מגמות ופיתוח תכונות עתידיות."
    )
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": combined_text
            },
            "footer": {
                "text": "אחרי קריאת התנאים והמדיניות, לחץ על מסכים"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_AGREE,
                            "title": "✅ מסכים לכל"
                        }
                    }
                ]
            }
        }
    }

def format_terms_of_service():
    """Format the terms of service message."""
    terms_text = (
        "*תנאי שימוש*\n\n"
        "קופי - בוט לניהול קופונים אינו אחראי לאובדן נתונים, נזק או הפסד כלשהו הנובע משימוש בשירות. "
        "המשתמש נושא באחריות מלאה לשמירת מידע הקופונים במקומות חלופיים. "
        "במקרה של מחיקת נתונים ממסד הנתונים של הבוט, המשתמש לא יהיה זכאי לפיצוי או לשחזור הנתונים.\n\n"
        "השימוש בבוט נעשה על אחריותו הבלעדית של המשתמש."
    )
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": terms_text
            },
            "footer": {
                "text": "אחרי קריאת התנאים, לחץ על מסכים"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_AGREE,
                            "title": "✅ מסכים"
                        }
                    }
                ]
            }
        }
    }

def format_privacy_policy():
    """Format the privacy policy message."""
    privacy_text = (
        "*מדיניות פרטיות*\n\n"
        "קופי - בוט לניהול קופונים מתחייב שלא להשתמש בנתוני הקופונים לצרכים מסחריים או להעבירם לצדדים שלישיים. "
        "הנתונים מאוחסנים בבסיס נתונים מאובטח בפלטפורמת AWS ומוגנים באמצעים טכניים מתקדמים.\n\n"
        "עם זאת, הבוט עשוי להשתמש בנתונים סטטיסטיים אנונימיים (ללא פרטים מזהים או קודי קופונים) לצורך שיפור השירות, ניתוח מגמות ופיתוח תכונות עתידיות."
    )
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": privacy_text
            },
            "footer": {
                "text": "אחרי קריאת המדיניות, לחץ על מסכים"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_AGREE,
                            "title": "✅ מסכים"
                        }
                    }
                ]
            }
        }
    }

def format_commands_list():
    """Format the list of available commands after registration."""
    commands_text = (
        "*הפקודות הזמינות:*\n\n"
        "📋 */list* או *!* - הצג את רשימת הקופונים שלך\n"
        "📅 */list_expiring* - הצג קופונים שעומדים לפוג\n"
        "🔍 *!* - חפש קופונים (למשל: !פיצה)\n"
        "👥 */share_list [מספר טלפון]* - שתף רשימת קופונים עם חבר\n"
        "🚫 */cancel_sharing* - בטל שיתוף רשימה\n"
        "🌐 */web* - פתח את רשימת הקופונים בדפדפן\n"
        "➕ שלח תמונה, PDF או טקסט של קופון כדי להוסיף אותו\n\n"
        "תהנה מהשימוש! 😊"
    )
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": commands_text
            },
            "footer": {
                "text": "בחר אפשרות מהירה"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_LIST_COUPONS,
                            "title": "📋 הצג קופונים שמורים"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_SHARE_LIST,
                            "title": "👥 שיתוף רשימה עם חבר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": config.BUTTON_HOW_TO_ADD,
                            "title": "❔ איך להשתמש בקופי"
                        }
                    }
                ]
            }
        }
    }

def format_used_coupon_message(coupon_id, coupon_data):
    """Format a message for a used coupon with option to unmark."""
    store = coupon_data.get('store', 'חנות לא ידועה') or 'חנות לא ידועה'
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": f"הקופון ל- *{store}* קוד: *{coupon_data['coupon_code']}* כבר קיים ברשימה שלך, אבל הוא מסומן כנוצל.\n\nרוצה לבטל את הסימון ולהפעיל אותו מחדש?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"{config.BUTTON_UNMARK_AS_USED_PREFIX}{coupon_data['client_id']}:{coupon_id}",
                            "title": "✅ הפעל מחדש"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"{config.BUTTON_CANCEL_COUPON_PREFIX}{coupon_id}",
                            "title": "🗑️ מחק קופון"
                        }
                    }
                ]
            }
        }
    }

def format_web_link_message(web_url):
    """Format an interactive message with external link to web app."""
    return {
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {
                "text": "*תצוגה מלאה ונוחה בדפדפן*\n\nלצפייה וניהול נוחים יותר — פתח את \"קופי\" בדפדפן 📋✨"
            },
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "פתח בדפדפן",
                    "url": web_url
                }
            }
        }
    }