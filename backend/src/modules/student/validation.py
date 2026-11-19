from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ===========================================================================
# Constants
# ===========================================================================

TICKET_STATUSES = ("registered", "in_progress", "waiting_for_student", "resolved")


# ===========================================================================
# Ticket — create
# ===========================================================================

class TicketCreateRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Short summary of the issue.",
        examples=["Cannot access my student portal"],
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Full description of the problem. Be specific — operators "
                    "use this to triage.",
        examples=[
            "Since this morning, logging in shows 'Invalid credentials' even "
            "though I haven't changed my password. I've tried resetting it twice."
        ],
    )
    category_id: int = Field(
        ...,
        gt=0,
        description="ID of the ticket category. Fetch available categories from "
                    "`GET /student/categories`.",
        examples=[1],
    )

    @field_validator("title", "description")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()


# ===========================================================================
# Ticket — update (partial)
# ===========================================================================

class TicketUpdateRequest(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="New title. Omit to leave unchanged.",
        examples=["Portal login still failing"],
    )
    description: Optional[str] = Field(
        None,
        min_length=10,
        description="New description. Omit to leave unchanged.",
        examples=["Update: also happens on the mobile app."],
    )

    @field_validator("title", "description")
    @classmethod
    def _not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("Field cannot be blank when provided")
        return v.strip()

    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


# ===========================================================================
# Ticket — output
# ===========================================================================

class TicketOut(BaseModel):
    """
    Full ticket view returned to the student who owns it.

    `category_id` is for further API calls (filtering). `category_name` is for display.
    Both are `null` if the category was deleted by an admin.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[42])
    tracking_number: str = Field(..., examples=["T-20261118-A3F9K2"])
    title: str = Field(..., examples=["Cannot access my student portal"])
    description: str = Field(..., examples=["Since this morning..."])
    status: str = Field(
        ...,
        description="One of: `registered`, `in_progress`, `waiting_for_student`, `resolved`.",
        examples=["in_progress"],
    )
    category_id: Optional[int] = Field(
        None, description="Category id, or null if uncategorized.", examples=[1]
    )
    category_name: Optional[str] = Field(
        None, description="Human-readable category name, or null if uncategorized.",
        examples=["Portal Access"],
    )
    creator_id: Optional[int] = Field(
        None,
        description="User id of the ticket creator. Will always be the caller's id "
                    "in student endpoints.",
        examples=[7],
    )
    created_at: datetime = Field(..., examples=["2026-11-18T09:15:00Z"])
    updated_at: datetime = Field(..., examples=["2026-11-18T10:02:00Z"])
    closed_at: Optional[datetime] = Field(
        None, description="Set when the ticket is resolved.", examples=[None]
    )


# ===========================================================================
# Ticket — paginated list
# ===========================================================================

class TicketListOut(BaseModel):
    items: list[TicketOut]
    total: int = Field(..., description="Total number of tickets matching the filter.")
    page: int = Field(..., examples=[1])
    size: int = Field(..., examples=[20])
    pages: int = Field(..., description="Total number of pages.", examples=[3])


# ===========================================================================
# Messages
# ===========================================================================

class MessageCreateRequest(BaseModel):
    body: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Message text. Visible to the operator handling the ticket.",
        examples=["I tried resetting again — still getting the same error."],
    )

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be blank")
        return v.strip()


class MessageOut(BaseModel):
    """
    A public message on a ticket. Internal operator notes (`is_internal=true`)
    are never returned to students, so this model does not include that field.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[101])
    ticket_id: int = Field(..., examples=[42])
    sender_id: Optional[int] = Field(
        None,
        description="User id of the sender. Null if the sender account was deleted.",
        examples=[7],
    )
    body: str = Field(..., examples=["I tried resetting again — still getting the same error."])
    created_at: datetime = Field(..., examples=["2026-11-18T10:05:00Z"])


# ===========================================================================
# Categories (read-only for students)
# ===========================================================================

class CategoryOut(BaseModel):
    """A ticket category. Students can read these to pick one when creating a ticket."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[1])
    name: str = Field(..., examples=["Portal Access"])
    description: Optional[str] = Field(
        None, examples=["Issues logging in, SSO, password resets"]
    )