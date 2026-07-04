"""SQLAlchemy models — Postgres-ready (string UUID pks, JSON columns, indexed FKs)
but running on SQLite for the demo. Every tenant-scoped table carries org_id and
must be queried through the org-scope dependency (RLS stand-in)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# ----------------------------------------------------------------------------- tenancy
class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16), default="manager")  # manager|yard


class User(TimestampMixin, Base):
    __tablename__ = "users"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(24), default="superintendent")  # admin|superintendent|viewer
    accent: Mapped[str] = mapped_column(String(16), default="cerise")
    theme: Mapped[str] = mapped_column(String(16), default="system")


# ----------------------------------------------------------------------------- fleet
class Vessel(TimestampMixin, Base):
    __tablename__ = "vessels"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    vessel_type: Mapped[str] = mapped_column(String(40))  # LR2 / Aframax / MR ...
    dwt: Mapped[int] = mapped_column(Integer, default=0)
    loa_m: Mapped[float] = mapped_column(Float, default=0.0)
    beam_m: Mapped[float] = mapped_column(Float, default=0.0)
    summer_draft_m: Mapped[float] = mapped_column(Float, default=0.0)
    gt: Mapped[int] = mapped_column(Integer, default=0)
    built_year: Mapped[int] = mapped_column(Integer, default=0)
    class_society: Mapped[str] = mapped_column(String(40), default="")
    last_docking_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_docking_yard: Mapped[str] = mapped_column(String(120), default="")
    special_survey_no: Mapped[int] = mapped_column(Integer, default=1)
    uwild_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    edd_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    tce_usd_day: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")


# ----------------------------------------------------------------------------- yards
class Yard(TimestampMixin, Base):
    __tablename__ = "yards"
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80), default="")
    region: Mapped[str] = mapped_column(String(16), default="")  # SEA|MEast|ISC|FarEast|Med|NEur|Am
    labor_rate_band: Mapped[str] = mapped_column(String(8), default="mid")  # low|mid|high
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lon: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    docks: Mapped[list["Dock"]] = relationship(back_populates="yard", cascade="all, delete-orphan")


class Dock(TimestampMixin, Base):
    __tablename__ = "docks"
    yard_id: Mapped[str] = mapped_column(ForeignKey("yards.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16), default="graving")  # graving|floating
    length_m: Mapped[float] = mapped_column(Float, default=0.0)
    beam_m: Mapped[float] = mapped_column(Float, default=0.0)
    depth_over_blocks_m: Mapped[float] = mapped_column(Float, default=0.0)
    max_dwt: Mapped[int] = mapped_column(Integer, default=0)
    cranes_json: Mapped[list] = mapped_column(JSON, default=list)
    yard: Mapped[Yard] = relationship(back_populates="docks")


# ----------------------------------------------------------------------------- work-item library
class WorkItem(TimestampMixin, Base):
    __tablename__ = "work_items"
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    section: Mapped[int] = mapped_column(Integer)
    section_name: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    uom: Mapped[str] = mapped_column(String(24))
    norm_value: Mapped[float] = mapped_column(Float, default=0.0)
    norm_unit: Mapped[str] = mapped_column(String(40), default="")
    norm_basis: Mapped[str] = mapped_column(String(200), default="")  # always a source label
    factors_json: Mapped[dict] = mapped_column(JSON, default=dict)
    typical: Mapped[bool] = mapped_column(Boolean, default=True)


# ----------------------------------------------------------------------------- specifications
class Specification(TimestampMixin, Base):
    __tablename__ = "specifications"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    vessel_id: Mapped[str] = mapped_column(ForeignKey("vessels.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    docking_window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    docking_window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|frozen
    version: Mapped[int] = mapped_column(Integer, default=1)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items: Mapped[list["SpecItem"]] = relationship(
        back_populates="spec", cascade="all, delete-orphan", order_by="SpecItem.line_no"
    )


class SpecItem(TimestampMixin, Base):
    __tablename__ = "spec_items"
    spec_id: Mapped[str] = mapped_column(ForeignKey("specifications.id"), index=True)
    work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"), nullable=True)
    line_no: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200))
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str] = mapped_column(String(24), default="")
    qty_tbc: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String(16), default="owner")  # class|defect|owner|previous
    notes: Mapped[str] = mapped_column(Text, default="")
    spec: Mapped[Specification] = relationship(back_populates="items")


# ----------------------------------------------------------------------------- tenders
class Tender(TimestampMixin, Base):
    __tablename__ = "tenders"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    spec_id: Mapped[str] = mapped_column(ForeignKey("specifications.id"), index=True)
    ref: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # TND-YYYY-NNN
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|issued|closed|awarded
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fx_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fx_rates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    offhire_usd_day: Mapped[float] = mapped_column(Float, default=0.0)
    sealed: Mapped[bool] = mapped_column(Boolean, default=True)


class Invitation(TimestampMixin, Base):
    __tablename__ = "invitations"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    yard_id: Mapped[str] = mapped_column(ForeignKey("yards.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="invited")  # invited|declined|bid_received


class Clarification(TimestampMixin, Base):
    __tablename__ = "clarifications"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    asked_by: Mapped[str] = mapped_column(String(120), default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    addendum_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


# ----------------------------------------------------------------------------- bids
class Bid(TimestampMixin, Base):
    __tablename__ = "bids"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    yard_id: Mapped[str] = mapped_column(ForeignKey("yards.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    validity_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dock_id: Mapped[str | None] = mapped_column(ForeignKey("docks.id"), nullable=True)
    dock_days: Mapped[int] = mapped_column(Integer, default=0)
    slot_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    slot_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    terms_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tariff_captured: Mapped[bool] = mapped_column(Boolean, default=False)
    # TEC deviation inputs, captured with the bid (routing distance from the vessel's
    # discharge port to the yard, and port/canal dues for that deviation).
    deviation_nm: Mapped[float] = mapped_column(Float, default=0.0)
    port_fees_usd: Mapped[float] = mapped_column(Float, default=0.0)
    # Final-account growth factor for this yard; None -> tender/params default. In a
    # real build this is derived from the yard's scorecard history.
    growth_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sealed_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="portal")  # portal|ai_ingest
    lines: Mapped[list["BidLine"]] = relationship(
        back_populates="bid", cascade="all, delete-orphan"
    )


class BidLine(TimestampMixin, Base):
    __tablename__ = "bid_lines"
    bid_id: Mapped[str] = mapped_column(ForeignKey("bids.id"), index=True)
    spec_item_id: Mapped[str | None] = mapped_column(ForeignKey("spec_items.id"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    uom: Mapped[str] = mapped_column(String(24), default="")
    qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="priced")  # priced|included|excluded|unpriced
    assumptions: Mapped[str] = mapped_column(Text, default="")
    # VO-exposure inputs for excluded/unpriced lines: the provisional value used to
    # price the risk (a regional tariff median), and any extra carried because the
    # line's man-hour norm is below the guide band on a to-be-confirmed quantity.
    exposure_median_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    below_norm_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bid: Mapped[Bid] = relationship(back_populates="lines")


class Tariff(TimestampMixin, Base):
    __tablename__ = "tariffs"
    yard_id: Mapped[str] = mapped_column(ForeignKey("yards.id"), index=True)
    bid_id: Mapped[str | None] = mapped_column(ForeignKey("bids.id"), nullable=True)
    doc_name: Mapped[str] = mapped_column(String(200), default="")
    lines_json: Mapped[list] = mapped_column(JSON, default=list)


# ----------------------------------------------------------------------------- evaluation
class Evaluation(TimestampMixin, Base):
    __tablename__ = "evaluations"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class TecComponent(TimestampMixin, Base):
    __tablename__ = "tec_components"
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"), index=True)
    bid_id: Mapped[str] = mapped_column(ForeignKey("bids.id"), index=True)
    normalized_usd: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_usd: Mapped[float] = mapped_column(Float, default=0.0)
    offhire_usd: Mapped[float] = mapped_column(Float, default=0.0)
    vo_exposure_usd: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_nm: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_days: Mapped[float] = mapped_column(Float, default=0.0)
    flags_json: Mapped[list] = mapped_column(JSON, default=list)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False)


# ----------------------------------------------------------------------------- award & settlement
class Award(TimestampMixin, Base):
    __tablename__ = "awards"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    bid_id: Mapped[str] = mapped_column(ForeignKey("bids.id"), index=True)
    memo_note: Mapped[str] = mapped_column(Text, default="")
    checklist_json: Mapped[dict] = mapped_column(JSON, default=dict)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class VariationOrder(TimestampMixin, Base):
    __tablename__ = "variation_orders"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    award_id: Mapped[str] = mapped_column(ForeignKey("awards.id"), index=True)
    vo_no: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    spec_item_id: Mapped[str | None] = mapped_column(ForeignKey("spec_items.id"), nullable=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str] = mapped_column(String(24), default="")
    proposed_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tariff_line_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tariff_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="proposed")  # proposed|approved|disputed|rejected
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FinalAccount(TimestampMixin, Base):
    __tablename__ = "final_accounts"
    award_id: Mapped[str] = mapped_column(ForeignKey("awards.id"), index=True)
    lines_json: Mapped[list] = mapped_column(JSON, default=list)
    quoted_usd: Mapped[float] = mapped_column(Float, default=0.0)
    final_usd: Mapped[float] = mapped_column(Float, default=0.0)
    growth_pct: Mapped[float] = mapped_column(Float, default=0.0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class YardScore(TimestampMixin, Base):
    __tablename__ = "yard_scores"
    yard_id: Mapped[str] = mapped_column(ForeignKey("yards.id"), index=True)
    docking_ref: Mapped[str] = mapped_column(String(40), default="")
    growth_pct: Mapped[float] = mapped_column(Float, default=0.0)
    overrun_days: Mapped[int] = mapped_column(Integer, default=0)
    quality: Mapped[int] = mapped_column(Integer, default=3)  # 1..5
    hse: Mapped[int] = mapped_column(Integer, default=3)  # 1..5
    notes: Mapped[str] = mapped_column(Text, default="")


# ----------------------------------------------------------------------------- audit & agents
class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AgentEvent(TimestampMixin, Base):
    __tablename__ = "agent_events"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent: Mapped[str] = mapped_column(String(24))  # bid_parser|sanity_checker|docking_clock|vo_reconciler|clarifier
    severity: Mapped[str] = mapped_column(String(8), default="info")  # info|warn|crit
    vessel_id: Mapped[str | None] = mapped_column(ForeignKey("vessels.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(String(200), default="")
    needs_decision: Mapped[bool] = mapped_column(Boolean, default=False)
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now)
