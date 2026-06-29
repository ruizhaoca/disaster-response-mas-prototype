# Sample Prototype Run

This file is captured evidence for the prototype/simulation requirement. It shows one mocked disaster-response run with typed messages, contract-net bids, routing vetoes, human escalation, a blocked unsafe/uncertain incident, and an audit trail.

Command:

```powershell
python -B -m disaster_mas.simulation
```

Sample output:

```text
DISASTER MAS PROTOTYPE RUN
========================================================================

MESSAGE TRACE
- msg-0001 scout->command_center task.created p5 trace=incident-library-evac
- msg-0002 scout->command_center task.created p4 trace=incident-clinic-generator
- msg-0003 scout->command_center task.created p4 trace=incident-bridge-collapse
- msg-0004 scout->command_center hazard.update p5 trace=incident-main-street-flood
- msg-0005 command_center->all_specialists task.announce p5 trace=incident-task-library-evac
- msg-0006 medical->command_center bid.submit p5 trace=incident-task-library-evac
- msg-0007 logistics->command_center bid.submit p5 trace=incident-task-library-evac
- msg-0008 routing->command_center route.veto p5 trace=incident-task-library-evac
- msg-0009 routing->command_center route.propose p5 trace=incident-task-library-evac
- msg-0010 command_center->human_approver escalation.request p5 trace=incident-task-library-evac
- msg-0011 human_approver->command_center approval.grant p5 trace=incident-task-library-evac
- msg-0012 command_center->blackboard decision.award p5 trace=incident-task-library-evac
- msg-0013 command_center->all_specialists task.announce p4 trace=incident-task-bridge-collapse
- msg-0014 medical->command_center bid.submit p4 trace=incident-task-bridge-collapse
- msg-0015 logistics->command_center bid.submit p4 trace=incident-task-bridge-collapse
- msg-0016 routing->command_center route.veto p4 trace=incident-task-bridge-collapse
- msg-0017 routing->command_center route.propose p4 trace=incident-task-bridge-collapse
- msg-0018 command_center->human_approver escalation.request p4 trace=incident-task-bridge-collapse
- msg-0019 human_approver->command_center approval.deny p4 trace=incident-task-bridge-collapse
- msg-0020 command_center->blackboard decision.blocked p4 trace=incident-task-bridge-collapse
- msg-0021 command_center->all_specialists task.announce p4 trace=incident-task-clinic-generator
- msg-0022 logistics->command_center bid.submit p4 trace=incident-task-clinic-generator
- msg-0023 routing->command_center route.veto p4 trace=incident-task-clinic-generator
- msg-0024 routing->command_center route.propose p4 trace=incident-task-clinic-generator
- msg-0025 command_center->blackboard decision.award p4 trace=incident-task-clinic-generator

DECISIONS
- task-library-evac: awarded agent=medical route=route-library-hill risk=0.16 | human: Approved: urgency justifies controlled dispatch with commander awareness.
  rationale: Awarded via contract net: prioritizes casualty stabilization and evacuation capacity; route: clear route
- task-bridge-collapse: blocked agent=medical route=route-bridge-north risk=1.00 | human: Denied: high-impact action is based on low-confidence evidence.
  rationale: Denied: high-impact action is based on low-confidence evidence.
- task-clinic-generator: awarded agent=logistics route=route-clinic-ring risk=0.26
  rationale: Awarded via contract net: balances dispatch usefulness against inventory reserve floors; route: clear route

ESCALATIONS
- task-library-evac agent=medical route=route-library-hill reasons=large specialist utility disagreement
- task-bridge-collapse agent=medical route=route-bridge-north reasons=low confidence, ambulance remaining 0 below reserve 1, large specialist utility disagreement

INVENTORY AFTER COMMITTED AWARDS
- ambulance: 1 (reserve floor 1)
- fuel_can: 3 (reserve floor 1)
- generator: 0 (reserve floor 0)
- med_kit: 5 (reserve floor 2)
- rescue_van: 2 (reserve floor 1)
- water_crate: 12 (reserve floor 3)

AUDIT LOG
- task opened: task-library-evac medical_evacuation at Library Shelter
- task opened: task-clinic-generator generator_support at East Clinic
- task opened: task-bridge-collapse medical_evacuation at River Bridge
- hazard updated: Main Street risk=1.0 confidence=0.95
- bid: medical on task-library-evac utility=101.04 risk=0.16
- bid: logistics on task-library-evac utility=38.08 risk=0.20
- route: route-library-main for task-library-evac risk=1.00 blocked=True
- route: route-library-hill for task-library-evac risk=0.16 blocked=False
- decision: awarded task-library-evac agent=medical route=route-library-hill risk=0.16 human=Approved: urgency justifies controlled dispatch with commander awareness.
- bid: medical on task-bridge-collapse utility=57.76 risk=0.60
- bid: logistics on task-bridge-collapse utility=7.80 risk=0.65
- route: route-bridge-direct for task-bridge-collapse risk=1.00 blocked=True
- route: route-bridge-north for task-bridge-collapse risk=0.30 blocked=False
- decision: blocked task-bridge-collapse agent=medical route=route-bridge-north risk=1.00 human=Denied: high-impact action is based on low-confidence evidence.
- bid: logistics on task-clinic-generator utility=54.90 risk=0.26
- route: route-clinic-main for task-clinic-generator risk=1.00 blocked=True
- route: route-clinic-ring for task-clinic-generator risk=0.15 blocked=False
- decision: awarded task-clinic-generator agent=logistics route=route-clinic-ring risk=0.26 human=None
```

What this demonstrates:

- The prototype is not only a static design; it runs a scripted interaction end to end.
- Agents communicate only through typed messages on the bus.
- A high-urgency task can be approved by the human commander when the route is safe enough.
- A low-confidence, high-impact bridge incident is escalated and blocked.
- Audit entries explain why resources were committed or withheld.
