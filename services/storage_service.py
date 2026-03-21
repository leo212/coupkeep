import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import uuid
import re
from decimal import Decimal, InvalidOperation
import config

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(config.COUPONS_TABLE)
pairing_table = dynamodb.Table(config.PAIRING_TABLE)
user_state_table = dynamodb.Table(config.USER_STATE_TABLE)


def parse_amount(value):
    """Extract a numeric amount from free-form value strings like '100₪', '$50', or '100.5 ש"ח'."""
    if value is None:
        return None

    if isinstance(value, (int, float, Decimal)):
        return float(value)

    # Remove currency symbols and common Hebrew currency strings to isolate the number
    text = str(value).strip().replace(",", ".")
    text = text.replace("₪", "").replace("$", "").replace("ש\"ח", "").replace("שח", "")
    
    # Match first floating point number
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def to_decimal(value, default=Decimal('0')):
    """Convert numeric-like input to Decimal for DynamoDB writes."""
    if value is None:
        return default

    if isinstance(value, Decimal):
        return value

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, float):
        return Decimal(str(value))

    amount = parse_amount(value)
    if amount is None:
        return default

    try:
        return Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return default

def store_new_coupon(client_id, coupon_id, msg_id, coupon_data):
    """Store a new coupon in the database and share it with paired users if applicable."""
    item = {
        'client_id': client_id,
        'coupon_id': coupon_id,
        'msg_id': msg_id,
        'store': coupon_data.get('store'),
        'coupon_code': coupon_data.get('coupon_code'),
        'expiration_date': coupon_data.get('expiration_date'),
        'discount_value': coupon_data.get('discount_value'),
        'value': coupon_data.get('value'),
        'terms': coupon_data.get('terms_and_conditions'),
        'url': coupon_data.get('url'),
        'category': coupon_data.get('category'),
        'misc': coupon_data.get('misc'),
        'coupon_status': 'unused',
        'used': 0,
        'timestamp': datetime.now().isoformat()
    }

    table.put_item(Item=item)

    # check if the user has a pairing
    pairing_partner = pairing_table.get_item(Key={'client_id': client_id}).get("Item")
    if (pairing_partner is not None):
        # share the coupon with the partner
        share_coupon_with_user(client_id, coupon_id, pairing_partner.get("shared_with_client_id"))

def update_coupon_details(coupon_data, updated_fields):
    """Update specific fields of a coupon."""
    if not updated_fields:
        print("No fields to update.")
        return

    update_expressions = []
    expression_attribute_values = {}
    expression_attribute_names = {}

    # Map of DynamoDB field names (with aliases where needed) to updated_fields keys
    field_mapping = {
        '#store': 'store',
        'coupon_code': 'coupon_code',
        'expiration_date': 'expiration_date',
        'discount_value': 'discount_value',
        '#val': 'value',
        'terms': 'terms_and_conditions',
        '#url': 'url',
        'misc': 'misc',
        'category': 'category',
        'used': 'used'
    }

    # Full mapping of aliases to real DynamoDB attribute names
    full_attribute_name_mapping = {
        '#store': 'store',
        '#val': 'value',
        '#url': 'url'
    }

    for db_field, update_key in field_mapping.items():
        if update_key in updated_fields:
            placeholder = f":{db_field.strip('#')}"
            update_expressions.append(f"{db_field} = {placeholder}")
            field_value = updated_fields[update_key]
            if update_key == 'used':
                field_value = to_decimal(field_value)

            expression_attribute_values[placeholder] = field_value
            coupon_data[update_key] = field_value

            # If the db_field is an alias (starts with #), include it in the attribute names
            if db_field.startswith('#'):
                expression_attribute_names[db_field] = full_attribute_name_mapping[db_field]

    if not update_expressions:
        print("No matching fields to update.")
        return

    update_expression = "SET " + ", ".join(update_expressions)

    update_params = {
        'Key': {
            'client_id': coupon_data.get('client_id'),
            'coupon_id': coupon_data.get('coupon_id')
        },
        'UpdateExpression': update_expression,
        'ExpressionAttributeValues': expression_attribute_values,
    }

    if expression_attribute_names:
        update_params['ExpressionAttributeNames'] = expression_attribute_names

    table.update_item(**update_params)

def mark_coupon_as_used(client_id, coupon_id):
    """Mark a coupon as used."""
    coupon = get_coupon_by_code(client_id, coupon_id)
    full_used = parse_amount(coupon.get('value')) if coupon else None

    expression = 'SET coupon_status = :val, used_timestamp = :timestamp'
    expression_values = {':val': "used", ':timestamp': datetime.now().isoformat()}
    if full_used is not None:
        expression += ', used = :used'
        expression_values[':used'] = to_decimal(full_used)

    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression=expression,
        ExpressionAttributeValues=expression_values)
    print("Coupon marked as used:", coupon_id)

def get_user_coupons(client_id, expiring_soon=False, days=30, include_used=False):
    """Get all unused coupons for a user. Optionally filter for expiring soon."""
    if include_used:
        filter_expr = None
    else:
        filter_expr = Attr('coupon_status').eq('unused')
    
    if expiring_soon:
        now = datetime.now()
        future = now + timedelta(days=days)
        expiring_filter = Attr('expiration_date').gt(now.isoformat()) & Attr('expiration_date').lte(future.isoformat())
        filter_expr = filter_expr & expiring_filter if filter_expr else expiring_filter
    
    query_params = {'KeyConditionExpression': Key('client_id').eq(client_id)}
    if filter_expr:
        query_params['FilterExpression'] = filter_expr
    
    response = table.query(**query_params)
    return response.get('Items', [])

def find_coupon_by_code(client_id, coupon_code):
    """Find a coupon by its code for a specific user."""
    response = table.query(
        KeyConditionExpression=Key('client_id').eq(client_id),
        FilterExpression=Attr('coupon_code').eq(coupon_code)
    )
    items = response.get('Items', [])
    return items[0] if items else None

def unmark_coupon_as_used(client_id, coupon_id):
    """Unmark a coupon as used."""
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET coupon_status = :val, used = :used REMOVE used_timestamp',
        ExpressionAttributeValues={':val': 'unused', ':used': 0}
    )
    print("Coupon unmarked as used:", coupon_id)


def update_coupon_used_value(client_id, coupon_id, amount):
    """Increase coupon used amount by `amount`, clamped to coupon value if numeric."""
    coupon = get_coupon_by_code(client_id, coupon_id)
    if not coupon:
        return None

    current_used = parse_amount(coupon.get('used')) or 0.0
    added = parse_amount(amount) or 0.0
    new_used = current_used + max(added, 0.0)

    # Check value field which might have currency symbols
    value_amount = parse_amount(coupon.get('value'))
    if value_amount is not None:
        new_used = min(new_used, value_amount)

    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET used = :used',
        ExpressionAttributeValues={':used': to_decimal(new_used)}
    )

    coupon['used'] = new_used
    return coupon

def get_coupon_by_code(client_id, coupon_id):
    """Get a specific coupon by its ID, including shared coupons."""
    print("Getting coupon by code:", client_id, coupon_id)
    # First try to get the user's own coupon
    response = table.get_item(
        Key={"client_id": client_id, "coupon_id": coupon_id}
    )
    coupon = response.get("Item")
    
    if coupon:
        return coupon
    
    # If not found, check if it's a shared coupon
    response = table.query(
        IndexName='shared_with-index',
        KeyConditionExpression=Key('shared_with').eq(client_id),
        FilterExpression=Attr('coupon_id').eq(coupon_id)
    )
    items = response.get('Items', [])
    return items[0] if items else None

def get_shared_coupon(share_token):
    """Get a coupon that has been shared using a token."""
    # make sure user won't get previously shared coupons
    if (share_token == "..."):
        return None
    
    print("Getting coupon by share token:", share_token)
    response = table.query(
        IndexName='sharing_token-index',
        KeyConditionExpression=Key('sharing_token').eq(share_token)
    )
    items = response.get("Items")
    if (len(items) == 0):
        return None
    else:
        return items[0]

def generate_sharing_token(client_id, coupon_id):
    """Generate a unique token for sharing a coupon."""
    sharing_token = f"{uuid.uuid4().hex[:8].upper()}"
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET sharing_token = :val',
        ExpressionAttributeValues={':val': sharing_token}
    )
    print("Sharing token generated:", sharing_token)
    return sharing_token

def share_coupon_with_user(client_id, coupon_id, shared_with_client_id):
    """Share a coupon with another user."""
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET shared_with = :shared_with, sharing_token = :token',
        ExpressionAttributeValues={':shared_with': shared_with_client_id, ':token': "..."}
    )
    print("Coupon shared with user:", client_id, coupon_id, shared_with_client_id)

def cancel_coupon_sharing(client_id, coupon_id):
    """Cancel sharing of a coupon."""
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET shared_with = :shared_with, sharing_token = :token',
        ExpressionAttributeValues={':shared_with': "...", ':token': "..."}
    )
    print("Coupon sharing cancelled:", coupon_id, client_id)

def get_shared_coupons(client_id, expiring_soon=False, days=30, include_used=False):
    """Get all coupons shared with a user. Optionally filter for expiring soon."""
    filter_expr = None if include_used else Attr('coupon_status').eq('unused')
    
    if expiring_soon:
        now = datetime.now()
        future = now + timedelta(days=days)
        expiring_filter = Attr('expiration_date').gt(now.isoformat()) & Attr('expiration_date').lte(future.isoformat())
        filter_expr = filter_expr & expiring_filter if filter_expr else expiring_filter
    
    query_params = {
        'IndexName': 'shared_with-index',
        'KeyConditionExpression': Key('shared_with').eq(client_id)
    }
    if filter_expr:
        query_params['FilterExpression'] = filter_expr

    response = table.query(**query_params)
    items = response.get('Items', [])
    return items

def confirm_pairing(my_client_id, his_client_id):
    """Confirm pairing between two users for coupon sharing."""
    pairing_table.update_item(
        Key={'client_id': my_client_id},
        UpdateExpression='SET shared_with_client_id = :shared_with',
        ExpressionAttributeValues={':shared_with': his_client_id}
    )
    print("Pairing confirmed:", my_client_id, his_client_id)
    
    # update all of the coupons to be shared with the new partner
    all_coupons = get_user_coupons(my_client_id)
    for coupon in all_coupons:
        share_coupon_with_user(my_client_id, coupon.get("coupon_id"), his_client_id)

def cancel_pairing(client_id):
    """Cancel pairing between users."""
    # get pairing partner
    pairing_partner = pairing_table.get_item(Key={'client_id': client_id}).get("Item")
    if (pairing_partner is not None):
        partner_id = pairing_partner.get("shared_with_client_id")

        # cancel pairing with the partner
        pairing_table.delete_item(Key={'client_id': client_id})
        pairing_table.delete_item(Key={'client_id': partner_id})
    
        print("Pairing cancelled:", client_id)
        
        # update all of the coupons to be shared with the new partner
        all_coupons = get_user_coupons(client_id)
        for coupon in all_coupons:
            cancel_coupon_sharing(client_id, coupon.get("coupon_id"))

        # update all of the coupons to be shared with the new partner
        all_coupons = get_user_coupons(partner_id)
        for coupon in all_coupons:
            cancel_coupon_sharing(partner_id, coupon.get("coupon_id"))

def cancel_coupon(client_id, coupon_id):
    """Cancel a coupon."""
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET coupon_status = :val',
        ExpressionAttributeValues={':val': "canceled"})
    print("Coupon canceled:", coupon_id)

def set_user_state(client_id, updated_state):
    """Set or update a user's state."""
    if (get_user_state(client_id) is None):
        user_state_table.put_item(Item={'client_id': client_id, 'user_state': updated_state})
        print("User state created:", client_id, updated_state)
        return
    user_state_table.update_item(
        Key={'client_id': client_id},
        UpdateExpression='SET user_state = :user_state',
        ExpressionAttributeValues={':user_state': updated_state}
    )
    print("User state updated:", client_id, updated_state)

def get_user_state(client_id):
    """Get a user's current state."""
    response = user_state_table.get_item(Key={'client_id': client_id})
    if response.get("Item") is None:
        return None
    return response.get("Item").get("user_state")

def save_coupon_to_db_without_code(client_id, coupon_id):
    """Save a coupon without a code."""
    table.update_item(
        Key={'client_id': client_id, 'coupon_id': coupon_id},
        UpdateExpression='SET coupon_status = :val, coupon_code = :code, used = :used',
        ExpressionAttributeValues={':val': "unused", ':code' : None, ':used': 0})
    print("Coupon saved:", coupon_id)