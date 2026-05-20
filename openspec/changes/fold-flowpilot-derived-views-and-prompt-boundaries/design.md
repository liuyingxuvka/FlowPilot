## Context

FlowPilot already has separate physical ledgers for Controller actions, scheduler rows, packet lifecycle, system-card returns, role outputs, and terminal records. Recent changes added a shared closure kernel and several registry authorities, but remaining callers still carry local status lists or hand-written maps that can drift from those authorities.

The prompt runtime also has a prompt store and shared ACK policy assets, while many card markdown files repeat nearly identical boundary text. Those repetitions are behavior-bearing because they tell roles what counts as completion, what path may return formal outputs, and what source controls the next step.

## Goals / Non-Goals

**Goals:**

- Fold remaining lifecycle blocking decisions through shared closure classification at the blocker/wait boundary.
- Keep registry JSON files and owner modules as the authorities for control transactions, route actions, output contracts, and prompt policies.
- Preserve compatibility exports from `flowpilot_router.py` and existing public command behavior.
- Make prompt boundary wording centrally checked so card updates do not require manual same-text edits across every card.
- Run focused tests first, then background heavyweight FlowGuard regressions with the repository's artifact contract.
- Synchronize the installed local FlowPilot skill only after source validation passes.

**Non-Goals:**

- Do not merge physical ledgers into one table.
- Do not remove `flowpilot_router.py` as the public compatibility facade.
- Do not rename schema values, event names, ledger shapes, card ids, or CLI commands.
- Do not let ACK receipt satisfy semantic work, role-output, reviewer, officer, or PM decision completion.
- Do not expand Reviewer, Officer, Worker, Controller, or PM authority.
- Do not push, tag, publish, or create a remote release.

## Decisions

### Decision 1: Fold decisions, not storage

The implementation will replace remaining local lifecycle predicates with calls into the closure kernel where Router asks whether progress is blocked. The underlying ledgers remain separate because they encode different authorities: signed artifacts, Controller receipts, passive waits, packet ownership, and semantic role outputs.

Alternative considered: physically merge pending returns, scheduler rows, and controller actions into a single lifecycle table. Rejected because that would blur authority and privacy boundaries and would require broad migration of existing run artifacts.

### Decision 2: Registry owner modules derive compatibility views

Control transaction maps and route action maps should be derived or housed by their registry owner modules, then exported through the facade for compatibility. `flowpilot_router.py` should not own hand-maintained policy tables that duplicate runtime kit registries.

Alternative considered: leave constants in the facade and add comments. Rejected because comments do not stop drift between JSON registries, tests, and code.

### Decision 3: Contract bindings stay registry-first with Python fallback only where needed

Role-output runtime specs should prefer `contract_index.json` runtime binding fields. Python-built specs may remain temporarily for legacy aliases or complex defaults, but tests must make the remaining fallback visible so it does not grow unnoticed.

Alternative considered: move every field into JSON in one pass. Deferred because some runtime defaults are procedural and need focused migration tests before becoming pure data.

### Decision 4: Prompt cards use shared policy assets and checks

Prompt boundary policy should be encoded as shared prompt assets and validated against the card manifest. Role-specific card bodies can still contain domain instructions, but common headers about ACK, Router authority, output submission, sealed-body boundaries, and live context freshness should be generated, referenced, or mechanically checked from one policy source.

Alternative considered: manually normalize every markdown card. Rejected because it would be expensive to maintain and easy to drift again.

## Risks / Trade-offs

- Local predicate replacement could accidentally clear a wait too early -> add negative tests where unknown, identity-mismatched, or evidence-missing rows remain blocking.
- Registry derivation could break imports that expect facade constants -> keep facade compatibility aliases and add export equality tests.
- Prompt policy centralization could weaken role-specific warnings -> keep role-specific card bodies intact and only centralize common boundary language.
- Background regressions can produce progress logs before final results -> count only exit artifacts and meta JSON completion status as evidence.
- Peer-agent changes can stale validation -> re-check git status and touched paths before staging or committing.

## Migration Plan

1. Add focused FlowGuard/process evidence for the new derived-view and prompt-boundary contracts.
2. Convert remaining local lifecycle blockers to closure-kernel calls without changing ledger schemas.
3. Move route/control derived maps to registry owner modules and preserve facade exports.
4. Add prompt-policy assets/checks before touching many card files.
5. Run focused tests and then heavyweight background checks.
6. Sync installed FlowPilot skill and verify content freshness.
7. Commit only this change's files locally, leaving unrelated peer changes untouched.
