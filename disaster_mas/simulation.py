"""Runnable worked scenario for the disaster-response MAS prototype."""

from __future__ import annotations

from .agents import (
    CommandCenterAgent,
    FieldReport,
    HumanApprover,
    LogisticsAgent,
    MedicalAgent,
    RoutingAgent,
    ScoutAgent,
)
from .blackboard import Blackboard
from .messages import MessageBus


def build_system() -> tuple[Blackboard, MessageBus, ScoutAgent, CommandCenterAgent]:
    board = Blackboard()
    bus = MessageBus()
    scout = ScoutAgent("scout", board, bus)
    medical = MedicalAgent("medical", board, bus)
    logistics = LogisticsAgent("logistics", board, bus)
    routing = RoutingAgent("routing", board, bus)
    human = HumanApprover("human_approver", board, bus)
    command = CommandCenterAgent(board, bus, medical, logistics, routing, human)
    return board, bus, scout, command


def scenario_reports() -> list[FieldReport]:
    return [
        FieldReport(
            report_id="library-evac",
            location="Library Shelter",
            report_type="medical_evacuation",
            severity=5,
            confidence=0.92,
            details="Flooded shelter with injured residents and rising water.",
            requested_resources={"ambulance": 1, "med_kit": 3, "rescue_van": 1},
        ),
        FieldReport(
            report_id="clinic-generator",
            location="East Clinic",
            report_type="generator_support",
            severity=4,
            confidence=0.87,
            details="Backup generator is failing; vaccines and oxygen concentrators at risk.",
            requested_resources={"generator": 1, "fuel_can": 2},
        ),
        FieldReport(
            report_id="bridge-collapse",
            location="River Bridge",
            report_type="medical_evacuation",
            severity=4,
            confidence=0.48,
            details="Unverified call claims people are trapped near a damaged bridge.",
            requested_resources={"ambulance": 1, "med_kit": 2},
        ),
        FieldReport(
            report_id="main-street-flood",
            location="Main Street",
            report_type="route_hazard",
            severity=5,
            confidence=0.95,
            details="Water over hood height; debris moving fast.",
            requested_resources={},
        ),
    ]


def run_demo() -> tuple[Blackboard, MessageBus]:
    board, bus, scout, command = build_system()
    for report in scenario_reports():
        scout.ingest(report)

    command.coordinate_open_tasks()
    return board, bus


def print_demo(board: Blackboard, bus: MessageBus) -> None:
    print("DISASTER MAS PROTOTYPE RUN")
    print("=" * 72)
    print("\nMESSAGE TRACE")
    for message in bus.messages:
        print(f"- {message.compact()}")

    print("\nDECISIONS")
    for decision in board.decisions:
        human = f" | human: {decision.human_outcome}" if decision.human_outcome else ""
        print(
            f"- {decision.task_id}: {decision.status} "
            f"agent={decision.selected_agent} route={decision.route_id} "
            f"risk={decision.risk:.2f}{human}"
        )
        print(f"  rationale: {decision.rationale}")

    print("\nESCALATIONS")
    if not board.escalations:
        print("- none")
    for escalation in board.escalations:
        print(
            f"- {escalation['task_id']} agent={escalation['agent']} "
            f"route={escalation['route']} reasons={', '.join(escalation['reasons'])}"
        )

    print("\nINVENTORY AFTER COMMITTED AWARDS")
    for resource, amount in sorted(board.inventory.items()):
        floor = board.reserve_floor.get(resource, 0)
        print(f"- {resource}: {amount} (reserve floor {floor})")

    print("\nAUDIT LOG")
    for entry in board.audit_log:
        print(f"- {entry}")


def main() -> None:
    board, bus = run_demo()
    print_demo(board, bus)


if __name__ == "__main__":
    main()
