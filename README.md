# FlowPilot

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="FlowPilot concept hero image showing FlowGuard state models, packet mail, role gates, and router cadence" width="100%" />
</p>

<p align="center">
  <strong>A model-backed project-control layer for long AI-agent software work.</strong><br />
  <span>FlowGuard models, sealed packet mail, role authority, router cadence, and completion ledgers for disciplined agent runs.</span>
</p>

<p align="center">
  Source version: <strong>v0.9.6</strong> · MIT License · Codex skill source package
</p>
<!-- README HERO END -->

English comes first. The second half is a Chinese mirror.

FlowPilot is an opt-in Codex skill and local runtime for substantial AI-agent-led software projects. It is not a generic planning prompt. It gives an agent a persistent route, explicit role authority, sealed packet handoffs, FlowGuard model gates, heartbeat/manual-resume continuity, and a final completion ledger.

The practical goal is simple: make it harder for a long AI run to drift, skip gates, resume from guesswork, accept stale evidence, merge unreviewed work, or declare completion before the route-wide evidence supports it.

## Product Preview

| Canonical icon | Native startup intake UI |
| --- | --- |
| <img src="./assets/brand/flowpilot-icon-default.png" alt="FlowPilot canonical black hexagram icon" width="150" /> | <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot native startup intake UI with a work request field and toggles for background agents, scheduled continuation, and Cockpit UI" width="560" /> |

The startup intake UI captures the user's work request and startup choices as files. The request body is sealed into the PM intake packet; the Controller sees only envelope and hash metadata.

## Current Status

| Field | Value |
| --- | --- |
| Source version | `v0.9.6` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| License | MIT |
| Release shape | source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | real `flowguard` Python package |
| Required companion skills | `model-first-function-flow`, `grill-me`, `flowpilot` |
| Current UI surface | Windows WPF startup intake dialog plus chat route signs |
| Visual identity | `assets/brand/flowpilot-icon-default.png` |

`v0.9.6` focuses on route mutation safety: sibling branch replacement, replay-scope declaration, stale sibling evidence, superseded old-node packets, and final-ledger blocking after route mutation.

## What FlowPilot Is

FlowPilot is a control layer around an AI coding agent. The language model still does the semantic work: reading materials, writing code, reviewing artifacts, using tools, and explaining tradeoffs. FlowPilot controls the project process around that work:

- which run, route, node, and frontier are current;
- which transition is legal now;
- which role may plan, execute, review, model, approve, repair, or stop;
- which packet or role output is authoritative;
- which child skill or companion capability is required for a node;
- which evidence is fresh, stale, superseded, waived, blocked, or missing;
- how heartbeat or manual resume re-enters the current route;
- when final completion is allowed.

The core product is therefore not a checklist. It is a file-backed project controller with routes, packets, roles, FlowGuard models, ledgers, and validation gates.

## Why It Exists

Long AI-agent projects tend to fail in predictable ways:

- the agent treats chat history as the control surface;
- a continuation guesses the next step from memory;
- one role plans, implements, reviews, and approves its own work;
- evidence from an earlier route segment remains trusted after later changes;
- background agents or child skills return work without clean ownership;
- completion is declared because local edits exist, not because the final ledger is clear.

FlowPilot replaces informal discipline with explicit runtime objects. The router owns the next legal action, packets preserve handoff boundaries, roles separate authority, FlowGuard checks risky process and product paths, and the terminal ledger blocks premature closure.

## Four Control Pillars

| Pillar | What it does | Why it matters |
| --- | --- | --- |
| FlowGuard finite-state simulation | Models the development process and, when needed, target product or function behavior as executable finite-state systems. | Turns "the agent should be careful" into states, transitions, invariants, progress checks, and counterexample traces. |
| Sealed packet mail | Moves work through packet envelopes and sealed bodies with hashes, holder state, role origin, and controller relay rules. | Prevents authority collapse where the same context plans, executes, reviews, and accepts its own work. |
| Role authority | Separates Project Manager, Human-like Reviewer, Process FlowGuard Officer, Product FlowGuard Officer, Worker roles, and Controller duties. | Makes approval and challenge visible instead of blending them into one prompt. |
| Router rhythm | Uses a prompt-isolated router for startup, next action selection, packet loop re-entry, status projection, heartbeat, resume, and terminal closure. | Keeps continuation tied to current run state instead of model memory or a stale conversation. |

These pillars are meant to work together. FlowGuard gives the route a state model, packet mail preserves clean handoffs, roles keep authority separated, and the router controls cadence.

## Lifecycle At A Glance

```text
startup intake
  -> run shell and router state
  -> PM material understanding
  -> reviewer startup fact review
  -> route and frontier
  -> FlowGuard process/product gates when required
  -> packeted worker execution
  -> review, repair, route mutation, or stale-evidence reset
  -> terminal backward replay
  -> final completion ledger
```

The Controller is intentionally narrow. It may relay envelopes, scan router-owned status, write receipts, and show public route signs. It must not read sealed bodies, perform worker tasks, approve gates, or repair route logic from its own judgment.

## FlowGuard In FlowPilot

FlowPilot depends on the real [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) package. FlowGuard appears in two layers:

| Layer | What it models | Typical checks |
| --- | --- | --- |
| Process FlowGuard | startup gates, material intake, route creation, packet handoff, role authority, heartbeat/manual resume, route mutation, final ledger, and closure | no skipped startup, no controller body access, no stale route advance, no completion before approval |
| Product / Function FlowGuard | the product or workflow being built: inputs, state, outputs, side effects, failure cases, and acceptance behavior | no "technically done" result that misses the user's actual workflow, state contract, or risk scenarios |

FlowGuard counterexamples are design feedback. If a route can skip review, reuse stale evidence, or complete without the right gate, the route or protocol should change before the work is treated as safe.

## When To Use FlowPilot

Use FlowPilot for project-scale AI work where process control matters:

- multi-step implementation or refactor projects;
- work that needs background agents or role separation;
- tasks that need FlowGuard modeling, human-like review, or child-skill gates;
- long work that may need heartbeat or manual resume;
- projects where final completion requires route-wide evidence, not just local edits.

Do not use FlowPilot for ordinary Q&A, tiny edits, casual brainstorming, or tasks where a direct FlowGuard model or normal planning prompt is enough. FlowPilot is intentionally heavier than a lightweight TODO list.

## Quick Start

Recommended human path:

1. Open a fresh AI CLI/window that supports local tools. Background agents and heartbeat/scheduled continuation make FlowPilot stronger, but the file-backed protocol can still run with fallbacks.
2. Ask the agent to install FlowPilot and required dependencies:

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Install and verify the required dependencies too:
flowguard, model-first-function-flow, grill-me, and flowpilot itself.
```

3. Start a real project with a direct request:

```text
Use FlowPilot.
```

4. When the startup intake UI opens, put the real project request there rather than pasting the full request into chat. That keeps the raw request in the PM intake packet and limits what the Controller/router prompt surface can see.

Local checkout install:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

Check only, without changing the install:

```powershell
python scripts\install_flowpilot.py --check
```

Install optional UI/design companion skills only when a route needs them:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard --include-optional
```

## Verification

Common checkout checks:

```powershell
python scripts\check_install.py
python scripts\audit_local_install_sync.py
python scripts\smoke_autopilot.py
```

Representative FlowGuard simulation checks live under `simulations/`. Public release checks are intentionally scoped to this repository:

```powershell
python scripts\check_public_release.py
```

Release tooling must not commit, tag, push, package, upload, or publish companion skill repositories.

## Documentation Map

- [Project brief](docs/project_brief.md)
- [Protocol](docs/protocol.md)
- [Schema](docs/schema.md)
- [Verification](docs/verification.md)
- [Design decisions](docs/design_decisions.md)
- [Startup intake UI integration](docs/startup_intake_ui_integration_plan.md)
- [FlowGuard model mesh plan](docs/flowguard_model_mesh_plan.md)
- [Dependency sources](docs/dependency_sources.md)

## Repository Map

| Path | Purpose |
| --- | --- |
| `skills/flowpilot/` | Codex skill and prompt-isolated runtime assets |
| `skills/flowpilot/assets/flowpilot_router.py` | Router bootloader and action envelope driver |
| `skills/flowpilot/assets/packet_control_plane.py` | Packet/mail control-plane runtime |
| `skills/flowpilot/assets/role_output_runtime.py` | Typed role-output runtime |
| `templates/flowpilot/` | run, route, packet, evidence, heartbeat, and closure templates |
| `simulations/` | FlowGuard models and regression result files |
| `scripts/` | install, check, packet, role-output, lifecycle, release, and smoke helpers |
| `examples/minimal/` | minimal adoption example |
| `docs/` | protocol, schema, verification, design notes, and migration plans |

## Public Boundary

This public repository should include FlowPilot source, skill source, templates, docs, examples, public-safe validation artifacts, and README assets.

It should not include live private run bodies, sealed packet content from real projects, credentials, local Codex state, machine-specific state, personal handoff records, or unpublished companion-skill release material.

Generated runs belong under `.flowpilot/`. Local verification output may belong under `tmp/`. Those are local work artifacts, not public README evidence.

## What FlowPilot Is Not

FlowPilot is not a general TODO app, a prompt collection, a guarantee of autonomous correctness, a replacement for FlowGuard, or a universal project manager. It is a local control system for AI-agent software work whose risk, length, or coordination complexity justifies the extra protocol cost.

## Release History

For full engineering details, see [CHANGELOG.md](CHANGELOG.md).

| Version | Date | README summary |
| --- | --- | --- |
| `v0.9.6` | 2026-05-16 | Hardened route mutation with sibling branch replacement, replay scope, old-packet supersession, stale sibling evidence, and final-ledger blocking after route mutation. |
| `v0.9.5` | 2026-05-16 | Added recursive parent/module route entry and terminal closure reconciliation. |
| `v0.9.4` | 2026-05-16 | Added runtime-closure guards for officer lifecycle, continuation quarantine, final user report, and route-display refresh evidence. |
| `v0.9.3` | 2026-05-16 | Split router runtime helper boundaries and strengthened ACK/return settlement and terminal recovery checks. |
| `v0.9.2` | 2026-05-14 | Fixed startup intake icon packaging, ACK recovery, role-output blocker continuity, and missing-ACK quarantine coverage. |
| `v0.9.1` | 2026-05-13 | Simplified the default route skeleton to reviewer route challenge and refreshed hard-gate evidence. |
| `v0.9.0` | 2026-05-13 | Added model-driven recursive route governance, legal next action selection, PM package absorption, terminal summaries, model mesh checks, and stronger role-output authority. |

## License

MIT License. See [LICENSE](LICENSE).

---

# FlowPilot 中文说明

FlowPilot 是一个面向长周期 AI-agent 软件工作的、带模型约束的项目控制层。

## 产品预览

| Canonical icon | Native startup intake UI |
| --- | --- |
| <img src="./assets/brand/flowpilot-icon-default.png" alt="FlowPilot canonical black hexagram icon" width="150" /> | <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot native startup intake UI with a work request field and toggles for background agents, scheduled continuation, and Cockpit UI" width="560" /> |

Startup intake UI 会把用户请求和启动选项写成文件。请求正文进入 PM intake packet；Controller 只看到 envelope 和 hash metadata。

## 当前状态

| 字段 | 值 |
| --- | --- |
| Source version | `v0.9.6` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| License | MIT |
| Release shape | 只发布源码包，没有二进制 app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | 真实的 `flowguard` Python package |
| Required companion skills | `model-first-function-flow`、`grill-me`、`flowpilot` |
| Current UI surface | Windows WPF startup intake dialog，加上 chat route signs |
| Visual identity | `assets/brand/flowpilot-icon-default.png` |

`v0.9.6` 重点强化 route mutation：sibling branch replacement、replay-scope declaration、stale sibling evidence、old-node packet supersession，以及 route mutation 后的 final-ledger blocking。

## FlowPilot 是什么

FlowPilot 是 AI coding agent 外围的控制层。语言模型仍然负责语义工作：读材料、写代码、审查 artifact、使用工具、解释取舍。FlowPilot 控制的是项目过程：

- 当前 run、route、node、frontier 是什么；
- 当前哪个 transition 合法；
- 哪个 role 可以规划、执行、审查、建模、批准、修复或停止；
- 哪个 packet 或 role output 是权威证据；
- 哪个 child skill 或 companion capability 是当前 node 必需的；
- 哪些证据是 fresh、stale、superseded、waived、blocked 或 missing；
- heartbeat 或 manual resume 如何回到当前 route；
- 什么时候允许 final completion。

所以它不是 checklist，而是一个 file-backed project controller，包含 routes、packets、roles、FlowGuard models、ledgers 和 validation gates。

## 为什么需要它

长 AI-agent 项目常见失败方式很固定：

- agent 把 chat history 当成 control surface；
- continuation 靠记忆猜下一步；
- 同一个上下文同时规划、实现、审查和批准自己的工作；
- 后续改动之后，早期 route segment 的证据仍然被信任；
- background agent 或 child skill 返回结果，但 ownership 不清楚；
- 因为本地改动存在就宣布完成，而不是因为 final ledger 清了。

FlowPilot 用显式 runtime objects 替代口头纪律。Router 拥有下一个合法动作，packet 维持 handoff 边界，role 拆分 authority，FlowGuard 检查有风险的 process/product path，terminal ledger 阻止过早关闭。

## 四个控制支柱

| 支柱 | 做什么 | 为什么重要 |
| --- | --- | --- |
| FlowGuard finite-state simulation | 把开发过程，以及必要时的产品/功能行为，建成可执行有限状态系统 | 把“agent 应该小心”变成 state、transition、invariant、progress check 和 counterexample trace |
| Sealed packet mail | 用带 hash、holder state、role origin 和 relay rule 的 envelope/body 移动工作 | 防止同一个上下文规划、执行、审查并接受自己的结果 |
| Role authority | 拆分 PM、Human-like Reviewer、Process/Product FlowGuard Officer、Worker 和 Controller 职责 | 让 approval 和 challenge 可见，而不是混在一个 prompt 里 |
| Router rhythm | 用 prompt-isolated router 管 startup、next action、packet loop re-entry、status projection、heartbeat、resume 和 closure | 让 continuation 绑定当前 run state，而不是模型记忆或旧对话 |

四个部分一起工作：FlowGuard 给 route 状态模型，packet mail 保持交接干净，role 保持 authority 分离，router 控制节奏。

## 生命周期概览

```text
startup intake
  -> run shell and router state
  -> PM material understanding
  -> reviewer startup fact review
  -> route and frontier
  -> FlowGuard process/product gates when required
  -> packeted worker execution
  -> review, repair, route mutation, or stale-evidence reset
  -> terminal backward replay
  -> final completion ledger
```

Controller 有意保持很窄。它可以 relay envelope、扫描 router-owned status、写 receipt、显示公开 route sign；但不能读取 sealed body、执行 worker task、批准 gate，或凭自己的判断修 route logic。

## FlowGuard 在 FlowPilot 里的位置

FlowPilot 依赖真实的 [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) package。FlowGuard 有两层：

| 层 | 建模对象 | 常见检查 |
| --- | --- | --- |
| Process FlowGuard | startup gate、material intake、route creation、packet handoff、role authority、heartbeat/manual resume、route mutation、final ledger、closure | 不跳过 startup、不让 Controller 读 body、不用 stale route 推进、不在 approval 前 completion |
| Product / Function FlowGuard | 正在构建的产品或 workflow：input、state、output、side effect、failure case、acceptance behavior | 防止“技术上完成”但漏掉用户真实 workflow、state contract 或 risk scenario |

FlowGuard counterexample 是设计反馈。如果 route 可以跳过 review、复用 stale evidence 或没有正确 gate 就 complete，FlowPilot 应先改 route 或 protocol。

## 什么时候使用 FlowPilot

适合这些 project-scale AI 工作：

- 多步骤实现或 refactor；
- 需要 background agent 或 role separation；
- 需要 FlowGuard modeling、human-like review 或 child-skill gate；
- 可能需要 heartbeat 或 manual resume 的长任务；
- final completion 需要 route-wide evidence，而不是局部“感觉完成”。

不要把 FlowPilot 用在普通问答、小改动、随便 brainstorm，或者一个直接 FlowGuard 模型/普通 planning prompt 就够的任务上。FlowPilot 的协议成本是有意存在的。

## 快速开始

推荐的人类使用路径：

1. 打开一个支持本地工具的新 AI CLI/window。支持 background agents 和 heartbeat/scheduled continuation 会更好，但 file-backed protocol 可以降级运行。
2. 让 agent 安装 FlowPilot 和必需依赖：

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Install and verify the required dependencies too:
flowguard, model-first-function-flow, grill-me, and flowpilot itself.
```

3. 真正开始项目时直接发送：

```text
Use FlowPilot.
```

4. Startup intake UI 打开后，把真实项目请求填到 UI 里，而不是把完整请求贴进 chat。这样原始请求会进入 PM intake packet，Controller/router prompt surface 保持更窄。

本地 checkout 安装：

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

只检查，不改安装状态：

```powershell
python scripts\install_flowpilot.py --check
```

只有路线需要时才安装 optional UI/design companion skills：

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard --include-optional
```

## 验证

常规 checkout 检查：

```powershell
python scripts\check_install.py
python scripts\audit_local_install_sync.py
python scripts\smoke_autopilot.py
```

FlowGuard simulation checks 在 `simulations/` 目录。公开发布检查只作用于本仓库：

```powershell
python scripts\check_public_release.py
```

Release tooling 不应该 commit、tag、push、package、upload 或 publish companion skill repositories。

## 文档入口

- [Project brief](docs/project_brief.md)
- [Protocol](docs/protocol.md)
- [Schema](docs/schema.md)
- [Verification](docs/verification.md)
- [Design decisions](docs/design_decisions.md)
- [Startup intake UI integration](docs/startup_intake_ui_integration_plan.md)
- [FlowGuard model mesh plan](docs/flowguard_model_mesh_plan.md)
- [Dependency sources](docs/dependency_sources.md)

## 仓库结构

| Path | 用途 |
| --- | --- |
| `skills/flowpilot/` | Codex skill 和 prompt-isolated runtime assets |
| `skills/flowpilot/assets/flowpilot_router.py` | Router bootloader 和 action envelope driver |
| `skills/flowpilot/assets/packet_control_plane.py` | Packet/mail control-plane runtime |
| `skills/flowpilot/assets/role_output_runtime.py` | Typed role-output runtime |
| `templates/flowpilot/` | run、route、packet、evidence、heartbeat、closure 模板 |
| `simulations/` | FlowGuard models 和 regression result files |
| `scripts/` | install、check、packet、role-output、lifecycle、release、smoke helpers |
| `examples/minimal/` | 最小 adoption 示例 |
| `docs/` | protocol、schema、verification、design notes、migration plans |

## 公开边界

公开仓库应该包含 FlowPilot 源码、skill 源码、模板、文档、示例、公开安全验证 artifact 和 README 资产。

它不应该包含真实项目的 live private run body、sealed packet 内容、凭证、本地 Codex 状态、本机状态、个人项目交接记录或未发布 companion-skill release material。

生成的 run 留在 `.flowpilot/`。本地验证输出可能在 `tmp/`。这些是本地工作 artifact，不是公开 README 证据。

## FlowPilot 不是什么

FlowPilot 不是通用 TODO app、prompt 集合、自治正确性保证、FlowGuard 替代品或万能项目经理。它是一个本地控制系统，适用于风险、长度或协作复杂度足以承担额外协议成本的 AI-agent 软件工作。

## 版本历史

完整工程细节见 [CHANGELOG.md](CHANGELOG.md)。

| Version | Date | README 摘要 |
| --- | --- | --- |
| `v0.9.6` | 2026-05-16 | 强化 route mutation，覆盖 sibling branch replacement、replay scope、old-packet supersession、stale sibling evidence 和 final-ledger blocking。 |
| `v0.9.5` | 2026-05-16 | 增加 recursive parent/module route entry 和 terminal closure reconciliation。 |
| `v0.9.4` | 2026-05-16 | 增加 officer lifecycle、continuation quarantine、final user report 和 route-display refresh evidence 的 runtime closure guard。 |
| `v0.9.3` | 2026-05-16 | 拆分 router runtime helper 边界，并强化 ACK/return settlement 和 terminal recovery checks。 |
| `v0.9.2` | 2026-05-14 | 修复 startup intake icon packaging、ACK recovery、role-output blocker continuity 和 missing-ACK quarantine coverage。 |
| `v0.9.1` | 2026-05-13 | 简化默认 route skeleton 到 reviewer route challenge，并刷新 hard-gate evidence。 |
| `v0.9.0` | 2026-05-13 | 增加 model-driven recursive route governance、legal next action selection、PM package absorption、terminal summaries、model mesh checks 和更强 role-output authority。 |

## 许可证

MIT License。见 [LICENSE](LICENSE)。
