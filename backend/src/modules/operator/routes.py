from fastapi import APIRouter, Depends, Query, status

from src.modules.auth.models import User
from src.modules.operator.validation import (
    AssignSelfRequest,
    AssignmentFilter,
    DepartmentOut,
    MessageCreateRequest,
    MessageOut,
    ReleaseRequest,
    ResolveRequest,
    StatusChangeRequest,
    TicketListOut,
    TicketOut,
    TicketStatus,
)
from src.shared.dependencies import require_roles

router = APIRouter()

Operator = Depends(require_roles("operator", "admin"))

@router.get(
    "/departments",
    response_model=list[DepartmentOut],
    summary="List my departments",
    tags=["OPERATOR : DEPARTMENTS"],
)
async def list_my_departments(
    user: User = Operator,
    
):
    """
    **Departments you belong to.**

    Use this to build the department filter dropdown on the tickets page.

    You'll get back an array like:
    [
        { "id": 3, "name": "IT Support", "description": "Hardware, software, and portal access issues" },
        { "id": 5, "name": "Student Affairs", "description": null }
    ]
    Show the `name` to the operator. When they pick one, pass the `id` as
    `department_id` to `GET /operator/tickets` to filter.

    """
    pass

@router.get(
    "/tickets",
    response_model=TicketListOut,
    summary="List department tickets",
    tags=["OPERATOR : TICKETS"],
)
async def list_department_tickets(
    user: User = Operator,
    page: int = Query(1, ge=1, description="Page number. Starts at 1."),
    size: int = Query(20, ge=1, le=100, description="How many per page (1–100)."),
    assigned: AssignmentFilter = Query(
        "all",
        description="Filter by assignment: `me` (assigned to me), "
                    "`unassigned` (nobody yet), `all` (everything in my departments).",
        examples=["me"],
    ),
    status_filter: TicketStatus | None = Query(
        None,
        alias="status",
        description="Optional filter: `registered`, `in_progress`, "
                    "`waiting_for_student`, `resolved`.",
    ),
    category_id: int | None = Query(None, gt=0, description="Optional filter by category."),
    department_id: int | None = Query(
        None,
        gt=0,
        description="Optional filter: show only tickets in this department. "
                    "Must be one of your own departments (see `GET /operator/departments`).",
    ),
    tracking_number: str | None = Query(
        None, description="Optional exact-match filter by tracking number."
    ),
):
    """
    **Your department's ticket queue.**

    You only see tickets routed to **a department you are a member of**.
    Tickets in other departments are invisible to you.

    Use the `assigned` filter to switch between three views the frontend
    likely shows as tabs:

    - `assigned=me` → **My tickets** — the ones currently assigned to you
    - `assigned=unassigned` → **Queue** — tickets waiting for someone to claim
    - `assigned=all` → **All department tickets** — everything in your
      departments, assigned or not

    Use `department_id` to narrow to a single department. If you belong to
    more than one, the frontend can show a dropdown populated from
    `GET /operator/departments`. Passing a `department_id` you don't belong
    to returns `403 Forbidden`.

    Newest tickets appear first within each view.

    **Filters** combine: `?assigned=unassigned&status=registered&department_id=3`
    returns unclaimed, still-unstarted tickets in department 3.

    **Empty result:** `items: []`, `total: 0`. Show a friendly "nothing here."
    """
    pass


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    summary="Get ticket details",
    tags=["OPERATOR : TICKETS"],
)
async def get_ticket(
    ticket_id: int,
    user: User = Operator,
):
    """
    **The ticket detail page.**

    Returns **404** if:
    1. The ticket doesn't exist.
    2. The ticket is routed to a department you don't belong to.

    The response includes:
    - The student's `username`, `full_name`, and `student_number`
      (so you can identify them)
    - The assigned operator (or `null` if unassigned)
    - The current department id
    """
    pass


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Assign the ticket to yourself",
    tags=["OPERATOR : ASSIGNMENTS"],
)
async def assign_to_self(
    ticket_id: int,
    payload: AssignSelfRequest,
    user: User = Operator,
):
    """
    **Claim an unassigned ticket from your department queue.**

    On success:
    - A new active `TicketAssignment` is created with `assigned_to = you`
    - The ticket's status is set to `in_progress`
    - The ticket's `assigned_to` field is populated

    **Rules:**
    - The ticket must currently be **unassigned**. If another operator
      already has it, you'll get `409 Conflict`.
    - The ticket must be in a department you belong to.

    **Errors:**
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    - `409 Conflict` — ticket is already assigned to someone
    """
    pass


@router.post(
    "/tickets/{ticket_id}/release",
    response_model=TicketOut,
    summary="Cancel the assignment",
    tags=["OPERATOR : ASSIGNMENTS"],
)
async def release_ticket(
    ticket_id: int,
    payload: ReleaseRequest,
    user: User = Operator,
):
    """
    **Cancel the assignment and hand the ticket back to the student.**

    Use this when the ticket shouldn't have been claimed — wrong department,
    duplicate, student's mistake, etc.

    On success:
    - The active assignment's `ended_at` is set to now
    - The ticket's `assigned_to` becomes `null`
    - The ticket's status becomes `registered` — **the student can now edit
      or delete the ticket again**
    - A row is added to `ticket_status_history`

    **Rules:**
    - You can only release tickets **currently assigned to you**.
    - You cannot release a `resolved` ticket.

    **Errors:**
    - `403 Forbidden` — ticket isn't assigned to you
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    - `400 Bad Request` — ticket is already resolved
    """
    pass

@router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=TicketOut,
    summary="Resolve the ticket",
    tags=["OPERATOR : ASSIGNMENTS"],
)
async def resolve_ticket(
    ticket_id: int,
    payload: ResolveRequest,
    user: User = Operator,
):
    """
    **Mark the ticket as done.**

    This is the successful end of the workflow — the issue was handled.

    On success:
    - The active assignment's `ended_at` is set to now
    - The ticket's `assigned_to` becomes `null`
    - The ticket's status becomes `resolved`
    - `closed_at` is set to now
    - A row is added to `ticket_status_history`

    **Rules:**
    - You can only resolve tickets **currently assigned to you**.
    - The ticket must be in `in_progress` or `waiting_for_student` (you
      cannot resolve a ticket that was never claimed).

    **Errors:**
    - `403 Forbidden` — ticket isn't assigned to you
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    - `400 Bad Request` — ticket is already resolved
    """
    pass

@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    summary="Toggle between in_progress and waiting_for_student",
    tags=["OPERATOR : ASSIGNMENTS"],
)
async def change_ticket_status(
    ticket_id: int,
    payload: StatusChangeRequest,
    user: User = Operator,
):
    """
    **Switch the ticket between `in_progress` and `waiting_for_student`.**

    Use this when:
    - You need info from the student → `in_progress → waiting_for_student`
    - The student replied and you're back to work → `waiting_for_student → in_progress`

    **To finish the ticket, use `POST .../resolve` instead.**
    To cancel the assignment, use `POST .../release`.

    **Allowed transitions:**
    - `in_progress` → `waiting_for_student`
    - `waiting_for_student` → `in_progress`

    **Not allowed from this endpoint:**
    - `resolved` (use `.../resolve`)
    - `registered` (use `.../release`)
    - Any transition on a ticket **not assigned to you**

    Every change is recorded in `ticket_status_history`.

    **Errors:**
    - `403 Forbidden` — ticket isn't assigned to you
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    - `400 Bad Request` — invalid transition (e.g., you sent `resolved`)
    """
    pass


@router.get(
    "/tickets/{ticket_id}/messages",
    response_model=list[MessageOut],
    summary="List all messages on a ticket",
    tags=["OPERATOR : MESSAGES"],
)
async def list_messages(
    ticket_id: int,
    user: User = Operator,
):
    """
    **The full conversation thread on a ticket.**

    Returns **all** messages, oldest first — including `is_internal=true`
    notes that students never see.

    Each message has `is_internal` so the frontend can style public vs.
    internal messages differently (e.g., internal notes in a yellow box).

    **Errors:**
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    """
    pass


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message on a ticket",
    tags=["OPERATOR : MESSAGES"],
)
async def post_message(
    ticket_id: int,
    payload: MessageCreateRequest,
    user: User = Operator,
):
    """
    **Reply to the student (public) or leave an internal note.**

    The `is_internal` flag decides who sees it:

    - `is_internal: false` → **public reply** — the student sees it in their
      chat, and it's the right choice when asking a question or explaining a fix.
    - `is_internal: true` → **internal note** — only operators and admins see
      it. Use for things like "account is flagged, do not refund" or
      "waiting on the billing team to confirm."

    **Rules:**
    - You must be assigned to this ticket to post a message (even internal).
    - The ticket must not be `resolved` — a resolved ticket is closed for
      conversation. (Reopen via admin if needed.)

    **Errors:**
    - `403 Forbidden` — ticket isn't assigned to you
    - `404 Not Found` — ticket doesn't exist or isn't in your department
    - `400 Bad Request` — ticket is already resolved
    """
    pass