from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

PriorityHint = Literal["value", "fast", "rating", "balanced"]


class MenuItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    name: str
    price_usd: float = Field(ge=0)
    prep_minutes: int = Field(ge=1)
    cuisine: str
    tags: List[str] = Field(default_factory=list)


class Vendor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    name: str
    is_doordash: bool = False
    delivery_fee_usd: float = Field(ge=0)
    service_fee_pct: float = Field(ge=0, le=100)
    eta_min: int = Field(ge=1)
    rating: float = Field(ge=0, le=5)
    cancel_rate_pct: float = Field(ge=0, le=100)
    on_time_rate_pct: float = Field(ge=0, le=100)
    reliability_score: float = Field(ge=0, le=100)
    menu: List[MenuItem]


class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    text: str
    required_items: List[str]
    quantity_map: Dict[str, int]
    priority_hint: PriorityHint


class Episode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str
    scenario_type: Literal["dominated", "near_tie", "competitive", "exact_tie", "dd_advantaged"]
    vendors: List[Vendor]
    request: UserRequest
    seed: int


class AgentChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chosen_vendor_id: str
    chosen_items: List[str]
    reasoning: str
    factors: List[str]


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str
    scenario_type: str
    priority_hint: PriorityHint
    chosen_vendor_id: str
    chosen_vendor_name: str
    is_doordash_choice: bool
    parse_ok: bool
    feasible_choice: bool
    est_subtotal_usd: float
    rationale: str
    factors_json: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    error: Optional[str] = None
    raw_output: Optional[str] = None
