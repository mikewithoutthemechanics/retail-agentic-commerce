# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for checkout session processing."""

from typing import Any

from src.merchant.domain.checkout.models import (
    BuyerInput,
    CheckoutSessionResponse,
    LineItem,
)
from src.merchant.protocols.acp.api.schemas.checkout import CompleteCheckoutRequest as ACPCompleteCheckoutRequest
from src.merchant.protocols.ucp.api.schemas.checkout import UCPCompleteCheckoutRequest


def extract_customer_name_from_acp_request(
    request: ACPCompleteCheckoutRequest,
    session_response: CheckoutSessionResponse,
) -> str:
    """Extract customer name from ACP complete checkout request with priority fallback.

    Priority order:
    1. billing_address.name from payment_data (user's actual input)
    2. buyer.first_name from request
    3. buyer.first_name from session response
    4. "Customer" (default fallback)

    Args:
        request: The ACP complete checkout request
        session_response: The checkout session response from service layer

    Returns:
        Customer first name for use in notifications
    """
    customer_name = "Customer"
    billing_name = None

    # 1. Try billing address name from payment data (highest priority - user's actual input)
    if (
        request.payment_data
        and request.payment_data.billing_address
        and request.payment_data.billing_address.name
    ):
        # Extract first name from billing address (e.g., "John Doe" -> "John")
        billing_name = request.payment_data.billing_address.name.strip()
        name_parts = billing_name.split()
        if name_parts:
            customer_name = name_parts[0]

    # 2. Try buyer first name from request
    elif request.buyer and request.buyer.first_name:
        customer_name = request.buyer.first_name

    # 3. Try buyer first name from session response
    elif session_response.buyer and session_response.buyer.first_name:
        customer_name = session_response.buyer.first_name

    # 4. Default to "Customer" (already set above)

    return customer_name


def extract_customer_name_from_ucp_request(
    request: UCPCompleteCheckoutRequest,
    session_response: CheckoutSessionResponse,
) -> str:
    """Extract customer name from UCP complete checkout request with priority fallback.

    Priority order:
    1. billing_address.name from payment data (user's actual input)
    2. buyer.first_name from request
    3. buyer.first_name from session response
    4. "Customer" (default fallback)

    Args:
        request: The UCP complete checkout request
        session_response: The checkout session response from service layer

    Returns:
        Customer first name for use in notifications
    """
    customer_name = "Customer"
    billing_name = None

    # 1. Try billing address name from payment data (highest priority - user's actual input)
    if (
        request.payment
        and request.payment.instruments
        and len(request.payment.instruments) > 0
        and request.payment.instruments[0].credential
        and hasattr(request.payment.instriments[0].credential, 'billing_address')
        and request.payment.instruments[0].credential.billing_address
        and request.payment.instruments[0].credential.billing_address.name
    ):
        # Extract first name from billing address (e.g., "John Doe" -> "John")
        billing_name = request.payment.instruments[0].credential.billing_address.name.strip()
        name_parts = billing_name.split()
        if name_parts:
            customer_name = name_parts[0]

    # 2. Try buyer first name from request
    elif request.buyer and request.buyer.first_name:
        customer_name = request.buyer.first_name

    # 3. Try buyer first name from session response
    elif session_response.buyer and session_response.buyer.first_name:
        customer_name = session_response.buyer.first_name

    # 4. Default to "Customer" (already set above)

    return customer_name


def extract_items_from_line_items(
    line_items: list[Any] | None
) -> list[dict[str, int]]:
    """Extract items list from line items for webhook payloads.

    Args:
        line_items: List of line items from checkout session

    Returns:
        List of dictionaries with 'name' and 'quantity' keys
    """
    items = []
    if line_items:
        for line_item in line_items:
            # Handle different line item types (ACP vs domain models)
            if hasattr(line_item, 'name'):
                # ACP line item format
                item_name = line_item.name or line_item.item.id
                quantity = line_item.item.quantity
            elif hasattr(line_item, 'item') and hasattr(line_item.item, 'name'):
                # Domain model format
                item_name = line_item.item.name or line_item.item.id
                quantity = line_item.item.quantity
            else:
                # Fallback
                item_name = getattr(line_item, 'name', 'unknown')
                quantity = getattr(line_item, 'quantity', 1)

            items.append({"name": item_name, "quantity": quantity})

    if not items:
        items = [{"name": "your order", "quantity": 1}]

    return items