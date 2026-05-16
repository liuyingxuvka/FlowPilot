## Controller Wait-Shape Action Inventory

| Action type | Classification | Controller can execute? | Runtime treatment |
|---|---|---:|---|
| `await_role_decision` | Passive wait status | No | Preserve in Router pending/current_wait/status; exclude from ordinary Controller work rows. |
| `await_card_return_event` | Passive wait status | No | Preserve ACK wait metadata in current_wait/status; exclude from ordinary Controller work rows. |
| `await_card_bundle_return_event` | Passive wait status | No | Preserve bundle ACK wait metadata in current_wait/status; exclude from ordinary Controller work rows. |
| `await_current_scope_reconciliation` | Passive reconciliation status | No | Preserve reconciliation blockers in current_wait/status; preempt it with Router-local startup obligations when available. |
| `check_card_return_event` | Executable Controller action | Yes | Keep as ordinary work row because Controller validates a returned ACK artifact. |
| `check_card_bundle_return_event` | Executable Controller action | Yes | Keep as ordinary work row because Controller validates returned bundled ACK artifacts. |
| `send_wait_target_reminder` | Executable Controller action | Yes | Generic due-reminder row for the current waiting role; Controller sends Router-authored text and receipts delivery/liveness metadata. |
| `handle_control_blocker` | Executable/relay action | Yes | Keep as ordinary work row because Controller relays or handles a concrete blocker path. |
| `controller_repair_work_packet` | Executable repair action | Yes | Keep as ordinary work row under explicit repair transaction limits. |
| `continuous_controller_standby` | Standby monitor duty | Monitor duty | Keep as the final anti-exit standby row; it is not a pure wait target and must name current_wait from monitor status. |
| `await_user_after_model_miss_stop` | User-return boundary | No ordinary progress | Leave out of this pass because it intentionally returns the foreground turn to the user through `requires_user`. |

## Rule

Only rows with a concrete Controller side effect, validation, relay, display, receipt, reminder delivery, or bounded repair action remain ordinary work rows. Passive waits stay visible through Router daemon status, current status summary, scheduler metadata, and standby/patrol output.
