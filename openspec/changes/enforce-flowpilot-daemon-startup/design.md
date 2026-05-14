## Overview

The minimal repair is to remove daemon optionality from the formal startup
path. A new formal invocation must create the run, bind any requested
scheduled continuation, and then start the run-scoped Router daemon from
startup code before `load_controller_core` can complete.

## Runtime Contract

- Formal startup owns daemon startup.
- The daemon uses the existing run-scoped lock/status/ledger files under
  `.flowpilot/runs/<run-id>/runtime/`.
- Startup treats daemon launch failure as startup failure. It does not fall
  back to a non-daemon Controller loop.
- The command-line `daemon` subcommand remains for diagnostics, bounded tests,
  stale-lock recovery, and manual repair.
- User stop and terminal closure remain the only normal paths that stop the
  daemon.

## Implementation Shape

1. Add a startup bootstrap action that is internal to the router, not a user
   option.
2. The action starts a detached daemon process for the current run and waits
   briefly until the daemon lock/status and controller action ledger exist.
3. If a live daemon lock already exists for the same run, startup attaches to
   it instead of starting a duplicate writer.
4. If a stale lock exists, startup fails with an explicit stale-daemon error;
   repair uses the existing explicit stale-lock command path.
5. Only after the daemon is live does startup proceed to Controller core.

## FlowGuard Boundary

The model should represent formal startup as:

```text
formal_startup x State -> daemon_started | startup_error
```

Protected invalid states:

- Controller core loaded before the daemon startup action is executed.
- Formal startup silently continues after daemon startup failure.
- Formal startup starts a second daemon while a live same-run daemon exists.
- Manual diagnostic commands are mistaken for formal startup.

## Non-Goals

- No new daemon-off flag.
- No new user-facing choice for daemon startup.
- No broad rewrite of the packet/card sequence.
- No change to terminal stop semantics beyond preserving daemon cleanup.
