from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.auth.models import User
from src.modules.student.validation import (
    CategoryOut,
    MessageCreateRequest,
    MessageOut,
    TicketCreateRequest,
    TicketListOut,
    TicketOut,
    TicketUpdateRequest,
)
from src.shared.dependencies import get_current_user

from typing import Literal

router = APIRouter()
TicketStatus = Literal["registered", "in_progress", "waiting_for_student", "resolved"]

# ==========================================
# CATEGORIES (read-only, for the create form)
# ==========================================

@router.get(
    "/categories",
    response_model=list[CategoryOut],
    summary="List ticket categories",
    tags=["CATEGORIES"],
)
async def list_categories(
    user: User = Depends(get_current_user),
):
    """
    Get all available ticket categories.

    Use this to fill the category dropdown when creating a new ticket.
    """
    pass


# ==========================================
# TICKETS - CRUD
# ==========================================

@router.post(
    "/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket",
    tags=["TICKETS - CRUD"],
)
async def create_ticket(
    payload: TicketCreateRequest,
    user: User = Depends(get_current_user),
):
    """
    Submit a new support ticket.

    - New tickets always start with the status `registered`.
    - A unique `tracking_number` is generated automatically.
    - Returns the newly created ticket details.
    """
    pass


@router.get(
    "/tickets",
    response_model=TicketListOut,
    summary="List my tickets",
    tags=["TICKETS - CRUD"],
)
async def list_my_tickets(
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Number of tickets per page (max 100)"),
    status_filter: TicketStatus  | None = Query(
        None,
        alias="status",
        description="Filter by status: `registered`, `in_progress`, "
                    "`waiting_for_student`, or `resolved`",
    ),
    category_id: int | None = Query(None, gt=0, description="Filter by category ID"),
):
    """
    Get a paginated list of your support tickets, ordered from newest to oldest.

    You can optionally filter the list by `status` or `category_id`.
    """
    pass


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    summary="Get ticket details",
    tags=["TICKETS - CRUD"],
)
async def get_my_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get the full details of a specific ticket you own.

    Returns a **404 Not Found** error if the ticket doesn't exist or belongs to someone else.
    """
    pass


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    summary="Edit my ticket",
    tags=["TICKETS - CRUD"],
)
async def update_my_ticket(
    ticket_id: int,
    payload: TicketUpdateRequest,
    user: User = Depends(get_current_user),
):
    """
    Update the `title` or `description` of your ticket.

    - You can only edit a ticket while its status is `registered`.
    - Once support starts working on it, editing is locked. Send a message instead to add more details.
    - Only include the fields you want to change.
    """
    pass


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my ticket",
    tags=["TICKETS - CRUD"],
)
async def delete_my_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
):
    """
    Permanently delete one of your tickets.

    - You can only delete a ticket while its status is `registered`.
    - Once support responds or changes the status, the ticket can no longer be deleted.
    """
    pass


# ==========================================
# MESSAGES
# ==========================================

@router.get(
    "/tickets/{ticket_id}/messages",
    response_model=list[MessageOut],
    summary="List ticket messages",
    tags=["MESSAGES"],
)
async def list_ticket_messages(
    ticket_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get all messages on your ticket, ordered from oldest to newest.

    Private internal notes made by support staff are hidden.
    """
    pass


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message",
    tags=["MESSAGES"],
)
async def post_ticket_message(
    ticket_id: int,
    payload: MessageCreateRequest,
    user: User = Depends(get_current_user),
):
    """
    Reply to your ticket with a new message.

    - You can only send messages when the ticket status is `in_progress` or `waiting_for_student`.
    - Messaging is disabled if the ticket is still `registered` or already `resolved`.
    """
    pass
