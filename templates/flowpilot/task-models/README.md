# Task Models

Put task-local FlowGuard models here when the target software behavior needs
model-first validation.

Use this directory for:

- stateful workflows;
- retries, queues, caches, deduplication, or idempotency;
- module-boundary contracts;
- recovery and rollback behavior;
- repeated bug classes.

Each model should include:

- explicit input and state types;
- function blocks represented as `Input x State -> Set(Output x State)`;
- hard invariants;
- scenario, progress, loop, and stuck checks where relevant;
- notes on skipped conformance replay, if replay is not practical.
