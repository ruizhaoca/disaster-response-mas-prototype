import unittest

from disaster_mas.messages import MessageBus
from disaster_mas.simulation import run_demo


class DisasterMasSafetyTests(unittest.TestCase):
    def test_low_confidence_bridge_incident_is_blocked(self) -> None:
        board, _ = run_demo()
        bridge_decision = next(
            decision for decision in board.decisions if decision.task_id == "task-bridge-collapse"
        )

        self.assertEqual(bridge_decision.status, "blocked")
        self.assertTrue(bridge_decision.human_required)
        self.assertIn("low-confidence", bridge_decision.human_outcome)

    def test_committed_awards_preserve_resource_floors(self) -> None:
        board, _ = run_demo()

        for resource, floor in board.reserve_floor.items():
            self.assertGreaterEqual(board.inventory[resource], floor, resource)

    def test_messages_stay_inside_declared_contract(self) -> None:
        _, bus = run_demo()
        allowed = MessageBus.allowed_types

        self.assertTrue(bus.messages)
        for message in bus.messages:
            self.assertIn(message.type, allowed)
            self.assertGreaterEqual(message.priority, 1)
            self.assertLessEqual(message.priority, 5)
            self.assertTrue(message.trace_id.startswith("incident-"))


if __name__ == "__main__":
    unittest.main()
