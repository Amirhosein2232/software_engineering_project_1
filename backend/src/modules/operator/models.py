from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.base import Base


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"
    __table_args__ = (
        Index(
            "unique_active_ticket_assignment",
            "ticket_id",
            unique=True,
            postgresql_where="ended_at IS NULL",
        ),
        Index("idx_assignments_department", "department_id"),
        Index("idx_assignments_assigned_to", "assigned_to"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column()
    note: Mapped[str | None] = mapped_column(Text)

    ticket: Mapped["Ticket"] = relationship("Ticket")
    department: Mapped["Department | None"] = relationship("Department")


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"
    __table_args__ = (
        Index("idx_status_history_ticket", "ticket_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)

    ticket: Mapped["Ticket"] = relationship("Ticket")