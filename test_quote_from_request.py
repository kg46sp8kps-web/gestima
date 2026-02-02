#!/usr/bin/env python3
"""Debug script to test /quotes/from-request endpoint"""

import requests
import json

# Test payload (minimal valid example)
data = {
    "title": "Test Quote",
    "partner_id": None,
    "partner_data": {
        "company_name": "Test Company",
        "contact_person": None,
        "email": None,
        "phone": None,
        "ico": None,
        "dic": None,
        "is_customer": True,
        "is_supplier": False
    },
    "items": [
        {
            "part_id": None,
            "article_number": "TEST-001",
            "name": "Test Part",
            "quantity": 10,
            "notes": None
        }
    ],
    "customer_request_number": None,
    "valid_until": None,
    "notes": None,
    "discount_percent": 0.0,
    "tax_percent": 21.0
}

# Send request
try:
    response = requests.post(
        "http://localhost:8000/api/quotes/from-request",
        json=data,
        headers={"Content-Type": "application/json"}
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
