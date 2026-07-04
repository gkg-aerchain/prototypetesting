"""Pydantic request/response schemas. Kept lean — routers return dicts for the
aggregate endpoints; these cover auth and the core CRUD bodies."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ----------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    company: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    accent: str
    theme: str
    org_id: str
    org: str = ""
    vessel_count: int = 0

    class Config:
        from_attributes = True


class MePatch(BaseModel):
    accent: str | None = None
    theme: str | None = None
    full_name: str | None = None


# ----------------------------------------------------------------- vessels
class VesselIn(BaseModel):
    name: str
    vessel_type: str = "MR"
    dwt: int = 0
    loa_m: float = 0.0
    beam_m: float = 0.0
    summer_draft_m: float = 0.0
    gt: int = 0
    built_year: int = 0
    class_society: str = ""
    last_docking_date: datetime | None = None
    last_docking_yard: str = ""
    special_survey_no: int = 1
    uwild_ok: bool = False
    edd_enrolled: bool = False
    tce_usd_day: float = 0.0
    notes: str = ""


# ----------------------------------------------------------------- specs
class SpecIn(BaseModel):
    vessel_id: str
    title: str


class SpecItemIn(BaseModel):
    work_item_id: str | None = None
    title: str
    qty: float = 0.0
    uom: str = ""
    qty_tbc: bool = False
    origin: str = "owner"
    notes: str = ""


class SpecItemPatch(BaseModel):
    qty: float | None = None
    uom: str | None = None
    qty_tbc: bool | None = None
    origin: str | None = None
    notes: str | None = None
    title: str | None = None


# ----------------------------------------------------------------- tenders
class TenderIn(BaseModel):
    spec_id: str
    deadline: datetime | None = None
    offhire_usd_day: float = 0.0
    fx_date: datetime | None = None
    fx_rates: dict[str, float] = {}


class InviteIn(BaseModel):
    yard_ids: list[str]


class ClarificationIn(BaseModel):
    question: str


class ClarificationAnswerIn(BaseModel):
    answer: str
    publish: bool = True


# ----------------------------------------------------------------- bids
class BidLineIn(BaseModel):
    spec_item_id: str | None = None
    raw_text: str = ""
    uom: str = ""
    qty: float | None = None
    rate: float | None = None
    amount: float | None = None
    state: str = "priced"
    assumptions: str = ""


class BidIn(BaseModel):
    yard_id: str
    currency: str = "USD"
    dock_id: str | None = None
    dock_days: int = 0
    tariff_captured: bool = False
    lines: list[BidLineIn] = []


class BidLinePatch(BaseModel):
    spec_item_id: str | None = None
    state: str | None = None
    amount: float | None = None
    accept: bool = False


class EvaluateIn(BaseModel):
    offhire_usd_day: float | None = None
    growth_default: float | None = None
    fuel_usd_t: float | None = None
    speed_kn: float | None = None


class AwardIn(BaseModel):
    bid_id: str
    memo_note: str = ""
    checklist: dict = {}


class VOIn(BaseModel):
    title: str
    spec_item_id: str | None = None
    qty: float = 0.0
    uom: str = ""
    proposed_usd: float = 0.0
    tariff_line_ref: str | None = None
    tariff_usd: float | None = None


class VOPatch(BaseModel):
    state: str
    reason: str = ""


class SettlementIn(BaseModel):
    lines: list[dict] = []
    final_usd: float = 0.0


# ----------------------------------------------------------------- ai
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage]
    tender_ref: str | None = None
    vessel_name: str | None = None
