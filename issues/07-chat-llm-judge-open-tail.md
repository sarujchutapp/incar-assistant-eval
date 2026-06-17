Status: ready-for-agent

# Slice 7 — LLM-as-judge for the chat open tail

## Parent

PRD #1

**Type:** AFK  ·  **GitLab:** #8  ·  **PRD user stories covered:** 37, 38, 39, 40, 41, 48, 56, 57

## What to build

Add the guarded pairwise LLM-as-judge for the open chat tail. The judge runs through the model-client port and must apply all mandatory guards: CoT-forced critique before verdict, length normalization, position-swap (run twice, swap A/B), and a judge from a different family than the target. Per-dimension diagnostics (faithfulness, relevancy, conciseness) are elicited inside the critique. Aggregate head-to-heads with Bradley-Terry plus bootstrap CIs. No bare scalar judging. Includes Role Adherence scoring against the fixed v1 persona.

## Acceptance criteria

- [ ] The judge elicits a critique before the verdict, applies length normalization, and runs pairwise twice with A/B swapped
- [ ] The judge handle is asserted to be a different family than the target
- [ ] Per-dimension diagnostics (faithfulness, relevancy, conciseness) are captured per comparison
- [ ] Head-to-heads aggregate via Bradley-Terry with bootstrap CIs (no Elo)
- [ ] Role Adherence to the fixed persona is scored
- [ ] No bare-scalar judging path exists; tests verify guards via an injected fake judge

## Blocked by

- [06-chat-objective-by-construction.md](./06-chat-objective-by-construction.md)
