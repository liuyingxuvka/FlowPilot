# FlowPilot

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="FlowPilot concept hero image showing FlowGuard state models, packet mail, role gates, and router cadence" width="100%" />
</p>

<p align="center">
  <img src="./assets/brand/flowpilot-icon-default.png" alt="FlowPilot red-purple rounded hexagram icon" width="132" />
</p>

<p align="center">
  <strong>A project-control layer for long AI-agent software work.</strong><br />
  <span>FlowGuard models, sealed packet mail, role authority, startup intake, and completion ledgers for disciplined agent runs.</span>
</p>

<p align="center">
  Source version: <strong>v0.10.20</strong> · MIT License · Codex skill source package
</p>
<!-- README HERO END -->

English comes first. The second half is a full Chinese mirror.

## What FlowPilot Is

FlowPilot is an opt-in Codex skill and local runtime for substantial AI-agent-led software projects.

It is built for work that is too long or too risky to trust to one continuous chat memory. FlowPilot gives the agent a persistent route, sealed handoff packets, role-separated authority, FlowGuard model gates, startup intake, patrol/manual-resume continuity, and a final completion ledger.

The language model still does the semantic work: reading materials, writing code, reviewing artifacts, using tools, and explaining tradeoffs. FlowPilot controls the process around that work so the run does not drift, skip gates, reuse stale evidence, or declare completion before the route-wide evidence supports it.

## The Problem

Long AI-agent projects tend to fail in predictable ways:

1. The agent treats chat history as the control surface.
2. A continuation guesses the next step from memory.
3. One role plans, implements, reviews, and approves its own work.
4. Evidence from an earlier route remains trusted after later changes.
5. A child skill or worker returns output without clean ownership.
6. Completion is declared because local edits exist, not because the final ledger is clear.

FlowPilot replaces informal discipline with explicit runtime objects.

## Product Preview

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot desktop startup intake window with the background collaboration toggle above the project request field and no visible scrollbar" width="760" />
</p>

The startup intake UI captures the user's work request and whether FlowPilot may use host-supported background collaboration for isolated role work. Manual continuation and chat route signs are fixed startup defaults. The request body is sealed into the PM intake packet; the Controller sees only envelope and hash metadata.

## How It Works

The core route is:

```text
startup intake
-> run shell and lifecycle guard
-> PM material understanding
-> reviewer startup fact review
-> route and frontier
-> FlowGuard process/product gates when required
-> packeted worker execution
-> review, repair, route redesign, or stale-evidence reset
-> terminal backward replay
-> final completion ledger
```

In plain language:

- **Router state** decides the next legal action from current run state, not from memory.
- **Sealed packet mail** moves work through envelopes and sealed bodies with hashes and holder state.
- **Role authority** separates planning, execution, review, modeling, approval, repair, stop, and controller duties.
- **FlowGuard gates** model risky process and product paths before the route treats them as safe.
- **Completion ledger** blocks broad done claims until route-wide evidence is current.

## Four Control Objects

| Object | What it controls | Why it matters |
| --- | --- | --- |
| FlowGuard finite-state models | Process transitions and risky target behavior | Turns "be careful" into states, invariants, progress checks, and counterexamples |
| Sealed packets | Handoff bodies, envelopes, hashes, holder state, and role origin | Prevents the same context from planning, executing, reviewing, and accepting itself |
| Role authority | PM, reviewer, FlowGuard operator, worker, and Controller boundaries | Makes approval and challenge visible |
| Router rhythm | Startup, next action, packet re-entry, status projection, patrol, resume, and terminal closure | Keeps continuation tied to current run state |

## Current Status

| Field | Value |
| --- | --- |
| Source version | `v0.10.20` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| Release shape | Source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | Real `flowguard` Python package |
| Current UI surface | Windows WPF startup intake dialog plus chat route signs |

`v0.10.20` simplifies parent backward closure to one Reviewer-owned parent backward review packet. After the last child of a parent or module closes, FlowPilot returns to that parent, opens exactly one `review.parent_backward_replay` packet, and the accepted review result itself becomes the parent-closure evidence. PM then absorbs that evidence before continuing. If a later ancestor, terminal, or final gate sees a missing or multiple parent-review gap, FlowPilot treats it as a control-plane ordering violation instead of late repair work. This release keeps the path current-contract only: no old-run migration, compatibility alias, fallback translator, or historical-state promotion is added.

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
2. If the host has a goal/target option, set the goal to keep using FlowPilot until FlowPilot reaches a terminal state, asks for user input, or explicitly says to stop.
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

Then ask the agent to start a FlowPilot run for your project-scale task.

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

**Source version:** `v0.10.20`<br />
**许可证：** MIT<br />
**形态：** Codex skill source package

## 它是什么

FlowPilot 是一个 opt-in 的 Codex skill 和本地 runtime，用于较长、较复杂的 AI-agent 软件项目。

它适合那种不能只靠一段连续聊天记忆管理的工作。FlowPilot 给 agent 一个持久 route、sealed handoff packets、角色分离的 authority、FlowGuard model gates、startup intake、patrol/manual-resume continuity 和 final completion ledger。

语言模型仍然做语义工作：读材料、写代码、审查工件、使用工具、解释取舍。FlowPilot 控制这些工作外面的流程，防止 run 漂移、跳过门槛、复用旧证据，或在 route-wide evidence 不足时宣布完成。

## 为什么需要它

长 AI-agent 项目常见失败方式很固定：

1. agent 把聊天历史当控制面。
2. continuation 靠记忆猜下一步。
3. 同一个角色计划、实现、审查并批准自己的工作。
4. route 早期证据在后续变化后仍被信任。
5. child skill 或 worker 返回了输出，但 ownership 不清。
6. 因为本地有改动就宣布完成，而不是因为 final ledger 清楚。

FlowPilot 用明确 runtime objects 替代“希望 agent 自觉”。

## 产品预览

<p align="center">
  <img src="./assets/readme-screenshots/startup-intake.png" alt="FlowPilot desktop startup intake window with the background collaboration toggle above the project request field and no visible scrollbar" width="760" />
</p>

Startup intake UI 收集用户的工作请求，并确认 FlowPilot 是否可以使用 host-supported background collaboration 来隔离角色工作。Manual continuation 和 chat route signs 是固定 startup defaults。请求正文会 sealed 到 PM intake packet；Controller 只能看到 envelope 和 hash metadata。

## 它怎么工作

核心路线是：

```text
startup intake
-> run shell and lifecycle guard
-> PM material understanding
-> reviewer startup fact review
-> route and frontier
-> FlowGuard process/product gates when required
-> packeted worker execution
-> review, repair, route redesign, or stale-evidence reset
-> terminal backward replay
-> final completion ledger
```

翻成人话：

- **Router state** 从当前 run state 决定下一步合法动作，而不是靠记忆。
- **Sealed packet mail** 用 envelope、sealed body、hash 和 holder state 传递工作。
- **Role authority** 分离 planning、execution、review、modeling、approval、repair、stop 和 controller duty。
- **FlowGuard gates** 在 route 认为安全之前建模风险流程和产品路径。
- **Completion ledger** 阻止证据还没闭合时的 broad done claim。

## 四个控制对象

| 对象 | 控制什么 | 为什么重要 |
| --- | --- | --- |
| FlowGuard finite-state models | 流程转移和高风险目标行为 | 把“要小心”变成 state、invariant、progress check 和 counterexample |
| Sealed packets | handoff body、envelope、hash、holder state、role origin | 防止同一上下文计划、执行、审查、接受自己的工作 |
| Role authority | PM、reviewer、FlowGuard operator、worker、Controller 边界 | 让批准和挑战可见 |
| Router rhythm | startup、next action、packet re-entry、status projection、patrol、resume、terminal closure | 让 continuation 绑定当前 run state |

## 当前状态

| 字段 | 值 |
| --- | --- |
| Source version | `v0.10.20` |
| Public project name | `FlowPilot` |
| Skill slug | `flowpilot` |
| Release shape | source package only, no binary app bundle |
| First concrete host | Codex-compatible skill runtime |
| Required core dependency | real `flowguard` Python package |
| Current UI surface | Windows WPF startup intake dialog plus chat route signs |

`v0.10.20` 把父级倒查收尾简化成一个 Reviewer 负责的父级倒查审查包。某个父节点或模块的最后一个子节点关闭后，FlowPilot 会回到这个父节点，只打开一个 `review.parent_backward_replay` 包；这个审查结果被接受后，本身就算父级收尾证据。之后 PM 再吸收这份证据，决定是否继续往下走。如果更高层、终局或最后总验收才看见父级审查缺口，或者同时看见多个父级审查缺口，FlowPilot 会把它当成控制流程顺序坏掉，而不是临时补派修复审查。本版本只保留当前合约路径：不加入旧运行迁移、兼容 alias、fallback translator，也不把历史状态提升成当前证据。

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
2. 如果 host 有 goal/target 选项，把 goal 设置为持续使用 FlowPilot，直到 FlowPilot 到达 terminal state、请求用户输入或明确说停止。
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

然后让 agent 为你的项目级任务启动 FlowPilot run。

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
