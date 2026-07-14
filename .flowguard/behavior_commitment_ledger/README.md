# FlowPilot Behavior Commitment Ledger

`ledger.json` is the sole behavior-inventory authority. `model.py` is only a
thin loader; it must not rebuild commitments or source surfaces in Python.

The ledger separates product runtime, agent operation, and development process
commitments. Only commitments with a real alternate-success or authority risk
are path-sensitive. Primary Path Authority, Model-Test Alignment, TestMesh,
and release checks provide executable freshness evidence; a green ledger shape
does not replace those checks.

Run the structural ledger check with:

```powershell
python .flowguard/behavior_commitment_ledger/run_checks.py
```
