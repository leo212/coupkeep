"""Business logic for coupon operations, independent of API layer."""

import uuid
import json
from decimal import Decimal
import services.coupon_parser as coupon_parser
import services.storage_service as storage_service

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def add_remaining_field(coupon):
    """Add a computed remaining value (value-used) when value is numeric."""
    if not coupon:
        return coupon

    coupon_copy = dict(coupon)
    used = storage_service.parse_amount(coupon_copy.get('used')) or 0.0
    coupon_copy['used'] = used

    value_amount = storage_service.parse_amount(coupon_copy.get('value'))
    if value_amount is not None:
        coupon_copy['remaining'] = max(value_amount - used, 0.0)

    return coupon_copy

def create_coupon_from_text(client_id, text):
    """Parse and create coupon(s) from text."""
    coupon_data = coupon_parser.parse_coupon_details(text)
    
    if isinstance(coupon_data, list):
        results = []
        for coupon in coupon_data:
            if coupon["valid"]:
                existing = None
                if coupon.get('coupon_code'):
                    existing = storage_service.find_coupon_by_code(client_id, coupon['coupon_code'])
                
                if existing:
                    results.append({'status': 'duplicate', 'coupon': existing})
                else:
                    coupon_id = str(uuid.uuid4())
                    storage_service.store_new_coupon(client_id, coupon_id, None, coupon)
                    coupon['coupon_id'] = coupon_id
                    coupon['used'] = 0
                    results.append({'status': 'created', 'coupon': add_remaining_field(coupon)})
        return results
    else:
        if not coupon_data["valid"]:
            return {'status': 'invalid', 'coupon': coupon_data}
        
        existing = None
        if coupon_data.get('coupon_code'):
            existing = storage_service.find_coupon_by_code(client_id, coupon_data['coupon_code'])
        
        if existing:
            return {'status': 'duplicate', 'coupon': existing}
        
        coupon_id = str(uuid.uuid4())
        storage_service.store_new_coupon(client_id, coupon_id, None, coupon_data)
        coupon_data['coupon_id'] = coupon_id
        coupon_data['used'] = 0
        return {'status': 'created', 'coupon': add_remaining_field(coupon_data)}

def create_coupon_from_image(client_id, image_bytes):
    """Parse and create coupon(s) from image."""
    coupon_data = coupon_parser.parse_image(image_bytes)
    
    if isinstance(coupon_data, list):
        results = []
        for coupon in coupon_data:
            if coupon["valid"]:
                existing = None
                if coupon.get('coupon_code'):
                    existing = storage_service.find_coupon_by_code(client_id, coupon['coupon_code'])
                
                if existing:
                    results.append({'status': 'duplicate', 'coupon': existing})
                else:
                    coupon_id = str(uuid.uuid4())
                    storage_service.store_new_coupon(client_id, coupon_id, None, coupon)
                    coupon['coupon_id'] = coupon_id
                    coupon['used'] = 0
                    results.append({'status': 'created', 'coupon': add_remaining_field(coupon)})
        return results
    else:
        if not coupon_data["valid"]:
            return {'status': 'invalid', 'coupon': coupon_data}
        
        existing = None
        if coupon_data.get('coupon_code'):
            existing = storage_service.find_coupon_by_code(client_id, coupon_data['coupon_code'])
        
        if existing:
            return {'status': 'duplicate', 'coupon': existing}
        
        coupon_id = str(uuid.uuid4())
        storage_service.store_new_coupon(client_id, coupon_id, None, coupon_data)
        coupon_data['coupon_id'] = coupon_id
        coupon_data['used'] = 0
        return {'status': 'created', 'coupon': add_remaining_field(coupon_data)}

def list_coupons(client_id, expiring_soon=False, include_shared=True, include_used=False):
    """Get list of user's coupons."""
    coupons = storage_service.get_user_coupons(client_id, expiring_soon=expiring_soon, include_used=include_used)
    shared_coupons = []
    if include_shared:
        shared_coupons = storage_service.get_shared_coupons(client_id, expiring_soon=expiring_soon, include_used=include_used)
    
    return {
        'coupons': [add_remaining_field(c) for c in coupons],
        'shared_coupons': [add_remaining_field(c) for c in shared_coupons]
    }

def get_coupon(client_id, coupon_id, include_example=False):
    """Get a specific coupon."""
    coupon = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon:
        return None
    result = add_remaining_field(coupon)
    if include_example:
        result['update_example'] = coupon_parser.generate_update_example(coupon)
    return result

def update_coupon(client_id, coupon_id, update_text):
    """Update coupon using natural language with disambiguation support."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    parse_result = coupon_parser.parse_update_request_details(coupon_data, update_text)
    
    status = parse_result.get('status')
    if status == 'ambiguous':
        return {
            'status': 'ambiguous',
            'options': parse_result.get('options', []),
            'message': parse_result.get('message', 'לא הבנתי למה הכוונה בדיוק, הנה כמה אפשרויות:')
        }
    
    updated_fields = parse_result.get('update_fields', {})
    
    # Process 'used' field if present to ensure it's a number
    if 'used' in updated_fields:
        parsed_used = storage_service.parse_amount(updated_fields['used'])
        updated_fields['used'] = parsed_used if parsed_used is not None else 0

    storage_service.update_coupon_details(coupon_data, updated_fields)
    
    return {
        'status': 'updated', 
        'coupon': add_remaining_field(coupon_data),
        'summary': parse_result.get('summary', 'הקופון עודכן בהצלחה.')
    }


def update_fields(client_id, coupon_id, fields):
    """Update specific coupon fields directly."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    # Process 'used' if present to ensure it's a number
    if 'used' in fields:
        parsed_used = storage_service.parse_amount(fields['used'])
        fields['used'] = parsed_used if parsed_used is not None else 0

    storage_service.update_coupon_details(coupon_data, fields)
    return {'status': 'updated', 'coupon': add_remaining_field(coupon_data)}

def add_coupon_usage(client_id, coupon_id, amount):
    """Increase a coupon usage amount without automatically marking as used."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}

    updated = storage_service.update_coupon_used_value(coupon_data['client_id'], coupon_id, amount)
    if not updated:
        return {'status': 'not_found'}

    return {'status': 'updated', 'coupon': add_remaining_field(updated)}

def mark_coupon_used(client_id, coupon_id):
    """Mark a coupon as used."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    storage_service.mark_coupon_as_used(coupon_data['client_id'], coupon_id)
    return {'status': 'marked_used'}

def unmark_coupon_used(client_id, coupon_id):
    """Unmark a coupon as used."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    storage_service.unmark_coupon_as_used(coupon_data['client_id'], coupon_id)
    return {'status': 'unmarked'}

def delete_coupon(client_id, coupon_id):
    """Delete a coupon."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    storage_service.cancel_coupon(coupon_data['client_id'], coupon_id)
    return {'status': 'deleted'}

def search_coupons(client_id, query):
    """Search coupons."""
    coupons = storage_service.get_user_coupons(client_id)
    if not coupons:
        return {'coupons': []}
    
    search_result = coupon_parser.search_coupons(coupons, query)
    matching_ids = search_result.get('coupon_ids', [])
    matching_coupons = [c for c in coupons if c['coupon_id'] in matching_ids]
    
    return {'coupons': [add_remaining_field(c) for c in matching_coupons]}

def share_coupon(client_id, coupon_id):
    """Generate sharing token for a coupon."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    token = storage_service.generate_sharing_token(coupon_data['client_id'], coupon_id)
    return {'status': 'shared', 'token': token}

def add_shared_coupon(client_id, share_token):
    """Add a shared coupon to user's collection."""
    coupon_data = storage_service.get_shared_coupon(share_token)
    if not coupon_data:
        return {'status': 'not_found'}
    
    storage_service.share_coupon_with_user(coupon_data['client_id'], coupon_data['coupon_id'], client_id)
    return {'status': 'added', 'coupon': add_remaining_field(coupon_data)}
