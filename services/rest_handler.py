"""REST API handlers for coupon management."""

import json
import base64
from decimal import Decimal
import services.auth_service as auth_service
import services.coupon_service as coupon_service

def decimal_default(obj):
    """Convert Decimal to int or float for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def make_json_response(status_code, body_obj):
    """Build a lambda HTTP response with JSON content-type header.

    `body_obj` may be a string (already JSON) or a Python object to serialize.
    """
    if isinstance(body_obj, str):
        body_str = body_obj
    else:
        body_str = json.dumps(body_obj, ensure_ascii=False, default=decimal_default)
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': '*'
        },
        'body': body_str
    }

def validate_request(event):
    """Validate API key from request."""
    headers = event.get('headers', {})
    api_key = headers.get('x-api-key') or headers.get('X-Api-Key')
    
    if not api_key:
        return None, make_json_response(401, {'error': 'Missing API key'})
    
    client_id = auth_service.validate_api_key(api_key)
    if not client_id:
        return None, make_json_response(403, {'error': 'Invalid API key'})
    
    return client_id, None

def handle_rest_api(event):
    """Route REST API requests."""
    path = event.get('rawPath', '')
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    
    client_id, error = validate_request(event)
    if error:
        return error
    
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])
    
    if path == '/default/api/coupons' and method == 'GET':
        return get_coupons(client_id, event.get('queryStringParameters', {}))
    elif path == '/default/api/coupons' and method == 'POST':
        return create_coupon(client_id, body)
    elif path.startswith('/default/api/coupons/') and method == 'GET':
        coupon_id = path.split('/')[-1]
        return get_coupon(client_id, coupon_id, event)
    elif path.startswith('/default/api/coupons/') and method == 'PUT':
        coupon_id = path.split('/')[-1]
        return update_coupon(client_id, coupon_id, body)
    elif path.startswith('/default/api/coupons/') and method == 'DELETE':
        coupon_id = path.split('/')[-1]
        return delete_coupon(client_id, coupon_id)
    elif path == '/default/api/coupons/search' and method == 'POST':
        return search_coupons_api(client_id, body)
    elif path.startswith('/default/api/coupons/') and path.endswith('/mark-used') and method == 'POST':
        coupon_id = path.split('/')[-2]
        return mark_used(client_id, coupon_id)
    elif path.startswith('/default/api/coupons/') and path.endswith('/use') and method == 'POST':
        coupon_id = path.split('/')[-2]
        return use_coupon_amount(client_id, coupon_id, body)
    elif path.startswith('/default/api/coupons/') and path.endswith('/unmark-used') and method == 'POST':
        coupon_id = path.split('/')[-2]
        return unmark_used(client_id, coupon_id)
    elif path.startswith('/default/api/coupons/') and path.endswith('/share') and method == 'POST':
        coupon_id = path.split('/')[-2]
        return share_coupon_api(client_id, coupon_id)
    elif path == '/default/api/coupons/shared' and method == 'POST':
        return add_shared_coupon_api(client_id, body)
    
    return make_json_response(404, {'error': 'Not found'})

def get_coupons(client_id, params):
    params = params or {}
    result = coupon_service.list_coupons(
        client_id,
        params.get('expiring_soon') == 'true',
        params.get('include_shared', 'true') == 'true',
        params.get('include_used', 'false') == 'true'
    )
    return make_json_response(200, result)

def create_coupon(client_id, body):
    if 'text' in body:
        result = coupon_service.create_coupon_from_text(client_id, body['text'])
    elif 'image' in body:
        result = coupon_service.create_coupon_from_image(client_id, base64.b64decode(body['image']))
    else:
        return make_json_response(400, {'error': 'Missing text or image'})
    status = 201 if isinstance(result, dict) and result.get('status') == 'created' else 200
    return make_json_response(status, result)

def get_coupon(client_id, coupon_id, event=None):
    include_example = False
    if event and event.get('queryStringParameters'):
        include_example = event['queryStringParameters'].get('include_example') == 'true'
    
    coupon = coupon_service.get_coupon(client_id, coupon_id, include_example=include_example)
    if not coupon:
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, coupon)

def update_coupon(client_id, coupon_id, body):
    if 'fields' in body:
        # Direct field update (used for disambiguation options)
        result = coupon_service.update_fields(client_id, coupon_id, body['fields'])
    elif 'text' in body:
        # Natural language update
        result = coupon_service.update_coupon(client_id, coupon_id, body['text'])
    else:
        return make_json_response(400, {'error': 'Missing text or fields'})
    
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    elif result['status'] in ['invalid', 'ambiguous']:
        return make_json_response(400, result)
    return make_json_response(200, result)

def delete_coupon(client_id, coupon_id):
    result = coupon_service.delete_coupon(client_id, coupon_id)
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, result)

def search_coupons_api(client_id, body):
    if 'query' not in body:
        return make_json_response(400, {'error': 'Missing query field'})
    result = coupon_service.search_coupons(client_id, body['query'])
    return make_json_response(200, result)

def mark_used(client_id, coupon_id):
    result = coupon_service.mark_coupon_used(client_id, coupon_id)
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, result)

def unmark_used(client_id, coupon_id):
    result = coupon_service.unmark_coupon_used(client_id, coupon_id)
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, result)


def use_coupon_amount(client_id, coupon_id, body):
    amount = body.get('amount')
    if amount is None:
        return make_json_response(400, {'error': 'Missing amount field'})

    result = coupon_service.add_coupon_usage(client_id, coupon_id, amount)
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, result)

def share_coupon_api(client_id, coupon_id):
    result = coupon_service.share_coupon(client_id, coupon_id)
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Coupon not found'})
    return make_json_response(200, result)

def add_shared_coupon_api(client_id, body):
    if 'token' not in body:
        return make_json_response(400, {'error': 'Missing token field'})
    result = coupon_service.add_shared_coupon(client_id, body['token'])
    if result['status'] == 'not_found':
        return make_json_response(404, {'error': 'Shared coupon not found'})
    return make_json_response(200, result)
