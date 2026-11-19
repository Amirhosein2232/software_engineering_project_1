from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ===========================================================================
# Shared types
# ===========================================================================

TicketStatus = Literal["registered", "in_progress", "waiting_for_student", "resolved"]
TicketStatusFilter = Literal["registered", "in_progress", "waiting_for_student", "resolved"]
AssignmentFilter = Literal["none", "any", "me"]
RoleName = Literal["student", "operator", "admin"]

_IRAN_PHONE_RE = __import__("re").compile(r"^(?:\+98|0)?9\d{9}$")


def _normalize_phone(value: str) -> str:
    if not _IRAN_PHONE_RE.match(value):
        raise ValueError("Invalid Iranian mobile number")
    digits = value.lstrip("+").replace(" ", "")
    if digits.startswith("98"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+98{digits[1:]}"
    return f"+98{digits}"


# ===========================================================================
# User — output
# ===========================================================================

class AdminUserOut(BaseModel):
    """Full user view for admins. Includes role_id and is_active."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[7])
    username: str = Field(..., examples=["ali_ahmadi"])
    email: Optional[str] = Field(None, examples=["student@university.edu"])
    phone_number: Optional[str] = Field(None, examples=["+989123456789"])
    full_name: Optional[str] = Field(None, examples=["Ali Ahmadi"])
    student_number: Optional[str] = Field(None, examples=["40123456789"])
    role_id: int = Field(..., examples=[1])
    role_name: str = Field(..., description="`student`, `operator`, or `admin`.", examples=["student"])
    is_active: bool = Field(..., examples=[True])
    created_at: datetime = Field(..., examples=["2026-11-18T09:15:00Z"])


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int = Field(..., examples=[123])
    page: int = Field(..., examples=[1])
    size: int = Field(..., examples=[20])
    pages: int = Field(..., examples=[7])


# ===========================================================================
# User — create / update
# ===========================================================================

class UserCreateRequest(BaseModel):
    """
    Create a user with any role. Unlike signup, admin chooses the role.
    At least one of `email` / `phone_number` is required (matches DB constraint).
    """
    username: str = Field(..., min_length=3, max_length=50, examples=["ali_ahmadi"])
    password: str = Field(..., min_length=8, examples=["MyStrongPass123"])
    role_id: int = Field(..., gt=0, description="1=student, 2=operator, 3=admin (check your seeded ids).", examples=[1])
    email: Optional[EmailStr] = Field(None, examples=["student@university.edu"])
    phone_number: Optional[str] = Field(None, examples=["09123456789"])
    full_name: Optional[str] = Field(None, max_length=100, examples=["Ali Ahmadi"])
    student_number: Optional[str] = Field(None, min_length=11, max_length=11, examples=["40123456789"])

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_phone(v) if v else None

    @field_validator("student_number")
    @classmethod
    def _student_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.isdigit():
            raise ValueError("Student number must contain only digits")
        return v

    @model_validator(mode="after")
    def _contact_required(self):
        if not self.email and not self.phone_number:
            raise ValueError("At least one of email or phone_number is required")
        return self


class UserUpdateRequest(BaseModel):
    """Partial update. Only included fields are changed."""
    full_name: Optional[str] = Field(None, max_length=100, examples=["Ali Ahmadi"])
    email: Optional[EmailStr] = Field(None, examples=["new@university.edu"])
    phone_number: Optional[str] = Field(None, examples=["09123456789"])
    student_number: Optional[str] = Field(None, min_length=11, max_length=11, examples=["40123456789"])
    role_id: Optional[int] = Field(None, gt=0, examples=[2])

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_phone(v) if v else None

    @field_validator("student_number")
    @classmethod
    def _student_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.isdigit():
            raise ValueError("Student number must contain only digits")
        return v

    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


# ===========================================================================
# Departments
# ===========================================================================

class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[3])
    name: str = Field(..., examples=["IT Support"])
    description: Optional[str] = Field(None, examples=["Hardware, software, and portal access"])


class DepartmentDetailOut(DepartmentOut):
    """Department with its member list."""
    members: list[AdminUserOut] = Field(default_factory=list)


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["IT Support"])
    description: Optional[str] = Field(None, examples=["Hardware, software, and portal access"])


class DepartmentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None)

    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class AddMemberRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="Operator user id to add to the department.", examples=[12])


# ===========================================================================
# Categories
# ===========================================================================

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[1])
    name: str = Field(..., examples=["Portal Access"])
    description: Optional[str] = Field(None, examples=["Login, SSO, password resets"])


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["Portal Access"])
    description: Optional[str] = Field(None, examples=["Login, SSO, password resets"])


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None)

    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


# ===========================================================================
# Tickets — admin view
# ===========================================================================

class _CreatorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., examples=[7])
    username: str = Field(..., examples=["ali_ahmadi"])
    full_name: Optional[str] = Field(None, examples=["Ali Ahmadi"])
    student_number: Optional[str] = Field(None, examples=["40123456789"])


class _AssigneeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., examples=[12])
    full_name: Optional[str] = Field(None, examples=["Sara Karimi"])


class AdminTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[42])
    tracking_number: str = Field(..., examples=["T-20261118-A3F9K2"])
    title: str = Field(..., examples=["Cannot access my student portal"])
    description: str = Field(..., examples=["Since this morning..."])
    status: str = Field(..., examples=["in_progress"])
    category_id: Optional[int] = Field(None, examples=[1])
    category_name: Optional[str] = Field(None, examples=["Portal Access"])
    creator: _CreatorSummary
    assigned_to: Optional[_AssigneeSummary] = Field(
        None, description="Current operator, or `null` if unassigned."
    )
    department_id: Optional[int] = Field(None, examples=[3])
    department_name: Optional[str] = Field(None, examples=["IT Support"])
    created_at: datetime = Field(..., examples=["2026-11-18T09:15:00Z"])
    updated_at: datetime = Field(..., examples=["2026-11-18T10:02:00Z"])
    closed_at: Optional[datetime] = Field(None, examples=[None])


class AdminTicketListOut(BaseModel):
    items: list[AdminTicketOut]
    total: int = Field(..., examples=[57])
    page: int = Field(..., examples=[1])
    size: int = Field(..., examples=[20])
    pages: int = Field(..., examples=[3])


# ===========================================================================
# Tickets — admin actions
# ===========================================================================

class AssignDepartmentRequest(BaseModel):
    department_id: int = Field(..., gt=0, examples=[3])


class AssignOperatorRequest(BaseModel):
    """Assign a specific operator. The ticket must already be in a department."""
    operator_id: int = Field(..., gt=0, examples=[12])
    note: Optional[str] = Field(None, max_length=500, examples=["Escalated to senior operator."])


class ForceReleaseRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500, examples=["Operator unreachable — returning to queue."])


class ReopenRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500, examples=["Student reports the issue returned."])


# ===========================================================================
# Ticket history
# ===========================================================================

class StatusHistoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[1])
    old_status: Optional[str] = Field(None, examples=["registered"])
    new_status: str = Field(..., examples=["in_progress"])
    changed_by_id: Optional[int] = Field(None, description="Operator/admin who changed the status.", examples=[12])
    changed_at: datetime = Field(..., examples=["2026-11-18T10:02:00Z"])
    note: Optional[str] = Field(None, examples=["Assigned to self."])