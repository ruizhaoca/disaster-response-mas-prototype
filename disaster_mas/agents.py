"""Agents and coordination policy for the disaster-response MAS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .blackboard import Bid, Blackboard, Decision, RouteProposal, Task
from .messages import Message, MessageBus


@dataclass(frozen=True)
class FieldReport:
    report_id: str
    location: str
    report_type: str
    severity: int
    confidence: float
    details: str
    requested_resources: dict[str, int]


class Agent:
    def __init__(self, name: str, board: Blackboard, bus: MessageBus) -> None:
        self.name = name
        self.board = board
        self.bus = bus

    def send(
        self,
        recipient: str,
        type_: str,
        payload: dict[str, Any],
        trace_id: str,
        priority: int = 3,
        requires_ack: bool = False,
    ) -> None:
        self.bus.publish(
            Message(
                sender=self.name,
                recipient=recipient,
                type=type_,
                payload=payload,
                trace_id=trace_id,
                priority=priority,
                requires_ack=requires_ack,
            )
        )


class ScoutAgent(Agent):
    """Transforms field reports into tasks or hazard updates."""

    capability_map = {
        "medical_evacuation": "medical",
        "supply_delivery": "logistics",
        "generator_support": "logistics",
        "route_hazard": "routing",
    }

    def ingest(self, report: FieldReport) -> None:
        trace_id = f"incident-{report.report_id}"
        if report.report_type == "route_hazard":
            payload = {
                "location": report.location,
                "risk": min(1.0, 0.2 + report.severity * 0.16),
                "confidence": report.confidence,
                "details": report.details,
            }
            self.send("command_center", "hazard.update", payload, trace_id, priority=report.severity)
            return

        task = Task(
            task_id=f"task-{report.report_id}",
            task_type=report.report_type,
            location=report.location,
            severity=report.severity,
            confidence=report.confidence,
            required_capability=self.capability_map[report.report_type],
            requested_resources=report.requested_resources,
            source=self.name,
        )
        self.send("command_center", "task.created", task.__dict__, trace_id, priority=report.severity, requires_ack=True)


class MedicalAgent(Agent):
    """Bids on tasks where casualty risk is central."""

    def bid_on(self, task: Task) -> Bid | None:
        if task.required_capability != "medical":
            return None
        med_kits = task.requested_resources.get("med_kit", 0)
        ambulances = task.requested_resources.get("ambulance", 0)
        reserve_issues = self.board.violates_reserve({"med_kit": med_kits, "ambulance": ambulances})
        utility = task.severity * 18 + task.confidence * 12 - len(reserve_issues) * 20
        risk = max(0.05, 1 - task.confidence) + 0.08 * ambulances
        constraints = reserve_issues.copy()
        rationale = "prioritizes casualty stabilization and evacuation capacity"
        return Bid(task.task_id, self.name, utility, risk, med_kits * 2 + ambulances * 8, {"med_kit": med_kits, "ambulance": ambulances}, rationale, constraints)


class LogisticsAgent(Agent):
    """Bids on physical-resource tasks and can support some evacuations."""

    def bid_on(self, task: Task) -> Bid | None:
        if task.required_capability not in {"logistics", "medical"}:
            return None

        impact = {
            resource: amount
            for resource, amount in task.requested_resources.items()
            if resource in self.board.inventory
        }
        reserve_issues = self.board.violates_reserve(impact)
        logistics_fit = 1.0 if task.required_capability == "logistics" else 0.55
        scarcity_penalty = sum(
            amount / max(1, self.board.inventory.get(resource, 1))
            for resource, amount in impact.items()
        )
        utility = task.severity * 14 * logistics_fit + task.confidence * 10 - scarcity_penalty * 7 - len(reserve_issues) * 18
        risk = max(0.05, 1 - task.confidence) + scarcity_penalty * 0.09
        rationale = "balances dispatch usefulness against inventory reserve floors"
        return Bid(task.task_id, self.name, utility, risk, scarcity_penalty * 10, impact, rationale, reserve_issues)


class RoutingAgent(Agent):
    """Proposes and vetoes routes based on known hazards."""

    base_routes = {
        "Library Shelter": [
            ("route-library-main", ["Main Street", "Library Shelter"], 14),
            ("route-library-hill", ["Hill Road", "Library Shelter"], 23),
        ],
        "East Clinic": [
            ("route-clinic-main", ["Main Street", "East Clinic"], 11),
            ("route-clinic-ring", ["Ring Road", "East Clinic"], 19),
        ],
        "River Bridge": [
            ("route-bridge-direct", ["Main Street", "River Bridge"], 9),
            ("route-bridge-north", ["North Road", "River Bridge"], 21),
        ],
    }

    def routes_for(self, task: Task) -> list[RouteProposal]:
        proposals: list[RouteProposal] = []
        for route_id, segments, minutes in self.base_routes.get(task.location, []):
            hazard_risk = 0.0
            hazard_reasons = []
            for segment in segments:
                hazard = self.board.hazards.get(segment)
                if hazard:
                    hazard_risk = max(hazard_risk, float(hazard["risk"]) * float(hazard["confidence"]))
                    hazard_reasons.append(f"{segment} hazard")
            risk = min(1.0, hazard_risk + (1 - task.confidence) * 0.35 + minutes / 180)
            blocked = risk >= 0.72
            rationale = "clear route" if not hazard_reasons else ", ".join(hazard_reasons)
            proposals.append(RouteProposal(task.task_id, route_id, minutes, risk, blocked, rationale))
        if not proposals:
            proposals.append(RouteProposal(task.task_id, "route-unknown", 45, 0.82, True, "no known safe route"))
        return proposals

    def publish_routes(self, task: Task) -> None:
        trace_id = f"incident-{task.task_id}"
        for proposal in self.routes_for(task):
            message_type = "route.veto" if proposal.blocked else "route.propose"
            self.send("command_center", message_type, proposal.__dict__, trace_id, priority=task.severity)


class HumanApprover(Agent):
    """Scripted human commander used to make escalation behavior visible."""

    def review(self, escalation: dict[str, Any]) -> tuple[bool, str]:
        task: Task = escalation["task"]
        route: RouteProposal | None = escalation.get("route")
        reasons: list[str] = escalation["reasons"]
        if task.confidence < 0.65 and task.severity >= 4:
            return False, "Denied: high-impact action is based on low-confidence evidence."
        if route and route.blocked:
            return False, "Denied: selected route is blocked by current hazard model."
        if "all routes blocked" in reasons:
            return False, "Denied: no route is currently acceptable; request replan."
        return True, "Approved: urgency justifies controlled dispatch with commander awareness."


class CommandCenterAgent(Agent):
    """Runs contract-net coordination and applies safety gates."""

    route_risk_escalation = 0.60
    low_confidence_threshold = 0.65
    disagreement_gap = 35.0

    def __init__(
        self,
        board: Blackboard,
        bus: MessageBus,
        medical: MedicalAgent,
        logistics: LogisticsAgent,
        routing: RoutingAgent,
        human: HumanApprover,
    ) -> None:
        super().__init__("command_center", board, bus)
        self.medical = medical
        self.logistics = logistics
        self.routing = routing
        self.human = human

    def absorb_inbound(self) -> None:
        for message in self.bus.to(self.name, "task.created", "hazard.update"):
            if message.type == "task.created":
                task = Task(**message.payload)
                if task.task_id not in self.board.tasks:
                    self.board.add_task(task)
            elif message.type == "hazard.update":
                self.board.add_hazard(message.payload["location"], message.payload)

    def announce_and_collect(self, task: Task) -> None:
        self.send("all_specialists", "task.announce", task.__dict__, f"incident-{task.task_id}", priority=task.severity)

        for agent in (self.medical, self.logistics):
            bid = agent.bid_on(task)
            if bid:
                self.board.add_bid(bid)
                agent.send("command_center", "bid.submit", bid.__dict__, f"incident-{task.task_id}", priority=task.severity)

        self.routing.publish_routes(task)
        for message in self.bus.by_trace(f"incident-{task.task_id}"):
            if message.type in {"route.propose", "route.veto"}:
                proposal = RouteProposal(**message.payload)
                if proposal not in self.board.routes.get(task.task_id, []):
                    self.board.add_route(proposal)

    def coordinate_open_tasks(self) -> None:
        self.absorb_inbound()
        open_tasks = sorted(
            (task for task in self.board.tasks.values() if task.status == "open"),
            key=lambda task: (-task.severity, task.confidence),
        )
        for task in open_tasks:
            self.announce_and_collect(task)
            self.decide(task)

    def decide(self, task: Task) -> None:
        bids = self.board.bids.get(task.task_id, [])
        routes = self.board.routes.get(task.task_id, [])
        viable_routes = [route for route in routes if not route.blocked]
        if not bids:
            self.block(task, "No capable agent bid on task.")
            return
        if not viable_routes:
            self.escalate_or_block(task, max(bids, key=lambda b: b.utility), None, ["all routes blocked"])
            return

        selected_bid = max(bids, key=lambda bid: bid.utility - bid.risk * 20 - bid.cost)
        selected_route = min(viable_routes, key=lambda route: route.risk * 100 + route.travel_minutes)
        reasons = self.safety_reasons(task, selected_bid, selected_route, bids)

        if reasons:
            self.escalate_or_block(task, selected_bid, selected_route, reasons)
            return

        self.award(task, selected_bid, selected_route, human_outcome=None)

    def safety_reasons(
        self,
        task: Task,
        bid: Bid,
        route: RouteProposal,
        bids: list[Bid],
    ) -> list[str]:
        reasons = []
        if task.confidence < self.low_confidence_threshold:
            reasons.append("low confidence")
        if route.risk > self.route_risk_escalation and task.severity >= 4:
            reasons.append("high route risk")
        reasons.extend(self.board.violates_reserve(bid.resource_impact))
        utilities = sorted((candidate.utility for candidate in bids), reverse=True)
        if len(utilities) >= 2 and utilities[0] - utilities[1] > self.disagreement_gap:
            reasons.append("large specialist utility disagreement")
        return reasons

    def escalate_or_block(
        self,
        task: Task,
        bid: Bid,
        route: RouteProposal | None,
        reasons: list[str],
    ) -> None:
        escalation = {"task": task, "bid": bid, "route": route, "reasons": reasons}
        self.board.escalations.append(
            {
                "task_id": task.task_id,
                "agent": bid.agent,
                "route": route.route_id if route else None,
                "reasons": reasons,
            }
        )
        self.send(
            "human_approver",
            "escalation.request",
            {
                "task_id": task.task_id,
                "agent": bid.agent,
                "route": route.route_id if route else None,
                "reasons": reasons,
            },
            f"incident-{task.task_id}",
            priority=task.severity,
            requires_ack=True,
        )
        approved, rationale = self.human.review(escalation)
        if approved and route:
            self.human.send("command_center", "approval.grant", {"task_id": task.task_id, "rationale": rationale}, f"incident-{task.task_id}", priority=task.severity)
            self.award(task, bid, route, human_outcome=rationale)
            return

        self.human.send("command_center", "approval.deny", {"task_id": task.task_id, "rationale": rationale}, f"incident-{task.task_id}", priority=task.severity)
        self.block(task, rationale, selected_agent=bid.agent, route_id=route.route_id if route else None, human_outcome=rationale)

    def award(
        self,
        task: Task,
        bid: Bid,
        route: RouteProposal,
        human_outcome: str | None,
    ) -> None:
        self.board.apply_resource_impact(bid.resource_impact)
        decision = Decision(
            task_id=task.task_id,
            status="awarded",
            selected_agent=bid.agent,
            route_id=route.route_id,
            utility=bid.utility,
            risk=max(bid.risk, route.risk),
            rationale=f"Awarded via contract net: {bid.rationale}; route: {route.rationale}",
            human_required=human_outcome is not None,
            human_outcome=human_outcome,
        )
        self.board.add_decision(decision)
        self.send("blackboard", "decision.award", decision.__dict__, f"incident-{task.task_id}", priority=task.severity)

    def block(
        self,
        task: Task,
        rationale: str,
        selected_agent: str | None = None,
        route_id: str | None = None,
        human_outcome: str | None = None,
    ) -> None:
        decision = Decision(
            task_id=task.task_id,
            status="blocked",
            selected_agent=selected_agent,
            route_id=route_id,
            utility=0,
            risk=1,
            rationale=rationale,
            human_required=human_outcome is not None,
            human_outcome=human_outcome,
        )
        self.board.add_decision(decision)
        self.send("blackboard", "decision.blocked", decision.__dict__, f"incident-{task.task_id}", priority=task.severity)
