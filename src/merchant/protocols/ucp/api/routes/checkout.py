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

"""Checkout session API routes implementing the Universal Commerce Protocol."""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from src.merchant.api.dependencies import verify_api_key
from src.merchant.db.database import get_session
from src.merchant.domain.checkout.service import (
    InvalidStateTransitionError,
    ProductNotFoundError,
    SessionNotFoundError,
    cancel_checkout_session,
    complete_checkout_session_from_data,
    create_checkout_session_from_data,
    get_checkout_session,
    update_checkout_session_from_data,
)
from src.merchant.domain.checkout.utils import (
    extract_customer_name_from_ucp_request,
    extract_items_from_line_items,
)
from src.merchant.protocols.ucp.api.schemas.checkout import (
    UCPCapabilityVersion,
    UCPBusinessProfile,
    UCPBuyerInput,
    UCPCheckoutResponse,
    UCPCompleteCheckoutRequest,
    UCPCreateCheckoutRequest,
    UCPErrorResponse,
    UCPErrorResponseCodeEnum,
    UCPErrorTypeEnum,
    UCPPaymentHandler,
    UCPUpdateCheckoutRequest,
)
from src.merchant.protocols.ucp.services.negotiation import (
    build_business_profile,
    compute_capability_intersection,
    fetch_platform_profile,
    parse_ucp_agent_header,
    transform_to_ucp_response,
)
from src.merchant.protocols.ucp.services.post_purchase_webhook import (
    trigger_post_purchase_flow_ucp,
)
from src.merchant.services.post_purchase import OrderItem

router = APIRouter(
    tags=["ucp"],
    dependencies=[Depends(verify_api_key)],
)


def _handle_ucp_error(error: Exception) -> HTTPException:
    """Convert service layer errors to UCP HTTP exceptions.

    Args:
        error: Service layer exception.

    Returns:
        HTTPException with appropriate status code and UCP error response.
    """
    if isinstance(error, SessionNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.NOT_FOUND,
                code=UCPErrorResponseCodeEnum.SESSION_NOT_FOUND,
                message=error.message,
            ).model_dump(),
        )

    if isinstance(error, ProductNotFoundError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INVALID_REQUEST,
                code=UCPErrorResponseCodeEnum.PRODUCT_NOT_FOUND,
                message=error.message,
            ).model_dump(),
        )

    if isinstance(error, InvalidStateTransitionError):
        return HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INVALID_REQUEST,
                code=UCPErrorResponseCodeEnum.INVALID_STATUS_TRANSITION,
                message=error.message,
            ).model_dump(),
        )

    # For any other error, return a generic internal error
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=UCPErrorResponse(
            type=UCPErrorTypeEnum.INTERNAL_ERROR,
            code=UCPErrorResponseCodeEnum.INTERNAL_ERROR,
            message="Internal server error",
        ).model_dump(),
    )


async def _get_negotiation_context(
    request: Request,
) -> tuple[
    dict[str, list[UCPCapabilityVersion]],
    dict[str, list[UCPPaymentHandler]] | None,
    str | None,
]:
    """Extract UCP-Agent header and perform capability negotiation.

    Returns:
        Tuple of (negotiated_capabilities, payment_handlers, order_webhook_url)
    """
    # Get UCP-Agent header (required for UCP)
    ucp_agent_header = request.headers.get("UCP-Agent")
    if not ucp_agent_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INVALID_REQUEST,
                code=UCPErrorResponseCodeEnum.MISSING_UCP_AGENT_HEADER,
                message="UCP-Agent header is required",
            ).model_dump(),
        )

    # Parse the UCP-Agent header to get the platform profile URL
    try:
        profile_url = parse_ucp_agent_header(ucp_agent_header)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INVALID_REQUEST,
                code=UCPErrorResponseCodeEnum.INVALID_UCP_AGENT_HEADER,
                message=str(e),
            ).model_dump(),
        )

    # Fetch the platform profile
    try:
        platform_profile = await fetch_platform_profile(profile_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INTERNAL_ERROR,
                code=UCPErrorResponseCodeEnum.UNABLE_TO_FETCH_PLATFORM_PROFILE,
                message=f"Unable to fetch platform profile: {str(e)}",
            ).model_dump(),
        )

    # Perform capability negotiation
    try:
        business_profile = build_business_profile(
            request_base_url=str(request.base_url).rstrip("/")
        )
        negotiated = compute_capability_intersection(business_profile, platform_profile)
        if not negotiated:
            raise ValueError("No compatible capabilities found")

        # Get payment handlers and order webhook URL from negotiated profile
        payment_handlers = business_profile.ucp.payment_handlers
        order_webhook_url = None  # Would be extracted from platform profile in full implementation

        return negotiated, payment_handlers, order_webhook_url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UCPErrorResponse(
                type=UCPErrorTypeEnum.INVALID_REQUEST,
                code=UCPErrorResponseCodeEnum.UCP_NEGOTIATION_FAILED,
                message=f"UCP capability negotiation failed: {str(e)}",
            ).model_dump(),
        )


@router.post(
    "/checkout-sessions",
    response_model=UCPCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create UCP Checkout Session",
    description="Create a new checkout session with UCP protocol.",
)
async def create_ucp_checkout(
    request: Request,
    checkout_request: UCPCreateCheckoutRequest,
    db: Session = Depends(get_session),
) -> UCPCheckoutResponse:
    """Create a new UCP checkout session.

    Args:
        request: The HTTP request (for UCP-Agent header and base URL).
        checkout_request: The UCP checkout creation request.
        db: Database session.

    Returns:
        UCPCheckoutResponse with the new session.

    Raises:
        HTTPException: 400 if invalid request, 500 if internal error.
    """
    try:
        # Perform UCP capability negotiation
        negotiated, payment_handlers, order_webhook_url = await _get_negotiation_context(request)

        # Convert UCP request to ACP format for the service layer
        items = [
            {"id": item.item.id, "quantity": item.quantity}
            for item in checkout_request.line_items
        ]
        buyer_dict = None
        if checkout_request.buyer:
            buyer_dict = {
                "first_name": checkout_request.buyer.first_name,
                "last_name": checkout_request.buyer.last_name,
                "email": checkout_request.buyer.email,
                "phone": checkout_request.buyer.phone,
            }
        fulfillment_address_dict = None
        if checkout_request.fulfillment_address:
            fulfillment_address_dict = {
                "first_name": checkout_request.fulfillment_address.name,
                "line_one": checkout_request.fulfillment_address.line_one,
                "line_two": checkout_request.fulfillment_address.line_two,
                "city": checkout_request.fulfillment_address.city,
                "state": checkout_request.fulfillment_address.state,
                "country": checkout_request.fulfillment_address.country,
                "postal_code": checkout_request.fulfillment_address.postal_code,
            }

        # Call the ACP service layer (shared business logic)
        acp_response = await create_checkout_session_from_data(
            db,
            items=items,
            buyer=buyer_dict,
            fulfillment_address=fulfillment_address_dict,
            protocol="ucp",  # Indicate this is a UCP request
        )

        # Convert ACP response to UCP format
        ucp_response = transform_to_ucp_response(
            acp_response, negotiated, payment_handlers
        )
        return ucp_response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_ucp_error(e)


@router.get(
    "/checkout-sessions/{session_id}",
    response_model=UCPCheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Get UCP Checkout Session",
    description="Retrieve a checkout session by ID with UCP protocol.",
)
async def get_ucp_checkout(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
) -> UCPCheckoutResponse:
    """Get a UCP checkout session by ID.

    Args:
        request: The HTTP request (for UCP-Agent header).
        session_id: The checkout session ID.
        db: Database session.

    Returns:
        UCPCheckoutResponse with the session details.

    Raises:
        HTTPException: 404 if session not found, 400 if UCP negotiation fails.
    """
    try:
        # Perform UCP capability negotiation
        negotiated, payment_handlers, order_webhook_url = await _get_negotiation_context(request)

        # Get the checkout session from the ACP service layer
        acp_response = get_checkout_session(db, session_id)
        if not acp_response:
            raise SessionNotFoundError(session_id=session_id)

        # Convert ACP response to UCP format
        ucp_response = transform_to_ucp_response(
            acp_response, negotiated, payment_handlers
        )
        return ucp_response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_ucp_error(e)


@router.put(
    "/checkout-sessions/{session_id}",
    response_model=UCPCheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Update UCP Checkout Session",
    description="Update a checkout session with UCP protocol (full replacement).",
)
async def update_ucp_checkout(
    request: Request,
    session_id: str,
    checkout_request: UCPUpdateCheckoutRequest,
    db: Session = Depends(get_session),
) -> UCPCheckoutResponse:
    """Update a UCP checkout session (full replacement).

    Args:
        request: The HTTP request (for UCP-Agent header).
        session_id: The checkout session ID.
        checkout_request: The UCP checkout update request.
        db: Database session.

    Returns:
        UCPCheckoutResponse with the updated session.

    Raises:
        HTTPException: 400 if invalid request, 404 if session not found, 409 if conflict.
    """
    try:
        # Perform UCP capability negotiation
        negotiated, payment_handlers, order_webhook_url = await _get_negotiation_context(request)

        # Convert UCP request to ACP format for the service layer
        items = None
        if checkout_request.line_items is not None:
            items = [
                {"id": item.item.id, "quantity": item.quantity}
                for item in checkout_request.line_items
            ]
        buyer_dict = None
        if checkout_request.buyer is not None:
            buyer_dict = {
                "first_name": checkout_request.buyer.first_name,
                "last_name": checkout_request.buyer.last_name,
                "email": checkout_request.buyer.email,
                "phone": checkout_request.buyer.phone,
            }
        fulfillment_address_dict = None
        if checkout_request.fulfillment_address is not None:
            fulfillment_address_dict = {
                "first_name": checkout_request.fulfillment_address.name,
                "line_one": checkout_request.fulfillment_address.line_one,
                "line_two": checkout_request.fulfillment_address.line_two,
                "city": checkout_request.fulfillment_address.city,
                "state": checkout_request.fulfillment_address.state,
                "country": checkout_request.fulfillment_address.country,
                "postal_code": checkout_request.fulfillment_address.postal_code,
            }

        # Call the ACP service layer (shared business logic)
        acp_response = await update_checkout_session_from_data(
            db,
            session_id,
            items=items,
            buyer=buyer_dict,
            fulfillment_address=fulfillment_address_dict,
            protocol="ucp",  # Indicate this is a UCP request
        )

        # Convert ACP response to UCP format
        ucp_response = transform_to_ucp_response(
            acp_response, negotiated, payment_handlers
        )
        return ucp_response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_ucp_error(e)


@router.post(
    "/checkout-sessions/{session_id}/complete",
    response_model=UCPCheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete UCP Checkout",
    description="Complete a checkout session with UCP protocol.",
)
async def complete_ucp_checkout(
    request: Request,
    session_id: str,
    checkout_request: UCPCompleteCheckoutRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
) -> UCPCheckoutResponse:
    """Complete a UCP checkout session.

    Args:
        request: The HTTP request (for UCP-Agent header).
        session_id: The checkout session ID.
        checkout_request: The UCP checkout completion request.
        background_tasks: FastAPI background tasks handler.
        db: Database session.

    Returns:
        UCPCheckoutResponse with the completed session.

    Raises:
        HTTPException: 400 if invalid request, 404 if session not found, 409 if conflict.
    """
    try:
        # Perform UCP capability negotiation
        negotiated, payment_handlers, order_webhook_url = await _get_negotiation_context(request)

        # Convert UCP request to ACP format for the service layer
        buyer_dict = None
        if checkout_request.buyer is not None:
            buyer_dict = {
                "first_name": checkout_request.buyer.first_name,
                "last_name": checkout_request.buyer.last_name,
                "email": checkout_request.buyer.email,
                "phone": checkout_request.buyer.phone,
            }
        payment_data_dict = {
            "token": checkout_request.payment.instruments[0].credential.token,
            "provider": checkout_request.payment.instruments[0].credential.id,  # Simplified
        }

        # Call the ACP service layer (shared business logic)
        acp_response = await complete_checkout_session_from_data(
            db,
            session_id,
            payment_data=payment_data_dict,
            buyer=buyer_dict,
            protocol="ucp",  # Indicate this is a UCP request
        )

        # Convert ACP response to UCP format
        ucp_response = transform_to_ucp_response(
            acp_response, negotiated, payment_handlers
        )

        # Trigger UCP post-purchase webhook (similar to ACP implementation)
        if acp_response.order is not None:
            # Extract customer name from multiple sources (in priority order):
            # 1. billing_address.name from payment_data (user's actual input)
            # 2. buyer.first_name from request
            # 3. buyer.first_name from session response
            customer_name = extract_customer_name_from_ucp_request(
                checkout_request, acp_response
            )

            items = extract_items_from_line_items(acp_response.line_items)

            # Add background task for UCP post-purchase webhook
            background_tasks.add_task(
                trigger_post_purchase_flow_ucp,
                checkout_session=acp_response,
                customer_name=customer_name,
                items=items,
                language="en",  # Default language, could be extracted from request
                webhook_url=get_settings().ucp_webhook_url or "",
                negotiated=negotiated,
            )

        return ucp_response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_ucp_error(e)


@router.post(
    "/checkout-sessions/{session_id}/cancel",
    response_model=UCPCheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel UCP Checkout",
    description="Cancel a checkout session with UCP protocol.",
)
async def cancel_ucp_checkout(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
) -> UCPCheckoutResponse:
    """Cancel a UCP checkout session.

    Args:
        request: The HTTP request (for UCP-Agent header).
        session_id: The checkout session ID.
        db: Database session.

    Returns:
        UCPCheckoutResponse with the canceled session.

    Raises:
        HTTPException: 404 if session not found, 400 if UCP negotiation fails.
    """
    try:
        # Perform UCP capability negotiation
        negotiated, payment_handlers, order_webhook_url = await _get_negotiation_context(request)

        # Cancel the checkout session using the ACP service layer
        acp_response = cancel_checkout_session(db, session_id)
        if not acp_response:
            raise SessionNotFoundError(session_id=session_id)

        # Convert ACP response to UCP format
        ucp_response = transform_to_ucp_response(
            acp_response, negotiated, payment_handlers
        )
        return ucp_response

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_ucp_error(e)