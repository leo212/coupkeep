"""
AWS Lambda function for handling WhatsApp webhook events for coupon management.
"""

import json
import urllib3
import uuid
import traceback
import config
import services.coupon_parser as coupon_parser
import services.whatsapp as whatsapp
import services.storage_service as storage_service
import utils.response_formatter as response_formatter

http = urllib3.PoolManager()

def response_with_coupon(coupon_data, msg_id, phone_number, is_new=True):
    """
    Handles the incoming coupon data by sending a reaction to the user's message,
    saving the coupon, and sending a confirmation message with the coupon details.
    
    Args:
        coupon_data: Dictionary containing coupon information
        msg_id: ID of the message that contained the coupon
        phone_number: User's phone number
        is_new: Whether this is a new coupon or an existing one
    """
    if (coupon_data["valid"]):
        whatsapp.send_reaction(phone_number, msg_id, config.REACTION_BOOKMARK)
        # generate UUID for the coupon and store it
        if is_new:
            coupon_id = str(uuid.uuid4())
            storage_service.store_new_coupon(phone_number, coupon_id, msg_id, coupon_data)   
        else:
            coupon_id = coupon_data["coupon_id"]
                                                         
        formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=is_new)                                                                    
        whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
    else:
        whatsapp.send_reaction(phone_number, msg_id, config.REACTION_ERROR)

def show_list_of_coupons(from_number):
    """
    Retrieves and displays the user's coupons and any shared coupons.
    
    Args:
        from_number: User's phone number
    """
    coupons = storage_service.get_user_coupons(from_number)
    shared_coupons = storage_service.get_shared_coupons(from_number)
    
    total_coupons = len(coupons) + len(shared_coupons)
    
    if total_coupons <= 10:
        formatted_list = response_formatter.format_coupons_list_interactive(coupons, shared_coupons)
    else:
        formatted_list = response_formatter.format_categories_list(coupons, shared_coupons)
    
    whatsapp.send_whatsapp_message(from_number, formatted_list, is_interactive=True)

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
    
    # Handle commands
    if msg_text == config.CMD_LIST or msg_text == config.CMD_LIST_SHORT:                            
        show_list_of_coupons(from_number)
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
        
    # Handle regular text (potential coupon)
    user_state = storage_service.get_user_state(from_number)

    if user_state is None:
        # new user
        user_state = config.STATE_IDLE
        storage_service.set_user_state(from_number, user_state)
    
    if len(msg_text) > 10:
        whatsapp.send_reaction(from_number, msg_id, config.REACTION_PROCESSING)

        if user_state == config.STATE_IDLE:
            # extract fields using NLP
            coupon_data = coupon_parser.parse_coupon_details(msg_text)
            # check if there are more than one coupon
            if isinstance(coupon_data, list):
                # Handle multiple coupons
                valid_coupons = False
                for coupon in coupon_data:
                    if coupon["valid"]:
                        response_with_coupon(coupon, msg_id, from_number, is_new=True)
                        valid_coupons = True
                
                if not valid_coupons:
                    # clear reaction
                    whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
                    whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False), is_interactive=True)

            else:            
                if not coupon_data["valid"]:
                    # clear reaction
                    whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)

                    # check if the user has valid coupons
                    coupons = storage_service.get_user_coupons(from_number)
                    if len(coupons) > 0:                                
                        whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False), is_interactive=True)
                    else:
                        whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=True), is_interactive=True)
                else:
                    response_with_coupon(coupon_data, msg_id, from_number)
                
        elif user_state.startswith(config.STATE_UPDATE_COUPON_PREFIX):
            coupon_id = user_state.split(":")[1]
            print("Updating coupon:", coupon_id)
            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
            updated_coupon_data = coupon_parser.parse_update_request_details(coupon_data, msg_text)
            print("Updated coupon data:", json.dumps(updated_coupon_data))
    else:
        coupon_data = { "valid": False }
        updated_coupon_data = { "valid": False }

    if user_state.startswith(config.STATE_UPDATE_COUPON_PREFIX):
        if updated_coupon_data["valid"]:
            # update the coupon
            storage_service.update_coupon_details(coupon_data, updated_coupon_data)
            coupon_data["valid"] = True
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_SUCCESS)
            response_with_coupon(coupon_data, msg_id, from_number, is_new=False)
            storage_service.set_user_state(from_number, config.STATE_IDLE)
        else:
            whatsapp.send_reaction(from_number, msg_id, config.REACTION_ERROR)
            coupon_id = user_state.split(":")[1]
            if updated_coupon_data.get("examples"):
                # Use the examples provided in the updated coupon data
                examples = "\n".join([f"- “{example}“" for example in updated_coupon_data["examples"]])
            else:
                examples = "- “שנה את התוקף ל־1.8.25”\n- “עדכן את שם החנות ל־Fox”\n"
            whatsapp.send_whatsapp_message(from_number, response_formatter.format_update_coupon_details_message(from_number, coupon_id, text=f"לא הצלחתי להבין את הבקשה לעדכון הקופון.\n\nאפשר לנסות לנסח שוב, למשל:\n{examples}\nאו לחץ ❌ כדי לבטל את העריכה."), is_interactive=True)
    
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
                        response_with_coupon(coupon, msg_id, from_number, is_new=True)
                        valid_coupons = True
                
                if not valid_coupons:
                    # clear reaction
                    whatsapp.send_reaction(from_number, msg_id, config.REACTION_NONE)
                    whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False), is_interactive=True)
            else:    
                response_with_coupon(coupon_data, msg_id, from_number)
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
    
    if interactive.get("type") == "button_reply":
        button_id = interactive["button_reply"]["id"]
        
        if button_id == config.BUTTON_LIST_COUPONS:
            show_list_of_coupons(from_number)
            return True
        elif button_id == config.BUTTON_SHARE_LIST:
            share_payload = response_formatter.format_share_list_interactive(from_number)
            whatsapp.send_whatsapp_message(from_number, share_payload, is_interactive=True)
            return True
        elif button_id == config.BUTTON_HOW_TO_ADD:
            how_to_add_message = "כדי להוסיף קופון חדש, פשוט שלח לי:\n\n1️⃣ *תמונה* של הקופון\n2️⃣ *קובץ PDF* שמכיל את הקופון\n3️⃣ *טקסט* עם פרטי הקופון\n\nאני אזהה אוטומטית את הפרטים ואשמור אותו עבורך! 📱✨"
            whatsapp.send_whatsapp_message(from_number, how_to_add_message)
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
    
    return False

def lambda_handler(event, context):
    """
    AWS Lambda handler function for processing WhatsApp webhook events.
    
    Args:
        event: AWS Lambda event object
        context: AWS Lambda context object
        
    Returns:
        Response object with status code and body
    """
    print("Received event:")
    print(json.dumps(event))

    method = event.get("requestContext", {}).get("http", {}).get("method", "")

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
                    
            return {"statusCode": 200, "body": "OK"}
        except Exception as e:
            print("Error processing message:", str(e))
            traceback.print_exc()
            return {"statusCode": 500, "body": "Error processing message"}