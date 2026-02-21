"""
Configuration module for the WhatsApp Hook Lambda function.
Contains environment variables and constants used throughout the application.
"""

import os

# WhatsApp API configuration
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_PHONE_NUMBER = os.environ.get("WHATSAPP_PHONE_NUMBER")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# Facebook Graph API configuration
FACEBOOK_GRAPH_API_URL = "https://graph.facebook.com/v19.0"

# Gemini API configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# DynamoDB table names
COUPONS_TABLE = "Coupons"
PAIRING_TABLE = "Pairing"
USER_STATE_TABLE = "UserState"

# Message reactions
REACTION_BOOKMARK = "🔖"
REACTION_ERROR = "✖️"
REACTION_PROCESSING = "⏳"
REACTION_SUCCESS = "👍"
REACTION_NONE = ""

# User states
STATE_IDLE = "idle"
STATE_UPDATE_COUPON_PREFIX = "update_coupon:"
STATE_REGISTRATION_PENDING = "registration_pending"

# Command prefixes
CMD_LIST = "/list"
CMD_LIST_SHORT = "!"
CMD_SEARCH = "!"
CMD_ADD_SHARED_COUPON = "/add_shared_coupon"
CMD_SHARE_LIST = "/share_list"
CMD_CANCEL_SHARING = "/cancel_sharing"

# Button IDs
BUTTON_LIST_COUPONS = "list_coupons"
BUTTON_SHARE_LIST = "share_list"
BUTTON_HOW_TO_ADD = "how_to_add"
BUTTON_UPDATE_COUPON_PREFIX = "update_coupon:"
BUTTON_UPDATE_COUPON_DETAILS_PREFIX = "update_coupon_details:"
BUTTON_CANCEL_UPDATE_COUPON_PREFIX = "cancel_update_coupon:"
BUTTON_MARK_AS_USED_PREFIX = "mark_as_used:"
BUTTON_UNMARK_AS_USED_PREFIX = "unmark_as_used:"
BUTTON_CANCEL_COUPON_PREFIX = "cancel_coupon:"
BUTTON_SHARE_COUPON_PREFIX = "share_coupon:"
BUTTON_CANCEL_SHARE_PREFIX = "cancel_share:"
BUTTON_CONFIRM_PAIR_PREFIX = "confirm_pair:"
BUTTON_DECLINE_PAIR_PREFIX = "decline_pair:"
BUTTON_SHOW_COUPON_PREFIX = "show_coupon:"
BUTTON_COUPON_PREFIX = "coupon:"
BUTTON_CATEGORY_PREFIX = "category:"
BUTTON_AGREE = "agree"