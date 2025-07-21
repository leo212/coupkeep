# WhatsApp Coupon Management Bot

A WhatsApp bot for managing coupons and vouchers, built on AWS Lambda.

## Features

- Extract coupon details from text, images, and PDF files using AI
- Store and manage coupons in DynamoDB
- Share coupons with other users
- Update coupon details
- Mark coupons as used
- Support for Hebrew language

## Architecture

The application is built using:

- AWS Lambda for serverless execution
- DynamoDB for data storage
- WhatsApp Business API for messaging
- Google Gemini API for AI-powered coupon extraction

## Project Structure

```
CKeepWhatsAppHook/
├── lambda_function.py     # Main Lambda handler
├── config.py              # Configuration and constants
├── services/              # Core services
│   ├── __init__.py
│   ├── coupon_parser.py   # AI-powered coupon extraction
│   ├── storage_service.py # DynamoDB interactions
│   └── whatsapp.py        # WhatsApp API interactions
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── image_utils.py     # Image processing utilities
│   └── response_formatter.py # Format WhatsApp responses
└── requirements.txt       # Python dependencies
```

## Environment Variables

The following environment variables need to be set:

- `WHATSAPP_TOKEN`: WhatsApp Business API token
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp Business phone number ID
- `WHATSAPP_PHONE_NUMBER`: WhatsApp Business phone number
- `VERIFY_TOKEN`: Token for WhatsApp webhook verification
- `GEMINI_API_KEY`: Google Gemini API key

## DynamoDB Tables

The application uses the following DynamoDB tables:

- `Coupons`: Stores coupon information
- `Pairing`: Stores user pairing information for sharing coupons
- `UserState`: Stores user state information for multi-step interactions

## Setup and Deployment

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up the required environment variables
4. Deploy to AWS Lambda
5. Configure the WhatsApp Business API webhook to point to the Lambda function

## Usage

Users can interact with the bot through WhatsApp by:

- Sending coupon text or images
- Using commands like `/list` to view saved coupons
- Clicking interactive buttons to manage coupons
- Sharing coupons with other users