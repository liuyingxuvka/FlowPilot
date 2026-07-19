# Model-Miss Review: Windows Interpreter Process Owner

## Observed discrepancy

A frozen all-tier owner launched the current virtual-environment
`python.exe`. On this Windows host that executable is a short-lived launcher:
it created the real packaged Python process and exited while the requested
pytest command was still running. The background child therefore began its
descendant-settlement window before the requested command had finished. The
pytest case passed, but the outer receipt correctly failed after terminating
still-running descendants.

## Ownership decision

- The product test and its daemon cleanup were not accepted as the owner of
  this failure.
- Increasing the settlement duration again was rejected because it would blur
  the distinction between the real command owner and a detached orphan.
- The defect belongs to the existing background child process-launch boundary.
- The failed supervisor and all exact descendants were terminated with
  descendant-zero confirmation. Its evidence root remains non-reusable.

## Current-contract repair

On Windows, when the requested command begins with the current virtual-
environment interpreter and that interpreter has a distinct base executable,
the background child starts the base executable directly and sets
`__PYVENV_LAUNCHER__` to the requested interpreter. The Python process
therefore keeps the frozen virtual-environment identity while the process
tracked by the supervisor is the real long-running execution owner.

Other commands keep their exact requested executable. No alternate interpreter
is selected, no newest-version lookup occurs, and the existing bounded
descendant settlement and survivor-fails-closed behavior remain unchanged.

## Backfeed

- TestTier now rejects a Windows virtual-environment shim acting as the
  background execution owner.
- MTA's toolchain-identity obligation includes direct process ownership and a
  dedicated edge test.
- The background receipt records the requested executable, direct process-
  owner executable, and virtual-environment binding as one launch plan.
- The existing positive and negative descendant-settlement tests continue to
  distinguish normal bounded teardown from a real surviving orphan.
