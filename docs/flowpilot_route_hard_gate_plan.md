# FlowPilot Route Hard Gate Plan

## Optimization Checklist

| Step | Plain-language goal | Owner of content judgment | Router hard gate |
| --- | --- | --- | --- |
| 1 | Product Officer produces the product behavior model before PM route drafting. | Product FlowGuard Officer | Route draft requires a product model report. |
| 2 | PM route must be reviewed against the product behavior model. | Product FlowGuard Officer / Reviewer | Route activation requires a passed route-product review report. |
| 3 | Process Officer gives a route viability verdict. | Process FlowGuard Officer | Route activation requires `process_viability_verdict=pass`. |
| 4 | PM cannot ignore `repair_required` or `blocked` process verdicts. | PM decides the repair/stop path from officer evidence. | Non-pass verdicts cannot unlock route activation. |
| 5 | Repair nodes define how they return to the mainline. | PM proposes; Process Officer validates. | Route mutation requires a return target and forces fresh route checks before execution continues. |
| 6 | Repair route is checked again before returning to work. | Process FlowGuard Officer, then Product Officer / Reviewer as needed. | Current-node work is blocked until the changed route passes the route checks again. |

## Risk Checklist

| Risk | What could go wrong | FlowGuard must catch |
| --- | --- | --- |
| R1 | PM drafts a route before the Product Officer model exists. | Missing product model before route draft or route activation. |
| R2 | PM claims the route follows the model but no qualified role checked it. | Route activation without product-model review pass. |
| R3 | Process Officer never gives a route viability verdict. | Route activation without process verdict. |
| R4 | Process Officer says repair is needed, but PM continues anyway. | Continuing after `repair_required`. |
| R5 | Process Officer blocks the route, but PM continues anyway. | Continuing after `blocked`. |
| R6 | A repair node is inserted but has no mainline return target. | Repair mutation without return target. |
| R7 | A repair route returns to work without a fresh Process Officer check. | Repair path without process recheck pass. |
| R8 | Router tries to judge semantic route quality itself. | Router semantic overreach. |

## Minimal Implementation Boundary

- Add only machine-checkable pass fields or report verdicts where the Router needs a gate.
- Keep semantic judgment with Product Officer, Process Officer, and Reviewer.
- Reset route-check gates after route mutation so the changed route cannot continue on stale approvals.
- Do not change the broader FlowPilot architecture or remote publishing path in this change.
