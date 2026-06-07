# FlowPilot

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="FlowPilot concept hero image showing FlowGuard state models, packet mail, role gates, and router cadence" width="100%" />
</p>

<p align="center">
  <img src="./assets/brand/flowpilot-icon-default.png" alt="FlowPilot red-purple rounded hexagram icon" width="132" />
</p>

<p align="center">
  <strong>A FlowGuard-built project-control layer for long AI-agent software work.</strong><br />
  <span>Built with FlowGuard models, sealed packet mail, role authority, startup intake, and completion ledgers for disciplined agent runs.</span>
</p>

<p align="center">
  Source version: <strong>v0.10.5</strong> · MIT License · Codex skill source package
</p>
<!-- README HERO END -->

English comes first. The second half is a full Chinese mirror.

FlowPilot is an opt-in Codex skill and local runtime for substantial AI-agent-led software projects. It is built with FlowGuard as its executable modeling foundation, not as a generic planning prompt. It gives an agent a persistent route, router-owned lifecycle, sealed packet handoffs, role-separated work, FlowGuard model gates, startup intake, patrol/manual-resume continuity, and a final completion ledger.

The practical goal is simple: make it harder for a long AI run to drift, skip gates, resume from guesswork, accept stale evidence, merge unreviewed work, or declare completion before the route-wide evidence supports it.

## Product Preview

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot expanded desktop startup intake window with the background collaboration toggle above the work request field and no visible scrollbar" width="760" />
</p>

The startup intake UI captures the user's work request and whether FlowPilot may use host-supported background collaboration for isolated role work. Manual continuation and chat route signs are fixed startup defaults. The request body is sealed into the PM intake packet; the Controller sees only envelope and hash metadata.

## Current Status

| Field | Value |
| --- | --- |
| Source version | `v0.10.5` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| Release shape | source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | real `flowguard` Python package |
| Current UI surface | Windows WPF startup intake dialog for work request and background collaboration; chat route signs after startup |
| Visual identity | `assets/brand/flowpilot-icon-default.png` |

`v0.10.5` keeps packet/result contracts as the runtime source of truth and makes `open-packet` deliver every authorized input material for the assigned role. Required sealed result/report bodies still have current-run hashes and role-scoped receipts, but normal work no longer depends on a separate `open-result` micro-step.

## What FlowPilot Is

FlowPilot is a control layer around an AI coding agent. The language model still does the semantic work: reading materials, writing code, reviewing artifacts, using tools, and explaining tradeoffs. FlowPilot controls the project process around that work:

- which run, route, node, and frontier are current;
- which transition is legal now;
- which role may plan, execute, review, model, approve, repair, or stop;
- which packet or role output is authoritative;
- which child skill or companion capability is required for a node;
- which evidence is fresh, stale, superseded, waived, blocked, or missing;
- how patrol or manual resume re-enters the current route;
- when final completion is allowed.

The core product is therefore not a checklist. It is a file-backed project controller with routes, packets, roles, FlowGuard models, ledgers, and validation gates.

## Why It Exists

Long AI-agent projects tend to fail in predictable ways:

- the agent treats chat history as the control surface;
- a continuation guesses the next step from memory;
- one role plans, implements, reviews, and approves its own work;
- evidence from an earlier route segment remains trusted after later changes;
- runtime role assistance or child skills return work without clean ownership;
- completion is declared because local edits exist, not because the final ledger is clear.

FlowPilot replaces informal discipline with explicit runtime objects. The router owns the next legal action, packets preserve handoff boundaries, roles separate authority, FlowGuard checks risky process and product paths, and the terminal ledger blocks premature closure.

## Four Control Pillars

| Pillar | What it does | Why it matters |
| --- | --- | --- |
| FlowGuard finite-state simulation | Models the development process and, when needed, target product/function behavior as executable finite-state systems. | Turns "the agent should be careful" into states, transitions, invariants, progress checks, and counterexample traces. |
| Sealed packet mail | Moves work through packet envelopes and sealed bodies with hashes, holder state, role origin, and controller relay rules. | Prevents authority collapse where the same context plans, executes, reviews, and accepts its own work. |
| Role authority | Separates Project Manager, Human-like Reviewer, FlowGuard operator, requested worker responsibilities, and Controller duties. | Makes approval and challenge visible instead of blending them into one prompt. |
| Router rhythm | Uses a prompt-isolated router for startup, next action selection, packet loop re-entry, status projection, patrol, resume, and terminal closure. | Keeps continuation tied to current run state instead of model memory or a stale conversation. |

These pillars are meant to work together. FlowGuard gives the route a state model, packet mail preserves clean handoffs, roles keep authority separated, and the router controls cadence.

## Lifecycle At A Glance

```text
startup intake
  -> run shell and flowpilot_new.py lifecycle guard
  -> PM material understanding
  -> reviewer startup fact review
  -> route and frontier
  -> FlowGuard process/product gates when required
  -> packeted worker execution
  -> review, repair, route redesign, or stale-evidence reset
  -> terminal backward replay
  -> final completion ledger
```

The Controller is intentionally narrow. It may relay envelopes, scan router-owned status, write receipts, and show public route signs. It must not read sealed bodies, perform worker tasks, approve gates, or repair route logic from its own judgment.

## FlowGuard In FlowPilot

FlowPilot is developed using the real [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) package, and it also depends on that package at runtime. FlowGuard appears in two layers:

| Layer | What it models | Typical checks |
| --- | --- | --- |
| FlowGuard operator process model | startup gates, material intake, route creation, packet handoff, role authority, patrol/manual resume, route redesign, final ledger, and closure | no skipped startup, no controller body access, no stale route advance, no completion before approval |
| FlowGuard operator product/function model | the product or workflow being built: inputs, state, outputs, side effects, failure cases, and acceptance behavior | no "technically done" result that misses the user's actual workflow, state contract, or risk scenarios |

FlowGuard counterexamples are design feedback. If a route can skip review, reuse stale evidence, or complete without the right gate, the route or protocol should change before the work is treated as safe.

## When To Use FlowPilot

Use FlowPilot for project-scale AI work where process control matters:

- multi-step implementation or refactor projects;
- work that needs runtime role assistance or role separation;
- tasks that need FlowGuard modeling, human-like review, or child-skill gates;
- projects where patrol, resume, or host-supported continuation must preserve current-run state;
- work where final completion needs a route-wide ledger rather than a local "done" feeling.

Do not use FlowPilot for ordinary Q&A, tiny edits, simple one-file changes, casual brainstorming, or work where a smaller FlowGuard model or normal planning prompt is enough.

## Quick Start

Recommended human-facing path:

1. Open a fresh AI agent or CLI window that supports local tools.
2. If the host has a Goal/target option, turn it on and set the goal to keep using FlowPilot until FlowPilot reaches a terminal state, asks for user input, or explicitly says to stop.
3. Ask the agent to install FlowPilot:

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Also install and verify its required FlowGuard dependency.
```

4. Start actual project work with only:

```text
Use FlowPilot.
```

5. When the startup intake dialog opens, type the real project request there and click OK. Choose whether background collaboration is allowed if that option is shown.
6. Keep the agent running until FlowPilot says the route is complete, asks for user input, or explicitly says to stop.

From a local checkout:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

Check without changing installed skills:

```powershell
python scripts\install_flowpilot.py --check
```

Refresh repository-owned installed skill copies from this checkout:

```powershell
python scripts\install_flowpilot.py --sync-repo-owned
```

## Required External Dependency

FlowPilot itself is this repository, so it is not listed as its own dependency.
For a user-facing install, the required external dependency to know about is
FlowGuard.

| Required external dependency | Why it is needed | Public source |
| --- | --- | --- |
| `flowguard` | Real Python package and FlowGuard modeling engine used by FlowPilot gates and validation | `https://github.com/liuyingxuvka/FlowGuard` |

`flowpilot.dependencies.json` is the installer-readable source of truth, and
[Dependency sources](docs/dependency_sources.md) gives the longer installer
policy. That manifest may name installer-managed skill copies or host-specific
capabilities, but those are not separate user-facing install choices. Optional
companion skills are selected by a FlowPilot route only when that route actually
needs them.

## Verification

Routine checkout checks:

```powershell
python scripts\check_install.py
python scripts\audit_local_install_sync.py
python scripts\smoke_flowpilot.py
```

Layered test runner:

```powershell
python scripts\run_test_tier.py --tier fast --json
python scripts\run_test_tier.py --tier router --json
```

For heavier router-route validation:

```powershell
python scripts\run_test_tier.py --tier router-route --background --background-dir tmp\flowguard_background --background-max-parallel 4 --json
```

Before a public release:

```powershell
python scripts\check_public_release.py
```

Release tooling is intentionally scoped to this repository. It must not commit, tag, push, package, upload, or publish companion skill repositories.

## Documentation Map

- [Project brief](docs/project_brief.md)
- [Protocol](docs/protocol.md)
- [Schema](docs/schema.md)
- [Verification](docs/verification.md)
- [Design decisions](docs/design_decisions.md)
- [Startup intake UI integration](docs/startup_intake_ui_integration_plan.md)
- [FlowGuard model mesh plan](docs/flowguard_model_mesh_plan.md)
- [FlowGuard model-test alignment](docs/flowguard_model_test_alignment.md)
- [Dependency sources](docs/dependency_sources.md)

## Repository Map

| Path | Purpose |
| --- | --- |
| `skills/flowpilot/` | Codex skill and prompt-isolated runtime assets |
| `skills/flowpilot/assets/flowpilot_new.py` | Fresh formal runtime entrypoint, lifecycle guard, and packet loop driver |
| `skills/flowpilot/assets/packet_runtime.py` | Packet mail runtime |
| `skills/flowpilot/assets/role_output_runtime.py` | Typed role-output runtime |
| `templates/flowpilot/` | File-backed run, route, packet, evidence, patrol, and closure templates |
| `simulations/` | FlowGuard models and regression result files |
| `scripts/` | Install, check, packet, role-output, test-tier, and release validation scripts |
| `examples/minimal/` | Minimal adoption example |
| `docs/` | Protocol, schema, verification, design, and migration notes |

## Public Boundary

This public repository should include FlowPilot source, skill source, templates, docs, examples, public-safe validation artifacts, and README assets. It should not include live private run bodies, sealed packet contents from real projects, credentials, local Codex state, local machine state, personal project handoff records, or unpublished companion-skill release material.

Generated runs live under `.flowpilot/` and local validation outputs may live under `tmp/`; those are local working artifacts, not public README evidence.

## What FlowPilot Is Not

FlowPilot is not a general TODO app, a prompt collection, an autonomous guarantee, a FlowGuard replacement, or a universal project manager. It is a local control system for AI-agent software work where the extra protocol cost is justified by risk, length, or coordination complexity.

## License

MIT License. See [LICENSE](LICENSE).

---

# FlowPilot 中文说明

**Source version:** `v0.10.5`
**许可证：** MIT  
**发布形态：** Codex skill source package，不是二进制 app bundle。

FlowPilot 是一个显式 opt-in 的 Codex skill 和本地 runtime，用于较大的 AI-agent 软件项目。它是使用 FlowGuard 开发的，并以 FlowGuard 作为可执行建模基础；它不是普通规划 prompt。它给 agent 一个持久 route、router-owned lifecycle、sealed packet handoff、角色分离、FlowGuard model gate、startup intake、patrol/manual-resume continuity 和 final completion ledger。

目标很直接：让长时间 AI run 更难漂移、更难跳过 gate、更难靠猜测 resume、更难接受过期证据、更难合并未审查工作，也更难在 route-wide evidence 不充分时宣布完成。

## 产品预览

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot expanded desktop startup intake window with the background collaboration toggle above the work request field and no visible scrollbar" width="760" />
</p>

Startup intake UI 把用户请求以及是否允许 FlowPilot 使用当前 host 支持的后台协作写入文件。Manual continuation 和 chat route signs 是固定 startup defaults。请求正文封存在 PM intake packet 里；Controller 只看到 envelope 和 hash 元数据。

## 当前状态

| 字段 | 值 |
| --- | --- |
| Source version | `v0.10.5` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| 发布形态 | source package only，没有 binary app bundle |
| 首个具体 host | Codex-compatible skill runtime |
| 必需核心依赖 | 真实 `flowguard` Python package |
| 当前 UI surface | Windows WPF startup intake dialog，用于 work request 和 background collaboration；startup 后使用 chat route signs |
| 视觉标识 | `assets/brand/flowpilot-icon-default.png` |

`v0.10.5` 继续把 packet/result contract 作为 runtime 的单一事实来源，并让 `open-packet` 直接交付该角色被授权读取的输入材料。必需的 sealed result/report body 仍然有 current-run hash 和 role-scoped receipt，但正常工作不再依赖额外的 `open-result` 微动作。

## 它是什么

FlowPilot 是 AI coding agent 外面的一层控制系统。语言模型仍然负责语义工作：读材料、写代码、审查 artifact、用工具、解释取舍。FlowPilot 控制这些工作周围的项目流程：

- 当前 run、route、node、frontier 是什么；
- 当前哪种 transition 合法；
- 哪个角色可以 plan、execute、review、model、approve、repair 或 stop；
- 哪个 packet 或 role output 是权威来源；
- 哪个 child skill 或 companion capability 是某个节点必需的；
- 哪些证据是 fresh、stale、superseded、waived、blocked 或 missing；
- patrol 或 manual resume 如何重新进入当前 route；
- final completion 什么时候被允许。

所以它不是 checklist，而是一个 file-backed project controller：有 route、packet、role、FlowGuard model、ledger 和 validation gate。

## 为什么需要它

长 AI-agent 项目常见失败模式包括：

- 把 chat history 当成控制面；
- continuation 依赖模型记忆猜下一步；
- 同一个上下文负责计划、实现、审查和批准；
- 后续改动发生后，旧证据仍被信任；
- runtime role 或 child skill 返回工作但 ownership 不清；
- 因为本地有改动就宣布完成，而不是因为 final ledger 真的清空。

FlowPilot 用显式 runtime object 替代口头纪律。Router 决定下一个合法动作，packet 保留 handoff boundary，role 分离权威，FlowGuard 检查高风险 process/product 路径，terminal ledger 阻止过早关闭。

## 四个控制支柱

| 支柱 | 做什么 | 为什么重要 |
| --- | --- | --- |
| FlowGuard 有限状态模拟 | 把开发流程以及必要时的产品/功能行为建成可执行有限状态系统。 | 把“小心一点”变成 state、transition、invariant、progress check 和 counterexample trace。 |
| Sealed packet mail | 用带 hash、holder state、role origin 和 controller relay rule 的 envelope/sealed body 传递工作。 | 防止一个上下文同时计划、执行、审查和接受自己的工作。 |
| Role authority | 分离 PM、Human-like Reviewer、FlowGuard operator、按需 worker responsibility 和 Controller 职责。 | 让批准和挑战可见，而不是混进同一个 prompt。 |
| Router rhythm | 用 prompt-isolated router 管 startup、next action、packet loop re-entry、status projection、patrol、resume 和 terminal closure。 | 让 continuation 绑定当前 run state，而不是依赖模型记忆或旧对话。 |

## 生命周期概览

```text
startup intake
  -> run shell and flowpilot_new.py lifecycle guard
  -> PM material understanding
  -> reviewer startup fact review
  -> route and frontier
  -> required FlowGuard process/product gates
  -> packeted worker execution
  -> review, repair, route redesign, or stale-evidence reset
  -> terminal backward replay
  -> final completion ledger
```

Controller 的权限故意很窄：它可以 relay envelope、查看 router-owned status、写 receipt、展示 public route sign；不能读 sealed body，不能做 worker task，不能 approve gate，也不能凭自己判断修 route。

## FlowGuard 在 FlowPilot 里的位置

FlowPilot 是使用真实 [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) package 开发的，并且运行时也依赖它。FlowGuard 有两层用途：

| 层 | 建模对象 | 常见检查 |
| --- | --- | --- |
| FlowGuard operator process model | startup gate、material intake、route creation、packet handoff、role authority、patrol/manual resume、route redesign、final ledger、closure | 不跳过 startup、不让 Controller 读 body、不用 stale route 推进、不在 approval 前 completion |
| FlowGuard operator product/function model | 正在构建的产品或工作流：input、state、output、side effect、failure case、acceptance behavior | 防止“技术上完成”但漏掉用户真实 workflow、state contract 或风险场景 |

FlowGuard counterexample 是设计反馈。如果模型显示某条 route 可以跳过 review、复用 stale evidence 或没有正确 gate 就 complete，FlowPilot 应该先改 route 或 protocol。

## 什么时候使用 FlowPilot

适合这些 project-scale AI 工作：

- 多步骤实现或 refactor；
- 需要 runtime role 或 role separation；
- 需要 FlowGuard modeling、human-like review 或 child-skill gate；
- patrol、resume 或 host-supported continuation 必须保持当前 run state；
- final completion 需要 route-wide ledger，而不是局部“感觉完成”。

不要把 FlowPilot 用在普通问答、小改动、简单单文件任务、随便 brainstorm，或者一个较小 FlowGuard 模型/普通规划 prompt 就够的任务上。

## 快速开始

推荐的人类使用路径：

1. 打开一个支持本地工具的全新 AI agent 或 CLI/window。
2. 如果宿主界面有 Goal/目标 选项，就打开它，把目标设成：持续使用 FlowPilot，直到 FlowPilot 明确完成、要求用户输入，或者明确说可以停止。
3. 让 AI 安装 FlowPilot：

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Also install and verify its required FlowGuard dependency.
```

4. 真正开始项目时，只发送：

```text
Use FlowPilot.
```

5. Startup intake 对话框打开后，把真实项目请求填进去，然后点击 OK。如果界面显示是否允许 background collaboration，再按项目需要选择。
6. 之后让 AI 持续运行，直到 FlowPilot 说路线已经完成、要求用户输入，或者明确说可以停止。

本地 checkout 安装：

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

只检查、不改安装状态：

```powershell
python scripts\install_flowpilot.py --check
```

从当前 checkout 刷新 repo-owned installed skill copy：

```powershell
python scripts\install_flowpilot.py --sync-repo-owned
```

## 必需外部依赖

FlowPilot 本身就是这个仓库，所以不在表里把 `flowpilot` 再列成自己的依赖。
对用户来说，需要知道的必需外部依赖是 FlowGuard。

| 必需外部依赖 | 为什么需要 | Public source |
| --- | --- | --- |
| `flowguard` | 真实 Python package 和 FlowGuard 建模引擎，用于 FlowPilot gate 和验证 | `https://github.com/liuyingxuvka/FlowGuard` |

`flowpilot.dependencies.json` 是 installer-readable source of truth；
[Dependency sources](docs/dependency_sources.md) 里有更完整的安装器策略说明。这个
manifest 可能记录安装器管理的 skill copy 或 host-specific capability，但这些不是
用户每次手动选择的额外安装项。Optional companion skills 只有在 FlowPilot route
实际选中时才会使用。

## 验证

常规 checkout 检查：

```powershell
python scripts\check_install.py
python scripts\audit_local_install_sync.py
python scripts\smoke_flowpilot.py
```

分层测试 runner：

```powershell
python scripts\run_test_tier.py --tier fast --json
python scripts\run_test_tier.py --tier router --json
```

更重的 router-route 验证：

```powershell
python scripts\run_test_tier.py --tier router-route --background --background-dir tmp\flowguard_background --background-max-parallel 4 --json
```

公开发布前：

```powershell
python scripts\check_public_release.py
```

Release tooling 只作用于这个仓库，不应该 commit、tag、push、package、upload 或 publish companion skill repositories。

## 文档入口

- [Project brief](docs/project_brief.md)
- [Protocol](docs/protocol.md)
- [Schema](docs/schema.md)
- [Verification](docs/verification.md)
- [Design decisions](docs/design_decisions.md)
- [Startup intake UI integration](docs/startup_intake_ui_integration_plan.md)
- [FlowGuard model mesh plan](docs/flowguard_model_mesh_plan.md)
- [FlowGuard model-test alignment](docs/flowguard_model_test_alignment.md)
- [Dependency sources](docs/dependency_sources.md)

## 仓库结构

| Path | 用途 |
| --- | --- |
| `skills/flowpilot/` | Codex skill 和 prompt-isolated runtime assets |
| `skills/flowpilot/assets/flowpilot_new.py` | 新版 formal runtime entrypoint、lifecycle guard 和 packet loop driver |
| `skills/flowpilot/assets/packet_runtime.py` | Packet mail runtime |
| `skills/flowpilot/assets/role_output_runtime.py` | Typed role-output runtime |
| `templates/flowpilot/` | run、route、packet、evidence、patrol、closure 模板 |
| `simulations/` | FlowGuard 模型和 regression result files |
| `scripts/` | install、check、packet、role-output、test-tier、release validation scripts |
| `examples/minimal/` | 最小 adoption 示例 |
| `docs/` | protocol、schema、verification、design、migration notes |

## 公开边界

公开仓库应该包含 FlowPilot 源码、skill 源码、模板、文档、示例、公开安全验证 artifact 和 README 资产。它不应该包含真实项目的 live private run body、sealed packet 内容、凭证、本地 Codex 状态、本机状态、个人项目交接记录或未发布 companion-skill release material。

生成的 run 留在 `.flowpilot/`，本地验证输出可能在 `tmp/`；这些是本地工作 artifact，不是公开 README 证据。

## FlowPilot 不是什么

FlowPilot 不是通用 TODO app、prompt 集合、自治保证、FlowGuard 替代品或万能项目经理。它是一个本地控制系统，适用于风险、长度或协作复杂度足以承担额外协议成本的 AI-agent 软件工作。

## 许可证

MIT License。见 [LICENSE](LICENSE)。
