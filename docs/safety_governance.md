# Safety And Governance Evidence

This file is focused evidence for the safety/governance requirement. The README gives the design story; this document maps safety controls to the prototype behavior and known failure cases.

## Safety Claims

| Claim | Prototype evidence |
| --- | --- |
| High-risk decisions do not auto-commit. | `CommandCenterAgent.escalate_or_block` sends `escalation.request` before committing an award. |
| Humans can deny unsafe or uncertain actions. | `HumanApprover.review` denies low-confidence high-impact tasks and blocked routes. |
| Audit logs preserve decision context. | `Blackboard.audit_log` records tasks, hazards, bids, routes, decisions, and human outcomes. |
| Resource floors prevent silent depletion. | `Blackboard.violates_reserve` checks award impacts before commitment. |
| Unsafe routes can veto otherwise attractive tasks. | `RoutingAgent` emits `route.veto`; command ignores blocked routes for awards. |

## Human-In-The-Loop Controls

The command center escalates when any of these conditions are true:

- Task confidence is below `0.65`.
- Severity is high and route risk is above `0.60`.
- A bid would push inventory below a reserve floor.
- All routes are blocked.
- Specialist bids disagree by more than the configured utility gap.

The human approver can:

- Grant approval, allowing command to commit the award.
- Deny approval, causing command to mark the task as blocked.
- Provide rationale, which is copied into the decision and audit trail.

The sample run shows both outcomes:

- `task-library-evac` is escalated and approved.
- `task-bridge-collapse` is escalated and denied because the evidence is low confidence and the action is high impact.

## Audit Log

The audit log is append-only within the prototype run. It captures:

- Task creation.
- Hazard updates.
- Specialist bids and bid scores.
- Route proposals and route vetoes.
- Final award or blocked decisions.
- Human approval or denial rationale.

Operationally, this supports after-action review: a commander can reconstruct why a task was awarded, which route was selected, whether a human approved it, and which resources were consumed.

## Rollback Model

The prototype uses a two-step commit model:

1. Command computes a candidate award from bids and routes.
2. Safety gates and human review run before `apply_resource_impact`.

If a human denies the escalation, no resource mutation occurs and the task is marked `blocked`. This is visible in the bridge scenario: the bridge evacuation requests an ambulance, but the inventory remains at its reserve floor because the denied action is not committed.

For a production version, rollback would be extended with:

- Decision IDs and idempotency keys.
- Compensating actions for dispatch cancellation.
- Snapshotting inventory before each committed award.
- A `decision.reversed` message type with human rationale.

## Abuse And Failure Cases

| Failure or abuse case | Risk | Current mitigation | Residual risk |
| --- | --- | --- | --- |
| Fake incident report | Resources can be diverted from real victims. | Low confidence triggers human escalation for high-impact tasks. | Sophisticated fake reports may appear high confidence without source authentication. |
| Unsafe route selected | Responders may be sent into floodwater or debris. | Routing veto blocks high-risk routes; command selects only viable routes. | The route model is mocked and could be stale. |
| Resource depletion | A single task can consume last critical asset. | Reserve-floor checks escalate or block awards. | Reserve floors are static and may need incident-specific tuning. |
| Confirmation cascade | Agents repeat uncertain information until it sounds confirmed. | Confidence remains attached to task payloads and safety gates use original confidence. | Production agents need provenance tracking across all derived facts. |
| Over-escalation | Human commander becomes bottlenecked. | Escalation reasons are explicit and measurable. | Thresholds need tuning against real workload data. |
| Bid gaming or bad calibration | A specialist can overstate utility. | Bid rationale, risk, cost, and resource impact are audited. | Production needs calibration monitoring and anomaly detection. |
| Stale hazards | New flood data arrives after route selection. | Route bids are recomputed from current blackboard state during coordination. | Long-running dispatches need live route revalidation. |

## Evaluation Hooks

The existing test suite checks:

- Low-confidence bridge incident is blocked.
- Committed awards preserve reserve floors.
- Messages stay within the declared contract.

Additional production-grade evaluations should measure:

- Escalation precision and recall.
- Time from task creation to award or block.
- Frequency of route veto overrides.
- Human approval burden per operational hour.
- Calibration of bid utility against actual outcomes.
- Audit completeness during incident replay.

## Governance Boundary

The command center is the accountable authority in the prototype. Specialist agents can propose, bid, and veto, but they cannot independently dispatch resources. This keeps the MAS useful while preserving a clear chain of responsibility.
