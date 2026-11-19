from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


TicketStatus = Literal["registered", "in_progress", "waiting_for_student", "resolved"]
AssignmentFilter = Literal["me", "unassigned", "all"]

class DepartmentOut(BaseModel):
    """A department the operator belongs to."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[3])
    name: str = Field(..., examples=["IT Support"])
    description: Optional[str] = Field(
        None, examples=["Hardware, software, and portal access issues"]
    )


class _CreatorSummary(BaseModel):
    """Minimal info about the student who created a ticket."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[7])
    username: str = Field(..., examples=["ali_ahmadi"])
    full_name: Optional[str] = Field(None, examples=["Ali Ahmadi"])
    student_number: Optional[str] = Field(None, examples=["40123456789"])


class _AssigneeSummary(BaseModel):
    """Minimal info about the operator assigned to a ticket."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[12])
    full_name: Optional[str] = Field(None, examples=["Sara Karimi"])


class TicketOut(BaseModel):
    """Ticket as seen by an operator in their department."""
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
    category_id: Optional[int] = Field(None, examples=[1])
    category_name: Optional[str] = Field(None, examples=["Portal Access"])
    creator: _CreatorSummary = Field(
        ...,
        description="The student who opened the ticket. Use their `student_number` "
                    "to identify them in the university system.",
    )
    assigned_to: Optional[_AssigneeSummary] = Field(
        None,
        description="The operator currently handling the ticket. `null` means unassigned.",
    )
    department_id: Optional[int] = Field(
        None,
        description="The department the ticket is currently routed to.",
        examples=[3],
    )
    created_at: datetime = Field(..., examples=["2026-11-18T09:15:00Z"])
    updated_at: datetime = Field(..., examples=["2026-11-18T10:02:00Z"])
    closed_at: Optional[datetime] = Field(None, examples=[None])


class TicketListOut(BaseModel):
    items: list[TicketOut]
    total: int = Field(..., description="Total tickets matching the filter.", examples=[57])
    page: int = Field(..., examples=[1])
    size: int = Field(..., examples=[20])
    pages: int = Field(..., examples=[3])


class AssignSelfRequest(BaseModel):
    """
    Assign the ticket to yourself. No fields required — the server sets
    `assigned_to = caller` and `assigned_by = caller`.

    The optional note is stored on the assignment record for audit purposes.
    """
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional note explaining why you're taking this ticket.",
        examples=["This is in my area, I'll handle it."],
    )


class ReleaseRequest(BaseModel):
    """
    Cancel the assignment and return the ticket to `registered`.
    The student can edit/delete it again.
    """
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for releasing the ticket.",
        examples=["Going on leave — handing this back to the queue."],
    )

class ResolveRequest(BaseModel):
    """Mark the ticket as resolved and end the assignment."""
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional note about the resolution (recorded in status history).",
        examples=["Student confirmed the fix works."],
    )

class StatusChangeRequest(BaseModel):
    new_status: Literal["in_progress", "waiting_for_student"] = Field(
        ...,
        description="The new status. Allowed values: `in_progress`, "
                    "`waiting_for_student`. Use `/resolve` to finish the "
                    "ticket, or `/release` to cancel the assignment.",
        examples=["waiting_for_student"],
    )

class MessageCreateRequest(BaseModel):
    body: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Message text.",
        examples=["Hi — could you confirm which browser you're using?"],
    )
    is_internal: bool = Field(
        False,
        description="`true` = internal note (operators only). "
                    "`false` = public message visible to the student.",
        examples=[False],
    )

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be blank")
        return v.strip()


class MessageOut(BaseModel):
    """A message on a ticket, as seen by an operator (includes internal notes)."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[101])
    ticket_id: int = Field(..., examples=[42])
    sender_id: Optional[int] = Field(None, examples=[12])
    body: str = Field(..., examples=["Hi — could you confirm which browser?"])
    is_internal: bool = Field(
        ...,
        description="`true` = internal note, `false` = public reply.",
        examples=[False],
    )
    created_at: datetime = Field(..., examples=["2026-11-18T10:05:00Z"])