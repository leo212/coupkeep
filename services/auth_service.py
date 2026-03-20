"""Authentication service for API key management."""

import uuid
import boto3
import config

dynamodb = boto3.resource('dynamodb')
user_state_table = dynamodb.Table(config.USER_STATE_TABLE)

def generate_api_key(client_id):
    """Generate a new API key for a user."""
    api_key = str(uuid.uuid4())
    user_state_table.update_item(
        Key={'client_id': client_id},
        UpdateExpression='SET api_key = :key',
        ExpressionAttributeValues={':key': api_key}
    )
    return api_key

def validate_api_key(api_key):
    """Validate an API key and return the associated client_id."""
    response = user_state_table.query(
        IndexName='api_key-index',
        KeyConditionExpression='api_key = :key',
        ExpressionAttributeValues={':key': api_key}
    )
    items = response.get('Items', [])
    return items[0]['client_id'] if items else None

def get_web_url(client_id):
    """Get or generate web URL with API key for a user."""
    response = user_state_table.get_item(Key={'client_id': client_id})
    item = response.get('Item')
    
    if item and item.get('api_key'):
        api_key = item['api_key']
    else:
        api_key = generate_api_key(client_id)
    
    return f"{config.WEB_BASE_URL}/{api_key}"
