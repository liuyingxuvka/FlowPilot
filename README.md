# FlowPilot

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="FlowPilot concept hero image showing FlowGuard state models, packet mail, role gates, and router cadence" width="100%" />
</p>

<p align="center">
  <img src="./assets/brand/flowpilot-icon-default.png" alt="FlowPilot red-purple rounded hexagram icon" width="132" />
</p>

<p align="center">
  <strong>An open-source control loop that lets AI agents work like a role-based project team.</strong><br />
  <span>FlowGuard route simulation, background role dispatch, sealed packet mail, independent review, route replanning, and completion ledgers for disciplined agent runs.</span>
</p>

<p align="center">
  Source version: <strong>v0.11.3</strong> · MIT License · open-source AI-agent control runtime
</p>
<!-- README HERO END -->

English comes first. The second half is a full Chinese mirror.

## What FlowPilot Is

FlowPilot is an opt-in, open-source control loop and local runtime for substantial AI-agent-led software projects. It turns one long AI run into a model-backed project team: a project manager plans and absorbs results, workers execute bounded packets, reviewers challenge the output, FlowGuard operators inspect process and state risk, and the Controller keeps the route tied to current runtime evidence.

The current public package is a Codex-compatible local skill runtime. The product idea is broader: give an AI agent a controllable loop it can run under human supervision, with explicit route state, role-scoped packet handoffs, model-backed checks, repair gates, and completion evidence.

It is built for work that is too long or too risky to trust to one continuous chat memory. FlowPilot gives the agent a persistent route, sealed handoff packets, host-supported background collaboration, role-separated authority, FlowGuard model gates, startup intake, patrol/manual-resume continuity, and a final completion ledger.

The language model still does the semantic work: reading materials, writing code, reviewing artifacts, using tools, and explaining tradeoffs. FlowPilot controls the process around that work so the run does not drift, skip gates, reuse stale evidence, or declare completion before the route-wide evidence supports it.

## How To Start FlowPilot

The human-facing workflow is:

1. Open an AI agent interface that can use local tools and work with your repository.
2. If the host offers a goal, target, or objective mode, turn it on.
3. Send this instruction:

```text
Formally start FlowPilot. Keep using FlowPilot and do not stop until FlowPilot reaches terminal return, asks for my input, or explicitly says stopping is allowed.
```

4. Wait for the FlowPilot startup window.
5. Put the project goal, constraints, and expected outcome into that startup window.
6. Start the run and let FlowPilot control the loop.

After startup, FlowPilot should drive the agent through route planning, role dispatch, packeted execution, review, repair, route replanning when needed, and final completion evidence.

## The Problem

Long AI-agent projects tend to fail in predictable ways:

1. The agent treats chat history as the control surface.
2. A continuation guesses the next step from memory.
3. One role plans, implements, reviews, and approves its own work.
4. Evidence from an earlier route remains trusted after later changes.
5. Background agents, child skills, or workers return output without clean ownership.
6. Completion is declared because local edits exist, not because the final ledger is clear.

FlowPilot replaces informal discipline with explicit runtime objects: route state, role bindings, sealed packets, model checks, review decisions, repair records, and ledger evidence.

## Product Preview

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot desktop startup intake window with the background collaboration toggle above the project request field and no visible scrollbar" width="760" />
</p>

The startup intake UI captures the user's work request and whether FlowPilot may use host-supported background collaboration for isolated role work. Manual continuation and chat route signs are fixed startup defaults. The request body is sealed into the PM intake packet; the Controller sees only envelope and hash metadata.

## The Role-Based Agent Team

FlowPilot's loop is not a single assistant repeatedly telling itself to continue. When the host can provide isolated role surfaces, FlowPilot can dispatch background agents into bounded responsibilities and bring their results back through the current runtime state.

| Role | Responsibility | What it cannot silently do |
| --- | --- | --- |
| Project Manager (PM) | Understand materials, design the route, issue work packets, absorb results, decide repair/replan/continue/stop | Execute worker packets or approve its own output as final evidence |
| Worker | Execute a bounded packet with the allowed files, tools, child skills, and expected output shape | Redesign the route, mark the node complete, or bypass review |
| Reviewer | Challenge PM plans, worker outputs, evidence credibility, and final completion from a human-quality perspective | Treat the PM checklist as proof without independent inspection |
| FlowGuard operator | Model process/product risk, run route simulations, inspect stale evidence and model misses | Replace the reviewer or guarantee final product correctness alone |
| Controller | Keep the current run, packet envelopes, leases, status, patrol, resume, and terminal return tied to runtime state | Read sealed bodies, infer progress from chat history, or mutate the route from memory |

This is why FlowPilot can feel like an autonomous loop without becoming a black box. The agent may keep working, but each meaningful move has an owner, a packet, a gate, and a current-state reason.

## Model First, Then Loop

FlowPilot is not just "dispatch, check, record, decide, repeat." Before the loop treats a path as safe, FlowGuard models and rehearses the expected process route. During the run, that route can be redesigned when new evidence, failed checks, changed requirements, or stale assumptions make the old path unsafe.

The core route is:

```text
startup intake
-> run shell and lifecycle guard
-> PM material understanding
-> runtime mechanical audit and role-binding readiness
-> route and frontier
-> FlowGuard process/product gates when required
-> runtime-requested role dispatch
-> packeted worker execution
-> review, repair, route redesign, or stale-evidence reset
-> terminal backward replay
-> final completion ledger
```

In plain language:

- **Route simulation** models the likely development path before the agent starts treating it as the active loop.
- **Router state** decides the next legal action from current run state, not from memory.
- **Sealed packet mail** moves work through envelopes and sealed bodies with hashes and holder state.
- **Role authority** separates PM planning, worker execution, reviewer challenge, FlowGuard modeling, repair, stop, and controller duties.
- **FlowGuard gates** model risky process and product paths before the route treats them as safe.
- **Completion ledger** blocks broad done claims until route-wide evidence is current.

## Four Control Objects

| Object | What it controls | Why it matters |
| --- | --- | --- |
| FlowGuard finite-state models | Planned route transitions and risky target behavior | Turns "be careful" into states, invariants, progress checks, and counterexamples before and during the loop |
| Sealed packets | Handoff bodies, envelopes, hashes, holder state, and role origin | Prevents the same context from planning, executing, reviewing, and accepting itself |
| Role authority | PM, reviewer, FlowGuard operator, worker, and Controller boundaries | Makes approval and challenge visible |
| Router rhythm | Startup, next action, packet re-entry, status projection, patrol, resume, route redesign, and terminal closure | Keeps continuation tied to current run state |

## Current Status

| Field | Value |
| --- | --- |
| Source version | `v0.11.3` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| Release shape | Source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | Real `flowguard` Python package |
| Current UI surface | Windows WPF startup intake dialog plus chat route signs |

`v0.11.3` strengthens the existing Reviewer/PM challenge chain with fixed stage review bindings, concrete PM-actionable Reviewer guidance, current status projection hardening, and refreshed OpenSpec, FlowGuard, topology, and install-sync validation.

## When To Use FlowPilot

Use FlowPilot for:

- multi-step implementation, refactor, release, or repair projects;
- work that needs runtime role assistance or role separation;
- tasks that need FlowGuard modeling, human-like review, or child-skill gates;
- projects where patrol, resume, or host-supported continuation must preserve current-run state;
- work where final completion needs a route-wide ledger rather than a local done feeling.

Do not use it for:

- ordinary Q&A;
- tiny edits;
- simple one-file changes;
- casual brainstorming;
- work where a smaller FlowGuard model or normal planning prompt is enough.

## Quick Start

Recommended human-facing path:

1. Open a fresh AI agent or CLI window that supports local tools.
2. If the host has a goal, target, or objective option, turn it on.
3. Ask the agent to install FlowPilot:

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Also install and verify its required FlowGuard dependency.
```

For a local source checkout:

```powershell
git clone https://github.com/liuyingxuvka/FlowPilot.git
cd FlowPilot
python scripts\check_install.py
```

Then send the startup instruction from [How To Start FlowPilot](#how-to-start-flowpilot), wait for the startup window, enter your project request there, and let FlowPilot run the loop.

## Verification

Run the install check from the repository root:

```powershell
python scripts\check_install.py
```

Release tooling is intentionally scoped to this repository. It must not commit, tag, push, package, upload, or publish companion skill repositories unless a maintainer explicitly starts a release task.

## Documentation Map

| File | Purpose |
| --- | --- |
| [`docs/flowguard_adoption_log.md`](./docs/flowguard_adoption_log.md) | FlowGuard adoption and process evidence |
| [`docs/ui/startup_intake_desktop_preview/README.md`](./docs/ui/startup_intake_desktop_preview/README.md) | Startup intake UI preview |
| [`skills/flowpilot/SKILL.md`](./skills/flowpilot/SKILL.md) | Installable Codex skill |
| [`skills/flowpilot/references/protocol.md`](./skills/flowpilot/references/protocol.md) | Core protocol |
| [`skills/flowpilot/references/failure_modes.md`](./skills/flowpilot/references/failure_modes.md) | Failure modes the route is designed to prevent |
| [`skills/flowpilot/assets/runtime_kit/README.md`](./skills/flowpilot/assets/runtime_kit/README.md) | Runtime kit |

## Repository Layout

```text
skills/flowpilot/        Installable Codex skill and runtime assets
scripts/                 Install, check, packet, role-output, test-tier, and release validation scripts
templates/flowpilot/     Runtime templates for packets, routes, evidence, roles, and ledgers
assets/                  Brand, README hero, and screenshot assets
docs/                    UI notes and FlowGuard adoption records
examples/                Minimal examples
VERSION                  Source version file
CHANGELOG.md             Release history
```

## Public Boundary

This public repository should include FlowPilot source, skill source, templates, docs, examples, public-safe validation artifacts, and README assets.

It should not include live private run bodies, sealed packet contents from real projects, credentials, local Codex state, local machine state, personal project handoff records, or unpublished companion-skill release material.

## What FlowPilot Is Not

FlowPilot is not a general memory layer, a chat summarizer, a replacement for FlowGuard, a binary app bundle, or a guarantee that an AI project is correct. It is a process-control layer that keeps long AI software work explicit, reviewable, and harder to close prematurely.

## License

MIT. See [`LICENSE`](./LICENSE).

---

# FlowPilot 中文说明

**Source version:** `v0.11.3`<br />
**许可证：** MIT<br />
**形态：** open-source AI-agent control runtime

## 它是什么

FlowPilot 是一个 opt-in、开源的 control loop 和本地 runtime，用于较长、较复杂的 AI-agent 软件项目。它把一次很长的 AI 运行变成一个由模型支撑的项目团队：project manager 负责规划和吸收结果，worker 执行有边界的 packet，reviewer 挑战输出质量，FlowGuard operator 检查流程和状态风险，Controller 让 route 始终绑定当前 runtime evidence。

当前公开包的第一种具体形态是 Codex-compatible local skill runtime。但产品概念更通用：给 AI agent 一个由人监督、由模型约束的工作 loop，让 route state、role-scoped packet handoff、model-backed checks、repair gates 和 completion evidence 都显式存在。

它适合那种不能只靠一段连续聊天记忆管理的工作。FlowPilot 给 agent 一个持久 route、sealed handoff packets、host-supported background collaboration、角色分离的 authority、FlowGuard model gates、startup intake、patrol/manual-resume continuity 和 final completion ledger。

语言模型仍然做语义工作：读材料、写代码、审查工件、使用工具、解释取舍。FlowPilot 控制这些工作外面的流程，防止 run 漂移、跳过门槛、复用旧证据，或在 route-wide evidence 不足时宣布完成。

## 怎么启动 FlowPilot

推荐的人类使用流程是：

1. 打开一个可以使用本地工具、可以操作仓库的 AI agent 界面。
2. 如果这个 host 有 goal、target 或 objective 模式，先打开。
3. 发送这句话：

```text
正式启动 FlowPilot。在 FlowPilot 到达 terminal return、请求我输入或明确允许停止之前，不要停止使用 FlowPilot。
```

4. 等 FlowPilot 的 startup window 打开。
5. 把项目目标、约束、期望结果写进 startup window。
6. 点击启动，让 FlowPilot 接管这个 loop。

启动之后，FlowPilot 应该推动 agent 完成 route planning、role dispatch、packeted execution、review、repair、必要时 route replanning，以及最后的 completion evidence。

## 为什么需要它

长 AI-agent 项目常见失败方式很固定：

1. agent 把聊天历史当控制面。
2. continuation 靠记忆猜下一步。
3. 同一个角色计划、实现、审查并批准自己的工作。
4. route 早期证据在后续变化后仍被信任。
5. background agents、child skills 或 worker 返回了输出，但 ownership 不清。
6. 因为本地有改动就宣布完成，而不是因为 final ledger 清楚。

FlowPilot 用明确 runtime objects 替代“希望 agent 自觉”：route state、role bindings、sealed packets、model checks、review decisions、repair records 和 ledger evidence。

## 产品预览

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot desktop startup intake window with the background collaboration toggle above the project request field and no visible scrollbar" width="760" />
</p>

Startup intake UI 收集用户的工作请求，并确认 FlowPilot 是否可以使用 host-supported background collaboration 来隔离角色工作。Manual continuation 和 chat route signs 是固定 startup defaults。请求正文会 sealed 到 PM intake packet；Controller 只能看到 envelope 和 hash metadata。

## 角色化后台团队

FlowPilot 的 loop 不是让同一个 assistant 一直对自己说“继续”。当 host 能提供隔离的角色界面时，FlowPilot 可以把后台智能体分派到有边界的职责里，再把它们的结果通过当前 runtime state 收回来。

| 角色 | 负责什么 | 不能默默做什么 |
| --- | --- | --- |
| Project Manager (PM) | 理解材料、设计 route、发 work packet、吸收结果、决定 repair/replan/continue/stop | 自己执行 worker packet，或把自己的输出当最终证据批准 |
| Worker | 在允许的文件、工具、child skill 和输出格式内执行一个有边界的 packet | 重新设计 route、标记 node 完成，或绕过 review |
| Reviewer | 从接近人工质量审查的角度挑战 PM plan、worker output、evidence credibility 和 final completion | 只因为 PM checklist 存在就当成证明 |
| FlowGuard operator | 建模 process/product risk，运行 route simulation，检查 stale evidence 和 model miss | 替代 reviewer，或单独保证最终产品一定正确 |
| Controller | 让当前 run、packet envelope、lease、status、patrol、resume 和 terminal return 绑定 runtime state | 读取 sealed body、从聊天历史推断进度，或凭记忆修改 route |

所以 FlowPilot 可以像自主 loop 一样持续推进，但不是黑箱。agent 可以继续工作，但每个有意义的动作都有 owner、packet、gate 和 current-state reason。

## 先建模路线，再执行 loop

FlowPilot 不是单纯地“持续触发、分派、检查、记录、再决定”。在 loop 把某条路径当成安全路径之前，FlowGuard 会先建模和预演预期的 process route。运行中如果出现新证据、检查失败、需求变化或旧假设失效，route 也可以被重新设计。

核心路线是：

```text
startup intake
-> run shell and lifecycle guard
-> PM material understanding
-> runtime mechanical audit and role-binding readiness
-> route and frontier
-> FlowGuard process/product gates when required
-> runtime-requested role dispatch
-> packeted worker execution
-> review, repair, route redesign, or stale-evidence reset
-> terminal backward replay
-> final completion ledger
```

翻成人话：

- **Route simulation** 在 agent 把路线当成 active loop 之前，先模拟可能的开发路径。
- **Router state** 从当前 run state 决定下一步合法动作，而不是靠记忆。
- **Sealed packet mail** 用 envelope、sealed body、hash 和 holder state 传递工作。
- **Role authority** 分离 PM planning、worker execution、reviewer challenge、FlowGuard modeling、repair、stop 和 controller duty。
- **FlowGuard gates** 在 route 认为安全之前建模风险流程和产品路径。
- **Completion ledger** 阻止证据还没闭合时的 broad done claim。

## 四个控制对象

| 对象 | 控制什么 | 为什么重要 |
| --- | --- | --- |
| FlowGuard finite-state models | planned route transitions 和高风险目标行为 | 在 loop 前和 loop 中，把“要小心”变成 state、invariant、progress check 和 counterexample |
| Sealed packets | handoff body、envelope、hash、holder state、role origin | 防止同一上下文计划、执行、审查、接受自己的工作 |
| Role authority | PM、reviewer、FlowGuard operator、worker、Controller 边界 | 让批准和挑战可见 |
| Router rhythm | startup、next action、packet re-entry、status projection、patrol、resume、route redesign、terminal closure | 让 continuation 绑定当前 run state |

## 当前状态

| 字段 | 值 |
| --- | --- |
| Source version | `v0.11.3` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| Release shape | source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | real `flowguard` Python package |
| Current UI surface | Windows WPF startup intake dialog plus chat route signs |

`v0.11.3` 在现有 Reviewer/PM challenge chain 上增加固定阶段审查绑定、具体可执行的 Reviewer 给 PM 建议、current status projection hardening，并刷新 OpenSpec、FlowGuard、topology 和 install-sync validation。

## 什么时候用 FlowPilot

适合：

- 多步骤 implementation、refactor、release 或 repair 项目；
- 需要 runtime role assistance 或 role separation 的工作；
- 需要 FlowGuard modeling、human-like review 或 child-skill gates 的任务；
- patrol、resume 或 host-supported continuation 必须保留 current-run state 的项目；
- final completion 需要 route-wide ledger，而不是局部 done feeling 的工作。

不适合：

- 普通问答；
- 很小的修改；
- 简单单文件改动；
- 轻量 brainstorm；
- 小 FlowGuard model 或普通 planning prompt 已经够用的工作。

## 快速开始

推荐的人类使用方式：

1. 打开一个支持本地工具的新 AI agent 或 CLI 窗口。
2. 如果 host 有 goal、target 或 objective 选项，先打开。
3. 请 agent 安装 FlowPilot：

```text
Install FlowPilot from https://github.com/liuyingxuvka/FlowPilot.
Also install and verify its required FlowGuard dependency.
```

本地源码 checkout：

```powershell
git clone https://github.com/liuyingxuvka/FlowPilot.git
cd FlowPilot
python scripts\check_install.py
```

然后发送[怎么启动 FlowPilot](#怎么启动-flowpilot)里的启动指令，等待 startup window，在里面填写项目请求，再让 FlowPilot 执行这个 loop。

## 验证

在仓库根目录运行安装检查：

```powershell
python scripts\check_install.py
```

Release tooling 只作用于这个仓库；除非 maintainer 明确开始 release task，否则不应该 commit、tag、push、package、upload 或 publish companion skill repositories。

## 文档入口

| 文件 | 作用 |
| --- | --- |
| [`docs/flowguard_adoption_log.md`](./docs/flowguard_adoption_log.md) | FlowGuard adoption 和 process evidence |
| [`docs/ui/startup_intake_desktop_preview/README.md`](./docs/ui/startup_intake_desktop_preview/README.md) | Startup intake UI preview |
| [`skills/flowpilot/SKILL.md`](./skills/flowpilot/SKILL.md) | 可安装 Codex skill |
| [`skills/flowpilot/references/protocol.md`](./skills/flowpilot/references/protocol.md) | 核心协议 |
| [`skills/flowpilot/references/failure_modes.md`](./skills/flowpilot/references/failure_modes.md) | route 要防住的失败模式 |
| [`skills/flowpilot/assets/runtime_kit/README.md`](./skills/flowpilot/assets/runtime_kit/README.md) | Runtime kit |

## 仓库结构

```text
skills/flowpilot/        可安装 Codex skill 和 runtime assets
scripts/                 install、check、packet、role-output、test-tier、release validation scripts
templates/flowpilot/     packet、route、evidence、role、ledger runtime templates
assets/                  brand、README hero、screenshot assets
docs/                    UI notes 和 FlowGuard adoption records
examples/                minimal examples
VERSION                  source version file
CHANGELOG.md             release history
```

## 公开边界

这个公开仓库应该包含 FlowPilot source、skill source、templates、docs、examples、public-safe validation artifacts 和 README assets。

它不应该包含真实项目的 live private run bodies、sealed packet contents、credentials、本地 Codex state、本地机器状态、personal project handoff records 或未发布 companion-skill release material。

## FlowPilot 不是什么

FlowPilot 不是通用 memory layer，不是 chat summarizer，不替代 FlowGuard，不是 binary app bundle，也不保证 AI 项目一定正确。它是一个 process-control layer，让长 AI 软件工作更显式、更可审查、更不容易过早关闭。

## 许可证

MIT. See [`LICENSE`](./LICENSE).
