"""Business logic for coupon operations, independent of API layer."""

import uuid
import services.coupon_parser as coupon_parser
import services.storage_service as storage_service

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
                    results.append({'status': 'created', 'coupon': coupon})
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
        return {'status': 'created', 'coupon': coupon_data}

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
                    results.append({'status': 'created', 'coupon': coupon})
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
        return {'status': 'created', 'coupon': coupon_data}

def list_coupons(client_id, expiring_soon=False, include_shared=True):
    """Get list of user's coupons."""
    coupons = storage_service.get_user_coupons(client_id, expiring_soon=expiring_soon)
    shared_coupons = []
    if include_shared:
        shared_coupons = storage_service.get_shared_coupons(client_id, expiring_soon=expiring_soon)
    
    return {'coupons': coupons, 'shared_coupons': shared_coupons}

def get_coupon(client_id, coupon_id):
    """Get a specific coupon."""
    return storage_service.get_coupon_by_code(client_id, coupon_id)

def update_coupon(client_id, coupon_id, update_text):
    """Update coupon using natural language."""
    coupon_data = storage_service.get_coupon_by_code(client_id, coupon_id)
    if not coupon_data:
        return {'status': 'not_found'}
    
    updated_fields = coupon_parser.parse_update_request_details(coupon_data, update_text)
    
    if not updated_fields.get('valid'):
        return {'status': 'invalid', 'examples': updated_fields.get('examples', [])}
    
    storage_service.update_coupon_details(coupon_data, updated_fields)
    return {'status': 'updated', 'coupon': coupon_data}

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
    
    return {'coupons': matching_coupons}

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
    return {'status': 'added', 'coupon': coupon_data}
