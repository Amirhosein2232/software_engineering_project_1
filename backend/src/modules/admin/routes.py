from fastapi import APIRouter, Depends, Query, status

from src.modules.auth.models import User
from src.modules.admin.validation import (
    AddMemberRequest,
    AdminTicketListOut,
    AdminTicketOut,
    AdminUserListOut,
    AdminUserOut,
    AssignDepartmentRequest,
    AssignOperatorRequest,
    CategoryCreateRequest,
    CategoryOut,
    CategoryUpdateRequest,
    DepartmentCreateRequest,
    DepartmentDetailOut,
    DepartmentOut,
    DepartmentUpdateRequest,
    ForceReleaseRequest,
    ReopenRequest,
    RoleName,
    StatusHistoryItemOut,
    TicketStatusFilter,
    UserCreateRequest,
    UserUpdateRequest,
)
from src.shared.dependencies import require_roles
from typing import Literal

router = APIRouter()

Admin = Depends(require_roles("admin"))


# ==========================================
# USERS
# ==========================================

@router.get(
    "/users",
    response_model=AdminUserListOut,
    summary="List all users",
    tags=['ADMIN : USER - CRUD'],
)
async def list_users(
    user: User = Admin,
    page: int = Query(1, ge=1, description="Page number. Starts at 1."),
    size: int = Query(20, ge=1, le=100, description="How many per page (1–100)."),
    role: RoleName | None = Query(None, description="Filter by role: `student`, `operator`, `admin`."),
    is_active: bool | None = Query(None, description="`true` = active only, `false` = deactivated only, omit = all."),
    search: str | None = Query(None, description="Search by username, email, phone, or full name (partial match)."),
):
    """
    **All users in the system.**

    Use this for the admin's "Users" table. Filter by role, active status,
    or search by username/email/phone/name.

    Newest users appear first.
    """
    pass


@router.get(
    "/users/{user_id}",
    response_model=AdminUserOut,
    summary="Get user details",
    tags=['ADMIN : USER - CRUD'],
)
async def get_user(
    user_id: int,
    user: User = Admin,
):
    """
    **Full details of one user.**

    Returns **404** if the user doesn't exist.
    """
    pass


@router.post(
    "/users",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    tags=['ADMIN : USER - CRUD'],
)
async def create_user(
    payload: UserCreateRequest,
    user: User = Admin,
):
    """
    **Create a new user with any role.**

    Unlike public signup (which always creates a `student`), the admin
    chooses the `role_id` here.

    **Required:** `username`, `password`, `role_id`, and **at least one** of
    `email` or `phone_number`.

    **Errors:**
    - `409 Conflict` — username, email, phone, or student_number already in use
    - `422 Unprocessable Entity` — validation failed (e.g., missing both email and phone)
    """
    pass


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    summary="Update a user",
    tags=['ADMIN : USER - CRUD'],
)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    user: User = Admin,
):
    """
    **Update user fields.** Only include what you want to change.

    **Editable:** `full_name`, `email`, `phone_number`, `student_number`, `role_id`.

    **Not editable here:** `username`, `password`, `is_active`. Use
    `/deactivate` and `/activate` for active status; password changes go
    through the user's own flow.

    **Errors:**
    - `404 Not Found` — user doesn't exist
    - `409 Conflict` — new email / phone / student_number already in use
    """
    pass


@router.delete(
    "/users/{user_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user (soft delete)",
    tags=['ADMIN : USER - CRUD'],
)
async def deactivate_user(
    user_id: int,
    user: User = Admin,
):
    """
    **Deactivate a user.**

    This is a **soft delete** — the user row stays in the database with
    `is_active = false`. The user can no longer log in, but their tickets
    and messages stay attributed to them (audit trail preserved).

    **Returns `204 No Content`** — no JSON body.

    **Errors:**
    - `404 Not Found` — user doesn't exist
    - `409 Conflict` — user is already deactivated (no-op, but we signal it)
    """
    pass


@router.patch(
    "/users/{user_id}/activate",
    response_model=AdminUserOut,
    summary="Reactivate a user",
    tags=['ADMIN : USER - CRUD'],
)
async def activate_user(
    user_id: int,
    user: User = Admin,
):
    """
    **Reactivate a deactivated user.**

    Sets `is_active = true`. The user can log in again.

    **Errors:**
    - `404 Not Found` — user doesn't exist
    - `409 Conflict` — user is already active
    """
    pass


# ==========================================
# DEPARTMENTS
# ==========================================

@router.get(
    "/departments",
    response_model=list[DepartmentOut],
    summary="List departments",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def list_departments(
    user: User = Admin,
):
    """
    **All departments.**

    Use this to populate the department dropdown when routing a ticket.
    """
    pass


@router.get(
    "/departments/{department_id}",
    response_model=DepartmentDetailOut,
    summary="Get department detail (with members)",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def get_department(
    department_id: int,
    user: User = Admin,
):
    """
    **One department, including its list of member operators.**

    Use this when the admin needs to see "who is in this department?" before
    assigning a ticket to a specific operator.

    **Errors:**
    - `404 Not Found` — department doesn't exist
    """
    pass


@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def create_department(
    payload: DepartmentCreateRequest,
    user: User = Admin,
):
    """
    **Create a new department.**

    Newly created departments have **no members**. Use
    `POST /admin/departments/{id}/members` to add operators.

    **Errors:**
    - `409 Conflict` — a department with this name already exists
    """
    pass


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentOut,
    summary="Update a department",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def update_department(
    department_id: int,
    payload: DepartmentUpdateRequest,
    user: User = Admin,
):
    """
    **Update a department's name or description.**

    **Errors:**
    - `404 Not Found` — department doesn't exist
    - `409 Conflict` — new name collides with another department
    """
    pass


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def delete_department(
    department_id: int,
    user: User = Admin,
):
    """
    **Delete a department.**

    **What gets affected:**
    - All `department_members` rows for this department are removed (cascade)
    - Tickets routed to this department become unrouted
    - Active assignments to this department are removed

    **Returns `204 No Content`.**

    **Errors:**
    - `404 Not Found` — department doesn't exist
    """
    pass


@router.post(
    "/departments/{department_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Add an operator to a department",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def add_department_member(
    department_id: int,
    payload: AddMemberRequest,
    user: User = Admin,
):
    """
    **Add a user to a department as a member.**

    Typically you add **operators** to departments.

    **Errors:**
    - `404 Not Found` — department or user doesn't exist
    - `409 Conflict` — user is already a member
    """
    pass


@router.delete(
    "/departments/{department_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an operator from a department",
    tags=['ADMIN : DEPARTMENTS - CRUD'],
)
async def remove_department_member(
    department_id: int,
    user_id: int,
    user: User = Admin,
):
    """
    **Remove a user from a department.**

    If the user has active assignments in this department, those assignments
    are removed and the operator no longer sees
    new tickets in this department's queue.

    **Returns `204 No Content`.**

    **Errors:**
    - `404 Not Found` — membership doesn't exist
    """
    pass


# ==========================================
# CATEGORIES
# ==========================================

@router.get(
    "/categories",
    response_model=list[CategoryOut],
    summary="List categories",
    tags=['ADMIN : CATEGORIES - CRUD'],
)
async def list_categories(
    user: User = Admin,
):
    """**All ticket categories.**"""
    pass


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    tags=['ADMIN : CATEGORIES - CRUD'],
)
async def create_category(
    payload: CategoryCreateRequest,
    user: User = Admin,
):
    """
    **Create a new ticket category.**

    **Errors:**
    - `409 Conflict` — category with this name already exists
    """
    pass


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryOut,
    summary="Update a category",
    tags=['ADMIN : CATEGORIES - CRUD'],
)
async def update_category(
    category_id: int,
    payload: CategoryUpdateRequest,
    user: User = Admin,
):
    """
    **Update a category's name or description.**

    **Errors:**
    - `404 Not Found` — category doesn't exist
    - `409 Conflict` — new name collides
    """
    pass


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    tags=['ADMIN : CATEGORIES - CRUD'],
)
async def delete_category(
    category_id: int,
    user: User = Admin,
):
    """
    **Delete a category.**

    Tickets that were in this category get `category_id = NULL`
    (they become "Uncategorized") — they are **not** deleted.

    **Returns `204 No Content`.**

    **Errors:**
    - `404 Not Found` — category doesn't exist
    """
    pass


# ==========================================
# TICKETS
# ==========================================

@router.get(
    "/tickets",
    response_model=AdminTicketListOut,
    summary="List all tickets",
    tags=['ADMIN : TICKETS'],
)
async def list_tickets(
    user: User = Admin,
    page: int = Query(1, ge=1, description="Page number. Starts at 1."),
    size: int = Query(20, ge=1, le=100, description="How many per page (1–100)."),
    status_filter: TicketStatusFilter | None = Query(
        None,
        alias="status",
        description="Filter by status: `registered`, `in_progress`, `waiting_for_student`, `resolved`.",
    ),
    department_id: int | None = Query(None, gt=0, description="Filter by department."),
    assigned_to: int | None = Query(None, gt=0, description="Filter by assigned operator id."),
    assigned: Literal["none", "any"] | None = Query(
        None,
        description="`none` = unassigned only. `any` = assigned only. Omit for both.",
    ),
    category_id: int | None = Query(None, gt=0, description="Filter by category."),
    creator_id: int | None = Query(None, gt=0, description="Filter by student (creator) id."),
    tracking_number: str | None = Query(None, description="Exact match on tracking number."),
):
    """
    **All tickets, across every department.**

    Newest tickets appear first.

    **Useful filter combinations:**

    - `?assigned=none` → **"Needs triage"** — unassigned tickets anywhere
    - `?assigned=none&department_id=3` → unassigned tickets in a specific department
    - `?status=resolved` → all resolved tickets (for review)
    - `?creator_id=7` → all tickets by a specific student
    - `?tracking_number=T-20261118-A3F9K2` → find by tracking number

    **Filters combine freely.**

    **Empty result:** `items: []`, `total: 0`.
    """
    pass


@router.get(
    "/tickets/{ticket_id}",
    response_model=AdminTicketOut,
    summary="Get ticket details",
    tags=['ADMIN : TICKETS'],
)
async def get_ticket(
    ticket_id: int,
    user: User = Admin,
):
    """
    **Full ticket detail.**

    Includes creator summary, assigned operator (or `null`), current
    department (or `null`), and category name.

    **Errors:**
    - `404 Not Found` — ticket doesn't exist
    """
    pass


@router.patch(
    "/tickets/{ticket_id}/department",
    response_model=AdminTicketOut,
    summary="Assign ticket to a department",
    tags=['ADMIN : TICKETS'],
)
async def assign_ticket_department(
    ticket_id: int,
    payload: AssignDepartmentRequest,
    user: User = Admin,
):
    """
    **Route a ticket to a department.**

    Use this to move a ticket from "unrouted" or "wrong department" into
    the correct department's queue.

    **Status stays `registered`.** The ticket hasn't been picked up by an
    operator yet — routing it just makes it visible in that department's
    queue.

    **What changes:**
    - `ticket_assignments.department_id` is set
    - Active assignment (if any) keeps its current `assigned_to`

    **Errors:**
    - `404 Not Found` — ticket or department doesn't exist
    """
    pass


@router.patch(
    "/tickets/{ticket_id}/assignee",
    response_model=AdminTicketOut,
    summary="Assign ticket to a specific operator",
    tags=['ADMIN : TICKETS - ASSIGNMENT'],
)
async def assign_ticket_operator(
    ticket_id: int,
    payload: AssignOperatorRequest,
    user: User = Admin,
):
    """
    **Directly assign a ticket to a specific operator.**

    This is the admin override — normally operators claim tickets themselves.

    **On success:**
    - A new active `TicketAssignment` is created with `assigned_to = operator_id`
    - **Status → `in_progress`** (the operator is now working on it)
    - Any previous active assignment is ended

    **The operator must belong to the ticket's current department.**
    If the ticket isn't routed yet, use `PATCH .../department` first.

    **Errors:**
    - `404 Not Found` — ticket or operator doesn't exist
    - `409 Conflict` — the ticket already has an active assignment (force-release first)
    - `400 Bad Request` — operator isn't a member of the ticket's department
    """
    pass


@router.delete(
    "/tickets/{ticket_id}/assignment",
    response_model=AdminTicketOut,
    summary="Force-release the current operator",
    tags=['ADMIN : TICKETS - ASSIGNMENT'],
)
async def force_release_ticket(
    ticket_id: int,
    user: User = Admin,
    payload: ForceReleaseRequest = None,
):
    """
    **Remove the current operator assignment.**

    Use this when an operator is stuck, unreachable, or assigned to the
    wrong ticket — and they haven't released it themselves.

    **On success:**
    - The active assignment's `ended_at` is set to now
    - `assigned_to` becomes `null`
    - **Status → `registered`** (back in the department queue)
    - The student can edit/delete the ticket again
    - A row is added to `ticket_status_history`

    **Returns the updated ticket.**

    **Errors:**
    - `404 Not Found` — ticket doesn't exist or has no active assignment
    """
    pass


@router.post(
    "/tickets/{ticket_id}/reopen",
    response_model=AdminTicketOut,
    summary="Reopen a resolved ticket",
    tags=['ADMIN : TICKETS - ASSIGNMENT'],
)
async def reopen_ticket(
    ticket_id: int,
    payload: ReopenRequest,
    user: User = Admin,
):
    """
    **Reopen a resolved ticket.**

    Use this when a student reports that the issue came back, or when a
    ticket was resolved by mistake.

    **On success:**
    - Status: `resolved` → `in_progress`
    - `closed_at` becomes `null`
    - A row is added to `ticket_status_history`

    **Errors:**
    - `404 Not Found` — ticket doesn't exist
    - `400 Bad Request` — ticket is not in `resolved` state
    """
    pass


@router.get(
    "/tickets/{ticket_id}/history",
    response_model=list[StatusHistoryItemOut],
    summary="Get ticket status history",
    tags=['ADMIN : TICKETS - ASSIGNMENT'],
)
async def get_ticket_history(
    ticket_id: int,
    user: User = Admin,
):
    """
    **The complete status-change history for a ticket.**

    Returns every row from `ticket_status_history`, oldest first. Each row
    shows who changed the status, when, and the optional note.

    Useful for auditing: "why is this ticket stuck?" or "who reopened it?"

    **Errors:**
    - `404 Not Found` — ticket doesn't exist
    """
    pass