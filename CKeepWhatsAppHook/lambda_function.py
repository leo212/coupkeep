import json
import os
import urllib3
import services.coupon_parser as coupon_parser
import services.whatsapp as whatsapp
import services.storage_service as storage_service
import utils.response_formatter as response_formatter
import utils.image_utils as image_utils
import uuid
import urllib 
import traceback

http = urllib3.PoolManager()

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # long-lived token
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_PHONE_NUMBER = os.environ.get("WHATSAPP_PHONE_NUMBER")

def response_with_coupon(coupon_data, msg_id, phone_number, is_new=True):
    """
    Handles the incoming coupon data by sending a reaction to the user's message,
    saving the coupon, and sending a confirmation message with the coupon details.
    """
    if (coupon_data["valid"]):
        whatsapp.send_reaction(phone_number, msg_id, "🔖")
        # generate UUID for the coupon and store it
        if is_new:
            coupon_id = str(uuid.uuid4())
            storage_service.store_new_coupon(phone_number, coupon_id, msg_id, coupon_data)   
        else:
            coupon_id = coupon_data["coupon_id"]
                                                         
        formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=is_new)                                                                    
        whatsapp.send_whatsapp_message(phone_number, formatted, is_interactive=True)
    else:
        whatsapp.send_reaction(phone_number, msg_id, "✖️")


def lambda_handler(event, context):
    print("Received event:")
    print(json.dumps(event))

    method = event.get("requestContext", {}).get("http", {}).get("method", "")

    if method == "GET":
        # Meta webhook verification
        params = event.get("queryStringParameters", {})                
        if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == os.environ.get("VERIFY_TOKEN"):
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
            if ("messages" in body["entry"][0]["changes"][0]["value"]):                
                msg = body["entry"][0]["changes"][0]["value"]["messages"][0]                
                print("Incoming:", json.dumps(msg))
                from_number = msg["from"]
                whatsapp.send_read_receipt(from_number, msg["id"])
                
                # standard message - with coupon free text
                if msg.get("type") == "text":
                    msg_text = msg["text"]["body"]            
                    if msg_text == "/list" or msg_text == "!":                            
                        show_list_of_coupons(from_number)
                    elif msg_text.startswith("/add_shared_coupon"):                                                        
                        # Extract the coupon ID from the message text
                        coupon_share_token = msg_text.split(" ")[1] 
                        # Retrieve the coupon data from the shared coupon
                        coupon_data = storage_service.get_shared_coupon(coupon_share_token)
                        
                        if coupon_data is None:
                            whatsapp.send_reaction(from_number, msg["id"], "✖️")
                            whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שהוא כבר נוצל או שהופסק השיתוף?🤔")
                        else:                                
                            # coupon found - add it to the user's coupons
                            storage_service.share_coupon_with_user(coupon_data['client_id'], coupon_data['coupon_id'], from_number)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")                            

                            # display it 
                            formatted = response_formatter.format_response(coupon_data['coupon_id'], coupon_data, is_temporary=False, is_shared=True)
                            whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
                            return {"statusCode": 200, "body": "OK"}
                    elif msg_text.startswith("/share_list"):
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
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                    elif msg_text.startswith("/cancel_sharing"):
                        storage_service.cancel_pairing(from_number)
                        whatsapp.send_reaction(from_number, msg["id"], "👍")
                    else:
                        # get user state
                        user_state = storage_service.get_user_state(from_number)

                        if (user_state is None):
                            # new user
                            first_message = True
                            user_state = "idle"
                            storage_service.set_user_state(from_number, user_state)
                        
                        if len(msg_text) > 10:
                            whatsapp.send_reaction(from_number, msg["id"], "⏳")

                            if user_state == "idle":
                                # extract fields using NLP
                                coupon_data = coupon_parser.parse_coupon_details(msg_text)
                            elif user_state.startswith("update_coupon:"):
                                coupon_id = user_state.split(":")[1]
                                print("Updating coupon:", coupon_id)
                                coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                                updated_coupon_data = coupon_parser.parse_update_request_details(coupon_data, msg_text)
                                print("Updated coupon data:", json.dumps(updated_coupon_data))
                        else:
                            coupon_data = { "valid": False }
                            updated_coupon_data = { "valid": False }

                        if user_state == "idle":
                            if not coupon_data["valid"]:
                                # clear reaction
                                whatsapp.send_reaction(from_number, msg["id"], "")

                                # check if the user has valid coupons
                                coupons = storage_service.get_user_coupons(from_number)
                                if len(coupons) > 0:                                
                                    whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=True),is_interactive=True)
                                else:
                                    whatsapp.send_whatsapp_message(from_number, response_formatter.format_welcome_message(new_user=False),is_interactive=True)
                            else:
                                response_with_coupon(coupon_data, msg["id"], from_number)
                        elif user_state.startswith("update_coupon:"):
                            if updated_coupon_data["valid"]:
                                # update the coupon
                                storage_service.update_coupon_details(coupon_data, updated_coupon_data)
                                coupon_data["valid"]=True
                                whatsapp.send_reaction(from_number, msg["id"], "👍")
                                response_with_coupon(coupon_data, msg["id"], from_number, is_new=False)
                            else:
                                whatsapp.send_reaction(from_number, msg["id"], "✖️")
                                coupon_id = user_state.split(":")[1]
                                if updated_coupon_data["examples"]:
                                    examples = "\n".join([f"- “{example}“" for example in updated_coupon_data["examples"]])
                                else:
                                    examples = "- “שנה את התוקף ל־1.8.25”\n- “עדכן את שם החנות ל־Fox”\n"
                                whatsapp.send_whatsapp_message(from_number, response_formatter.format_update_coupon_details_message(from_number, coupon_id, text=f"לא הצלחתי להבין את הבקשה לעדכון הקופון.\n\nאפשר לנסות לנסח שוב, למשל:\n{examples}\nאו לחץ ❌ כדי לבטל את העריכה."), is_interactive=True)

                elif msg.get("type") == "image":
                    # handle image 
                    whatsapp.send_reaction(from_number, msg["id"], "⏳")
                    image_id = msg["image"]["id"]
                    mime_type = msg["image"]["mime_type"]
                    image_bytes = whatsapp.download_media(image_id)
                    resized_image = image_utils.resize_image(image_bytes,max_width=1920, max_height=1920)
                    coupon_data = coupon_parser.parse_image(resized_image, mime_type)
                    response_with_coupon(coupon_data, msg["id"], from_number)
                
                elif msg.get("type") == "document":
                    # handle document
                    whatsapp.send_reaction(from_number, msg["id"], "⏳")
                    document_id = msg["document"]["id"]
                    mime_type = msg["document"]["mime_type"]
                    # check if it is a pdf
                    if mime_type == "application/pdf":                        
                        document_bytes = whatsapp.download_media(document_id)
                        coupon_data = coupon_parser.parse_pdf(document_bytes)
                        response_with_coupon(coupon_data, msg["id"], from_number)
                    else:
                        # document is not supported
                        whatsapp.send_reaction(from_number, msg["id"], "✖️")
                        whatsapp.send_whatsapp_message(from_number, "המסמך שנתת לי לא נתמך כרגע 🤷‍♂️ אפשר לשלוח טקסט, תמונה או PDF ואנסה לעזור!")

                # a button or a list item
                elif msg.get("type") == "interactive":
                    if msg["interactive"].get("type") == "button_reply":                          
                        parts = msg["interactive"]["button_reply"]["id"].split(":")
                        button_type = parts[0]
                        if (button_type == "how_to_add"):
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            whatsapp.send_whatsapp_message(from_number, "*➕ איך מוסיפים קופון?*\n\nפשוט שולחים לי את הקופון כהודעה רגילה —  \nזה יכול להיות טקסט, צילום מסך או קובץ PDF.\n\nאני אזהה את הפרטים, אראה לך מה מצאתי, ותוכל לשמור בלחיצת כפתור ✅")
                        # unused "save" buttons - remove later
                        elif (button_type == "save_coupon"):
                            coupon_id = parts[1]
                            storage_service.save_coupon_to_db(from_number, coupon_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"}
                        elif (button_type == "save_coupon_without_code"):
                            coupon_id = parts[1]
                            storage_service.save_coupon_to_db_without_code(from_number, coupon_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"}   
                        elif (button_type == "update_coupon"):
                            coupon_id = parts[1]
                            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                            if coupon_data is None:
                                whatsapp.send_reaction(from_number, msg["id"], "✖️")
                                whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שכבר ניצלת אותו?🤔")
                                return {"statusCode": 200, "body": "OK"}
                            else:
                                whatsapp.send_reaction(from_number, msg["id"], "👍")
                                whatsapp.send_whatsapp_message(from_number, response_formatter.format_update_coupon_message(coupon_data), is_interactive=True)
                            return {"statusCode": 200, "body": "OK"}
                        elif (button_type == "cancel_coupon"):
                            coupon_id = parts[1]
                            storage_service.cancel_coupon(from_number, coupon_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"} 
                        elif (button_type == "update_coupon_details"):
                            coupon_id = parts[1]
                            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                            if coupon_data is None:
                                whatsapp.send_reaction(from_number, msg["id"], "✖️")
                                whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שכבר ניצלת אותו?🤔")
                            else:
                                storage_service.set_user_state(from_number, "update_coupon:" + coupon_id)
                                whatsapp.send_whatsapp_message(from_number, response_formatter.format_update_coupon_details_message(from_number, coupon_id) , is_interactive=True)
                            return {"statusCode": 200, "body": "OK"}
                        elif button_type == "cancel_update_coupon":
                            client_id = parts[1]
                            coupon_id = parts[2]
                            storage_service.set_user_state(from_number, "idle")
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                        elif (button_type == "mark_as_used"):
                            client_id = parts[1]
                            coupon_id = parts[2]
                            storage_service.mark_coupon_as_used(client_id, coupon_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"}
                        elif (button_type == "list_coupons"):
                            show_list_of_coupons(from_number)
                        elif (button_type == "show_coupon"):
                            coupon_id = parts[1]
                            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                            if coupon_data is None:
                                whatsapp.send_reaction(from_number, msg["id"], "✖️")
                                whatsapp.send_whatsapp_message(from_number, "אופס.. זה מביך 😳. אני לא מוצא את הקופון הזה אצלי\nיכול להיות שכבר ניצלת אותו?🤔")
                                return {"statusCode": 200, "body": "OK"}
                            else:
                                whatsapp.send_reaction(from_number, msg["id"], "👍")
                                whatsapp.send_whatsapp_message(from_number, "הנה הקופון המקורי ששלחת לי", reg_msg=coupon_data["msg_id"], is_interactive=False)
                            return {"statusCode": 200, "body": "OK"}
                        elif (button_type == "share_coupon"):
                            coupon_id = parts[1]
                            coupon_data = storage_service.get_coupon_by_code(from_number, coupon_id)
                            if coupon_data.get("sharing_token") and coupon_data["sharing_token"] != "...":
                                sharing_token = coupon_data["sharing_token"]
                            else:
                                sharing_token = storage_service.generate_sharing_token(from_number, coupon_id)
                            share_payload = response_formatter.format_share_coupon_interactive(coupon_data, sharing_token)
                            whatsapp.send_whatsapp_message(from_number, share_payload, is_interactive=True)
                        elif (button_type == "cancel_share"):
                            coupon_id = parts[1]
                            storage_service.cancel_coupon_sharing(from_number, coupon_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"}
                        elif (button_type == "share_list"):
                            share_payload = response_formatter.format_share_list_interactive(from_number)
                            whatsapp.send_whatsapp_message(from_number, share_payload, is_interactive=True)
                        elif (button_type == "confirm_pair"):
                            client_id = parts[1]
                            storage_service.confirm_pairing(from_number, client_id)
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            return {"statusCode": 200, "body": "OK"}
                            
                    elif msg["interactive"].get("type") == "list_reply":
                        parts = msg["interactive"]["list_reply"]["id"].split(":")
                        reply_type = parts[0]
                        # coupon list item - return the information about the specific coupon
                        if (reply_type == "coupon"):
                            whatsapp.send_reaction(from_number, msg["id"], "👍")
                            client_id = parts[1]
                            coupon_id = parts[2]
                            coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
                            formatted = response_formatter.format_response(coupon_id, coupon_data, is_new=False, is_shared=client_id!=from_number)
                            whatsapp.send_whatsapp_message(from_number, formatted, is_interactive=True)
                            return {"statusCode": 200, "body": "OK"}

        except Exception as e:
            print("Error:", e)
            traceback.print_exc()

        return {"statusCode": 200, "body": "OK"}

def show_list_of_coupons(from_number):
    # Retrieve and send the list of saved coupons
    coupons = storage_service.get_user_coupons(from_number)
    shared_coupons = storage_service.get_shared_coupons(from_number)
    if (len(coupons) == 0):
        whatsapp.send_whatsapp_message(from_number, "*לא נמצאו קופונים שמורים 🎫*\nאפשר לשלוח פרטי קופון, תמונה או קובץ — ואני כבר אשמור את הקופון עבורך 📥😉")
    coupon_list = response_formatter.format_coupons_list_interactive(coupons, shared_coupons)
    whatsapp.send_whatsapp_message(from_number, coupon_list, is_interactive=True)