# -*- coding: utf-8 -*-
"""
AWS Lambda function for handling WhatsApp webhook events for coupon management.
"""

import json
import urllib3
import uuid
import traceback
import base64
import config
import services.coupon_parser as coupon_parser
import services.whatsapp as whatsapp
import services.storage_service as storage_service
import services.auth_service as auth_service
import services.rest_handler as rest_handler
import utils.response_formatter as response_formatter
from datetime import datetime, timedelta

http = urllib3.PoolManager()

def debug_print_coupons(coupons, shared_coupons, from_number):
    print(f"Loaded {len(coupons)} coupons and {len(shared_coupons)} shared coupons for user {from_number}")
    for c in coupons:
        print(f"Coupon: {c['coupon_code']} - {c.get('store', 'Unknown Store')} - {c.get('category', 'Uncategorized')} - expires on {c.get('expiration_date', 'Unknown Expiration')}")
    for c in shared_coupons:
        print(f"Shared Coupon: {c['coupon_code']} - {c.get('store', 'Unknown Store')} - {c.get('category', 'Uncategorized')} - expires on {c.get('expiration_date', 'Unknown Expiration')} - shared by {c.get('shared_by_client_id', 'Unknown')}")  

def response_with_coupon(coupon_data, msg_id, phone_number, is_new=True, existing_coupon=None):
    """
    Handles the incoming coupon data by sending a reaction to the user's message,
    saving the coupon, and sending a confirmation message with the coupon details.
    
    Args:
        coupon_data: Dictionary containing coupon information
        msg_id: ID of the message that contained the coupon
        phone_number: User's phone number
        is_new: Whether this is a new coupon or an existing one
        existing_coupon: Existing coupon data if duplicate found
    """
    if (coupon_data["valid"]):
        whatsapp.send_reaction(phone_number, msg_id, config.REACTION_BOOKMARK)
        
        if existing_coupon:
            # Duplicate coupon found
            coupon_id = existing_coupon['coupon_id']
            if existing_coupon.get('coupon_status') == 'used':
                # Coupon was used, offer to unmark
                formatted = response_formatter.format_used_coupon_message(coupon_id, existing_coupon)
                whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
            else:
                # Show existing coupon
                formatted = response_formatter.format_response(coupon_id, existing_coupon, is_new=False)
                whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
        elif is_new:
            coupon_id = str(uuid.uuid4())
            storage_service.store_new_coupon(phone_number, coupon_id, msg_id, coupon_data)   
            formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=is_new)                                                                    
            whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
        else:
            coupon_id = coupon_data["coupon_id"]
            formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=is_new)                                                                    
            whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
    else:
        whatsapp.send_reaction(phone_number, msg_id, config.REACTION_ERROR)

def show_list_of_coupons(from_number, expiring_soon=False):
    """
    Retrieves and displays the user's coupons and any shared coupons.
    
    Args:
        from_number: User's phone number
        expiring_soon: If True, show only coupons expiring soon
    """
    coupons = storage_service.get_user_coupons(from_number, expiring_soon=expiring_soon)
    shared_coupons = storage_service.get_shared_coupons(from_number, expiring_soon=expiring_soon)
    
    total_coupons = len(coupons) + len(shared_coupons)
    
    if expiring_soon:
        title_coupons = "📋 קופונים שעומדים לפוג בקרוב:"
        title_categories = "🎉 קופונים שעומדים לפוג בקרוב!"
    else:
        title_coupons = "📋 רשימת הקופונים שלך:"
        title_categories = "🎉 צברת אחלה של קופונים!"
    
    if total_coupons <= 10:
        formatted_list = response_formatter.format_coupons_list_interactive(coupons, shared_coupons, title=title_coupons)
    else:
        formatted_list = response_formatter.format_categories_list(coupons, shared_coupons, title=title_categories)
    
    whatsapp.send_whatsapp_message(from_number, formatted_list, is_interactive=True)

def send_web_cta(from_number):
    """Send the web UI CTA to an already registered user."""
    web_url = auth_service.get_web_url(from_number)
    if web_url:
        formatted = response_formatter.format_web_link_message(web_url)
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)

def process_coupon_update(from_number, coupon_id, msg_text, msg_id, from_state):
    """
    Process a coupon update request and handle the result.
    
    Args:
        from_number: User's phone number
        coupon_id: ID of the coupon to update
        msg_text: The update text from the user
        msg_id: WhatsApp message ID
        from_state: The state we came from (for context)
    """
    import services.coupon_service as coupon_service
    
    coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
    if not coupon_data:
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
        whatsapp.send_whatsapp_message(from_number, "הקופון לא נמצא.")
        storage_service.set_user_state(from_number, config.STATE_IDLE)
        return
    
    result = coupon_service.update_coupon(from_number, coupon_id, msg_text)
    print("Update result:", json.dumps(result, ensure_ascii=False))
    
    if result['status'] == 'updated':
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
        whatsapp.send_whatsapp_message(from_number, result.get('summary', 'הקופון עודכן בהצלחה.'))
        
        # Show updated coupon
        updated_coupon = result['coupon']
        updated_coupon['valid'] = True
        response_with_coupon(updated_coupon, msg_id, from_number, is_new=False)
        storage_service.set_user_state(from_number, config.STATE_IDLE)
    elif result['status'] == 'ambiguous':
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
        
        # Use the message returned by Gemini/coupon_service
        prompt_message = result.get('message', 'לא הבנתי למה הכוונה בדיוק, הנה כמה אפשרויות:')
        options = result.get('options', [])
        
        # Store options in state for when user selects an option
        options_str = json.dumps(options, ensure_ascii=False)
        encoded_options = base64.b64encode(options_str.encode()).decode()
        state_value = f"{config.STATE_PENDING_UPDATE_OPTION_SELECTION}{coupon_id}|{encoded_options}"
        storage_service.set_user_state(from_number, state_value)
        
        # Send as interactive list
        interactive_payload = response_formatter.format_update_options_interactive(prompt_message, options)
        whatsapp.send_whatsapp_message(from_number, interactive_payload, is_interactive=True)
    else:
        # Fallback for unexpected status (should rarely occur with new Gemini behavior)
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
        message = result.get('message', 'לא הצלחתי להבין את בקשת העדכון.')
        whatsapp.send_whatsapp_message(from_number, message)

def handle_text_message(msg, from_number):
    """
    Handles text messages from users, including commands and coupon text.
    
    Args:
        msg: Message object from WhatsApp
        from_number: User's phone number
        
    Returns:
        Boolean indicating if the message was handled
    """
    msg_text = msg["text"]["body"]
    msg_id = msg["id"]
    
    # Check user state first - new users must register
    user_state = storage_service.get_user_state(from_number)
    if user_state is None or user_state == config.STATE_REGISTRATION_PENDING:
        # new user or pending registration
        if user_state is None:
            storage_service.set_user_state(from_number, config.STATE_REGISTRATION_PENDING)
        formatted = response_formatter.format_registration_welcome()
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    
    # Handle commands
    if msg_text == config.CMD_WEB:
        web_url = auth_service.get_web_url(from_number)
        formatted = response_formatter.format_web_link_message(web_url)
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    elif msg_text.startswith(config.CMD_SEARCH) and len(msg_text) > 1:
        # Search coupons
        search_query = msg_text[1:].strip()
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)
        
        coupons = storage_service.get_user_coupons(from_number)
        if not coupons:
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
            whatsapp.send_whatsapp_message(from_number, "אין לך קופונים לחיפוש.")
            return True
        
        search_result = coupon_parser.search_coupons(coupons, search_query)
        matching_ids = search_result.get('coupon_ids', [])
        
        if not matching_ids:
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
            whatsapp.send_whatsapp_message(from_number, f"לא נמצאו קופונים התואמים לחיפוש: {search_query}")
        else:
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            matching_coupons = [c for c in coupons if c['coupon_id'] in matching_ids]
            formatted = response_formatter.format_coupons_list_interactive(matching_coupons, [], title=f"🔍 תוצאות חיפוש: {search_query}")
            whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    elif msg_text == config.CMD_LIST or msg_text == config.CMD_LIST_SHORT:                            
        show_list_of_coupons(from_number)
        send_web_cta(from_number)
        return True
    elif msg_text == "/list_expiring":
        show_list_of_coupons(from_number, expiring_soon=True)
        return True
    elif msg_text.startswith(config.CMD_ADD_SHARED_COUPON):                                                        
        # Extract the coupon ID from the message text
        coupon_share_token = msg_text.split(" ")[1] 
        # Retrieve the coupon data from the shared coupon
        coupon_data = storage_service.get_shared_coupon(coupon_share_token)
        
        if coupon_data is None:
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
            whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שהוא כבר נוצל או שהופסק השיתוף?🤔")
        else:                                
            # coupon found - add it to the user's coupons
            storage_service.share_coupon_with_user(coupon_data['client_id'], coupon_data['coupon_id'], from_number)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)                            

            # display it 
            formatted = response_formatter.format_response(coupon_data['coupon_id'], coupon_data, is_temporary=False, is_shared=True)
            whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    elif msg_text.startswith(config.CMD_SHARE_LIST):
        parts = msg_text.split(" ")
        if len(parts) < 2:
            share_payload = response_formatter.format_share_list_interactive(from_number)
            whatsapp.send_whatsapp_message(from_number, share_payload, is_interactive=True)
        else:                                
            target_client_id = msg_text.split(" ")[1]
            # allow one way sharing from this client and the target client
            storage_service.confirm_pairing(from_number, target_client_id)                                
            # request the other client to approve that as well
            whatsapp.send_whatsapp_message(target_client_id, response_formatter.build_pairing_confirmation_message(from_number), is_interactive=True)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
        return True
    elif msg_text.startswith(config.CMD_CANCEL_SHARING):
        storage_service.cancel_pairing(from_number)
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
        return True
        
    # Handle short messages or help requests for registered users
    if user_state == config.STATE_IDLE and (len(msg_text) <= 10 or msg_text in ['?', 'help', 'עזרה', 'אופציה']):
        coupons = storage_service.get_user_coupons(from_number)
        formatted = response_formatter.format_welcome_message(new_user=(len(coupons) == 0))
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        send_web_cta(from_number)
        return True

    # Handle regular text (potential coupon or update)
    if len(msg_text) > 0:
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)

        if user_state == config.STATE_IDLE:
            # Check for very short update-like messages that might be missed by the >10 check
            if len(msg_text) > 10:
                # extract fields using NLP
                coupon_data = coupon_parser.parse_coupon_details(msg_text)
                # check if there are more than one coupon
                if isinstance(coupon_data, list):
                    # Handle multiple coupons
                    valid_coupons = False
                    for coupon in coupon_data:
                        if coupon["valid"]:
                            # Check for duplicate
                            existing = None
                            if coupon.get('coupon_code'):
                                existing = storage_service.find_coupon_by_code(from_number, coupon['coupon_code'])
                            response_with_coupon(coupon, msg_id, from_number, is_new=True, existing_coupon=existing)
                            valid_coupons = True
                    
                    if not valid_coupons:
                        # clear reaction
                        whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
                        whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False), is_interactive=True)

                else:            
                    if not coupon_data["valid"]:
                        # clear reaction
                        whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)

                        # Show welcome message for unrecognized text
                        coupons = storage_service.get_user_coupons(from_number)
                        formatted = response_formatter.format_welcome_message(new_user=(len(coupons) == 0))
                        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
                    else:
                        # Check for duplicate
                        existing = None
                        if coupon_data.get('coupon_code'):
                            existing = storage_service.find_coupon_by_code(from_number, coupon_data['coupon_code'])
                        response_with_coupon(coupon_data, msg_id, from_number, existing_coupon=existing)
            else:
                 # message too short and in IDLE, just clear reaction
                 whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
                 return True
                
        elif user_state.startswith(config.STATE_UPDATE_COUPON_PREFIX):
            coupon_id = user_state.split(":")[1]
            print("Updating coupon via WhatsApp:", coupon_id, "text:", msg_text)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)
            process_coupon_update(from_number, coupon_id, msg_text, msg_id, config.STATE_UPDATE_COUPON_PREFIX)
        
        elif user_state.startswith(config.STATE_PENDING_UPDATE_OPTION_SELECTION):
            # User sent a new text message while waiting for option selection
            # Extract coupon_id from state and process the new update text
            state_parts = user_state.split("|")
            coupon_id = state_parts[0].replace(config.STATE_PENDING_UPDATE_OPTION_SELECTION, "")
            
            print("User sent new text during option selection:", coupon_id, "text:", msg_text)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)
            process_coupon_update(from_number, coupon_id, msg_text, msg_id, config.STATE_PENDING_UPDATE_OPTION_SELECTION)
    
    return True

def handle_media_message(msg, from_number):
    """
    Handles media messages (images, documents) from users.
    
    Args:
        msg: Message object from WhatsApp
        from_number: User's phone number
        
    Returns:
        Boolean indicating if the message was handled
    """
    msg_id = msg["id"]
    media_id = None
    media_type = msg.get("type")
    
    user_state = storage_service.get_user_state(from_number)
    if user_state is None or user_state == config.STATE_REGISTRATION_PENDING:
        formatted = response_formatter.format_registration_welcome()
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    
    if media_type == "image":
        media_id = msg["image"]["id"]
    elif media_type == "document":
        media_id = msg["document"]["id"]
    else:
        return False
        
    if media_id:
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)
        try:
            media_bytes = whatsapp.download_media(media_id)
            
            if media_type == "document" and msg["document"]["mime_type"] == "application/pdf":
                coupon_data = coupon_parser.parse_pdf(media_bytes)
            else:
                # Process as image
                coupon_data = coupon_parser.parse_image(media_bytes)

            # check if there are more than one coupon
            print("Parsed coupon data:", json.dumps(coupon_data, ensure_ascii=False))
            if isinstance(coupon_data, list):
                # Handle multiple coupons
                valid_coupons = False
                for coupon in coupon_data:
                    if coupon["valid"]:
                        # Check for duplicate
                        existing = None
                        if coupon.get('coupon_code'):
                            existing = storage_service.find_coupon_by_code(from_number, coupon['coupon_code'])
                        response_with_coupon(coupon, msg_id, from_number, is_new=True, existing_coupon=existing)
                        valid_coupons = True
                
                if not valid_coupons:
                    # clear reaction
                    whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
                    whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False), is_interactive=True)
            else:
                # Check for duplicate
                existing = None
                if coupon_data.get('coupon_code'):
                    existing = storage_service.find_coupon_by_code(from_number, coupon_data['coupon_code'])
                response_with_coupon(coupon_data, msg_id, from_number, existing_coupon=existing)
            return True
        except Exception as e:
            print(f"Error processing media: {str(e)}")
            traceback.print_exc()
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
            whatsapp.send_whatsapp_message(from_number, "אופס, לא הצלחתי לעבד את הקובץ. נסה שוב או שלח את הקופון כטקסט.")
            return True
    
    return False

def handle_interactive_message(msg, from_number):
    """
    Handles interactive messages (button clicks) from users.
    
    Args:
        msg: Message object from WhatsApp
        from_number: User's phone number
        
    Returns:
        Boolean indicating if the message was handled
    """
    if "interactive" not in msg:
        return False
        
    interactive = msg["interactive"]
    msg_id = msg["id"]
    
    user_state = storage_service.get_user_state(from_number)
    
    if interactive.get("type") == "button_reply":
        button_id = interactive["button_reply"]["id"]
        
        if button_id == config.BUTTON_AGREE:
            if user_state == config.STATE_REGISTRATION_PENDING:
                # Agreeing to terms and privacy, complete registration
                storage_service.set_user_state(from_number, config.STATE_IDLE)
                web_url = auth_service.get_web_url(from_number)
                formatted = response_formatter.format_commands_list(web_url)
                whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
            return True
        
        if button_id == config.BUTTON_LIST_COUPONS:
            show_list_of_coupons(from_number)
            send_web_cta(from_number)
            return True
        elif button_id == config.BUTTON_SHARE_LIST:
            share_payload = response_formatter.format_share_list_interactive(from_number)
            whatsapp.send_whatsapp_message(from_number, share_payload, is_interactive=True)
            return True
        elif button_id == config.BUTTON_HOW_TO_ADD:
            how_to_add_message = (
                "כדי להוסיף קופון חדש, פשוט שלח לי:\n\n"
                "1️⃣ *תמונה* של הקופון\n"
                "2️⃣ *קובץ PDF* שמכיל את הקופון\n"
                "3️⃣ *טקסט* עם פרטי הקופון\n\n"
                "אני אזהה אוטומטית את הפרטים ואשמור אותו עבורך! 📱✨\n\n"
                "*פקודות נוספות:*\n"
                "📋 */list* או *!* - הצג את רשימת הקופונים שלך\n"
                "📅 */list_expiring* - הצג קופונים שעומדים לפוג\n"
                "🔍 *!* - חפש קופונים (למשל: !פיצה)\n"
                "👥 */share_list [מספר טלפון]* - שתף רשימת קופונים עם חבר\n"
                "🚫 */cancel_sharing* - בטל שיתוף רשימה\n"
                "🌐 */web* - פתח את רשימת הקופונים בדפדפן\n"
                "\n"
                "תהנה מהשימוש! 😊"            )
            whatsapp.send_whatsapp_message(from_number, how_to_add_message)
            send_web_cta(from_number)
            return True
        elif button_id.startswith(config.BUTTON_UPDATE_COUPON_PREFIX):
            coupon_id = button_id.split(":")[1]
            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
            if coupon_data:
                formatted = response_formatter.format_update_coupon_message(coupon_data)
                whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
            return True
        elif button_id.startswith(config.BUTTON_UPDATE_COUPON_DETAILS_PREFIX):
            coupon_id = button_id.split(":")[1]
            storage_service.set_user_state(from_number, f"{config.STATE_UPDATE_COUPON_PREFIX}{coupon_id}")
            formatted = response_formatter.format_update_coupon_details_message(from_number, coupon_id)
            whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
            return True
        elif button_id.startswith(config.BUTTON_CANCEL_UPDATE_COUPON_PREFIX):
            storage_service.set_user_state(from_number, config.STATE_IDLE)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            return True
        elif button_id.startswith(config.BUTTON_MARK_AS_USED_PREFIX):
            parts = button_id.split(":")
            client_id = parts[1]
            coupon_id = parts[2]
            storage_service.mark_coupon_as_used(client_id, coupon_id)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            return True
        elif button_id.startswith(config.BUTTON_UNMARK_AS_USED_PREFIX):
            parts = button_id.split(":")
            client_id = parts[1]
            coupon_id = parts[2]
            storage_service.unmark_coupon_as_used(client_id, coupon_id)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            # Show the coupon again
            coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
            if coupon_data:
                formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=False)
                whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
            return True
        elif button_id.startswith(config.BUTTON_CANCEL_COUPON_PREFIX):
            coupon_id = button_id.split(":")[1]
            storage_service.cancel_coupon(from_number, coupon_id)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            return True
        elif button_id.startswith(config.BUTTON_SHARE_COUPON_PREFIX):
            coupon_id = button_id.split(":")[1]
            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
            if coupon_data:
                sharing_token = storage_service.generate_sharing_token(from_number, coupon_id)
                formatted = response_formatter.format_share_coupon_interactive(coupon_data, sharing_token)
                whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
            return True
        elif button_id.startswith(config.BUTTON_CANCEL_SHARE_PREFIX):
            coupon_id = button_id.split(":")[1]
            storage_service.cancel_coupon_sharing(from_number, coupon_id)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            return True
        elif button_id.startswith(config.BUTTON_CONFIRM_PAIR_PREFIX):
            target_client_id = button_id.split(":")[1]
            storage_service.confirm_pairing(from_number, target_client_id)
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            return True
        elif button_id.startswith(config.BUTTON_DECLINE_PAIR_PREFIX):
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            whatsapp.send_whatsapp_message(from_number, "בחירתך התקבלה. לא יתבצע שיתוף קופונים.")
            return True
        elif button_id.startswith(config.BUTTON_SHOW_COUPON_PREFIX):
            coupon_id = button_id.split(":")[1]
            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
            if coupon_data is None:
                whatsapp.send_reaction(from_number, msg["id"], "✖️")
                whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שכבר ניצלת אותו?🤔")
                return {"statusCode": 200, "body": "OK"}
            else:
                whatsapp.send_reaction(from_number, msg["id"], "👍")
                whatsapp.send_whatsapp_message(from_number, "הנה הקופון המקורי ששלחת לי", reg_msg=coupon_data["msg_id"], is_interactive=False)
            return True
    
    elif interactive.get("type") == "list_reply":
        list_id = interactive["list_reply"]["id"]

        if list_id.startswith(config.BUTTON_COUPON_PREFIX):
            parts = list_id.split(":")
            client_id = parts[1]
            coupon_id = parts[2]
            coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
            if coupon_data:
                is_shared = client_id != from_number
                formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=False, is_shared=is_shared)
                whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
                # Send coupon code separately for easy copy-paste
                if coupon_data.get("coupon_code"):
                    whatsapp.send_whatsapp_message(from_number, coupon_data["coupon_code"])
            return True
        elif list_id.startswith(config.BUTTON_CATEGORY_PREFIX):
            category = list_id.split(":")[1]
            coupons = storage_service.get_user_coupons(from_number)
            shared_coupons = storage_service.get_shared_coupons(from_number)            
            formatted_list = response_formatter.format_category_coupons_list(coupons, shared_coupons, category)
            whatsapp.send_whatsapp_message(from_number, formatted_list, is_interactive=True)
            return True
        elif list_id.startswith("update_opt_"):
            # Handle update option selection
            if user_state and user_state.startswith(config.STATE_PENDING_UPDATE_OPTION_SELECTION):
                state_parts = user_state.split("|")
                if len(state_parts) == 2:
                    # Extract coupon_id and options
                    coupon_id = state_parts[0].replace(config.STATE_PENDING_UPDATE_OPTION_SELECTION, "")
                    encoded_options = state_parts[1]
                    
                    try:
                        # Decode options
                        options = json.loads(base64.b64decode(encoded_options).decode())
                        
                        # Get the option index from the list ID (update_opt_1 -> index 0)
                        option_index = int(list_id.replace("update_opt_", "")) - 1
                        
                        if 0 <= option_index < len(options):
                            selected_option = options[option_index]
                            update_fields = selected_option.get('update_fields', {})
                            
                            # Apply the update
                            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                            if coupon_data:
                                # Update coupon with selected option's fields
                                storage_service.update_coupon_details(coupon_data, update_fields)
                                
                                # Reload coupon to show updated data
                                updated_coupon = storage_service.get_coupon_by_code(from_number, coupon_id)
                                if updated_coupon:
                                    updated_coupon['valid'] = True
                                
                                # Send confirmation and show updated coupon
                                whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
                                whatsapp.send_whatsapp_message(from_number, f"✅ {selected_option.get('label', 'הקופון עודכן בהצלחה')}")
                                response_with_coupon(updated_coupon, msg_id, from_number, is_new=False)
                                storage_service.set_user_state(from_number, config.STATE_IDLE)
                                return True
                    except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
                        print(f"Error decoding update options: {e}")
                        whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
                        whatsapp.send_whatsapp_message(from_number, "אופס, הייתה בעיה בעיבוד בחירתך. נסה שוב.")
                    return True
    
    return False

def handle_button_message(msg, from_number):
    """
    Handles button messages from users.
    
    Args:
        msg: Message object from WhatsApp
        from_number: User's phone number
        
    Returns:
        Boolean indicating if the message was handled
    """
    if "button" not in msg:
        return False
    
    button_payload = msg["button"]["payload"]
    msg_id = msg["id"]
    
    user_state = storage_service.get_user_state(from_number)
    if user_state is None or user_state == config.STATE_REGISTRATION_PENDING:
        formatted = response_formatter.format_registration_welcome()
        whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
        return True
    
    if button_payload == "הצג קופונים שעומדים לפוג":
        show_list_of_coupons(from_number, expiring_soon=True)
        return True
    
    return False

def lambda_handler(event, context):
    """
    AWS Lambda handler function for processing WhatsApp webhook events and REST API.
    
    Args:
        event: AWS Lambda event object
        context: AWS Lambda context object
        
    Returns:
        Response object with status code and body
    """
    print("Received event:")
    print(json.dumps(event))

    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")

    # Check if this is a REST API request
    if path.startswith('/default/api/'):
        try:
            if method == "OPTIONS":
                return {
                    "statusCode": 204,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*"
                    }
                }
            return rest_handler.handle_rest_api(event)
        except Exception as e:
            print(f"REST API Error: {str(e)}")
            traceback.print_exc()
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*"
                },
                "body": json.dumps({"error": "Internal server error"})
            }

    # WhatsApp webhook handling
    if method == "GET":
        # Meta webhook verification
        params = event.get("queryStringParameters", {})                
        if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == config.VERIFY_TOKEN:
            response = {
                "statusCode": 200,
                "body": params.get("hub.challenge")
            }
        else:
            response = {
                "statusCode": 403,
                "body": "Verification token mismatch"
            }
        print(json.dumps(response))
        return response

    elif method == "POST":
        body = json.loads(event.get("body", "{}"))
        try:
            # message received
            print("Received message:", json.dumps(body))
            if "messages" in body["entry"][0]["changes"][0]["value"]:                
                msg = body["entry"][0]["changes"][0]["value"]["messages"][0]                
                print("Incoming:", json.dumps(msg))
                from_number = msg["from"]
                whatsapp.send_read_receipt(from_number, msg["id"])
                
                # Handle different message types
                if msg.get("type") == "text":
                    handle_text_message(msg, from_number)
                elif msg.get("type") in ["image", "document"]:
                    handle_media_message(msg, from_number)
                elif msg.get("type") == "interactive":
                    handle_interactive_message(msg, from_number)
                elif msg.get("type") == "button":
                    handle_button_message(msg, from_number)
                    
            return {"statusCode": 200, "body": "OK"}
        except Exception as e:
            print("Error processing message:", str(e))
            traceback.print_exc()
            return {"statusCode": 500, "body": "Error processing message"}
