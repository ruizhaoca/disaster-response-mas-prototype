"""Shared operational state for the MAS prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    task_id: str
    task_type: str
    location: str
    severity: int
    confidence: float
    required_capability: str
    requested_resources: dict[str, int]
    source: str
    status: str = "open"


@dataclass
class Bid:
    task_id: str
    agent: str
    utility: float
    risk: float
    cost: float
    resource_impact: dict[str, int]
    rationale: str
    constraints: list[str] = field(default_factory=list)


@dataclass
class RouteProposal:
    task_id: str
    route_id: str
    travel_minutes: int
    risk: float
    blocked: bool
    rationale: str


@dataclass
class Decision:
    task_id: str
    status: str
    selected_agent: str | None
    route_id: str | None
    utility: float
    risk: float
    rationale: str
    human_required: bool = False
    human_outcome: str | None = None


@dataclass
class Blackboard:
    tasks: dict[str, Task] = field(default_factory=dict)
    hazards: dict[str, dict[str, Any]] = field(default_factory=dict)
    bids: dict[str, list[Bid]] = field(default_factory=dict)
    routes: dict[str, list[RouteProposal]] = field(default_factory=dict)
    decisions: list[Decision] = field(default_factory=list)
    escalations: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[str] = field(default_factory=list)
    inventory: dict[str, int] = field(
        default_factory=lambda: {
            "ambulance": 2,
            "med_kit": 8,
            "fuel_can": 5,
            "water_crate": 12,
            "generator": 1,
            "rescue_van": 2,
        }
    )
    reserve_floor: dict[str, int] = field(
        default_factory=lambda: {
            "ambulance": 1,
            "med_kit": 2,
            "fuel_can": 1,
            "water_crate": 3,
            "generator": 0,
            "rescue_van": 1,
        }
    )

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task
        self.audit(f"task opened: {task.task_id} {task.task_type} at {task.location}")

    def add_hazard(self, location: str, hazard: dict[str, Any]) -> None:
        self.hazards[location] = hazard
        self.audit(f"hazard updated: {location} risk={hazard.get('risk')} confidence={hazard.get('confidence')}")

    def add_bid(self, bid: Bid) -> None:
        self.bids.setdefault(bid.task_id, []).append(bid)
        self.audit(f"bid: {bid.agent} on {bid.task_id} utility={bid.utility:.2f} risk={bid.risk:.2f}")

    def add_route(self, proposal: RouteProposal) -> None:
        self.routes.setdefault(proposal.task_id, []).append(proposal)
        self.audit(
            f"route: {proposal.route_id} for {proposal.task_id} "
            f"risk={proposal.risk:.2f} blocked={proposal.blocked}"
        )

    def add_decision(self, decision: Decision) -> None:
        self.decisions.append(decision)
        task = self.tasks.get(decision.task_id)
        if task:
            task.status = decision.status
        self.audit(
            f"decision: {decision.status} {decision.task_id} "
            f"agent={decision.selected_agent} route={decision.route_id} "
            f"risk={decision.risk:.2f} human={decision.human_outcome}"
        )

    def apply_resource_impact(self, impact: dict[str, int]) -> None:
        for resource, amount in impact.items():
            self.inventory[resource] = self.inventory.get(resource, 0) - amount

    def violates_reserve(self, impact: dict[str, int]) -> list[str]:
        violations = []
        for resource, amount in impact.items():
            remaining = self.inventory.get(resource, 0) - amount
            floor = self.reserve_floor.get(resource, 0)
            if remaining < floor:
                violations.append(f"{resource} remaining {remaining} below reserve {floor}")
        return violations

    def audit(self, entry: str) -> None:
        self.audit_log.append(entry)
