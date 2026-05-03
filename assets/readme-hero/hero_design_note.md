# FlowPilot README Hero Design Note

## Project Summary

FlowPilot is a FlowGuard-based project-control layer for AI coding agents.
FlowGuard is the finite-state simulator/checker at the center of the method.
FlowPilot applies it to both the product/function behavior being built and the
agent's live development process while the work is running.

## Target Users

- AI coding agent users who run substantial software projects.
- Developers evaluating formal agent-control methods.
- Future FlowPilot adopters who need to understand the method before the
  implementation package is published.

## Core Problem

Large AI-agent-led projects can drift, skip gates, resume from stale state,
miss changed requirements, or finish before evidence supports completion.

## Core Workflow

User goals and materials enter a persistent finite-state project-control
model. Process FlowGuard checks the live development route while
product/function FlowGuard checks the behavior being built. Bounded chunks pass
through child-skill gates, verification, checkpoints, recovery branches, route
mutation, stale-evidence reset, and final completion ledger review.

## Hero Tagline

Finite-state project control for AI agents that model and correct development
work in real time.

## Visual Concept

A bright dimensional finite-state machine board with dual FlowGuard lanes:
amber for project-process control and cyan for product/function behavior. The
workflow moves from user materials to state nodes, gates, evidence cards,
checkpoints, and a final completion ledger.

## Image Keywords

finite-state machine, FlowGuard, AI coding agents, project control, verification
gates, evidence cards, completion ledger, dual-layer modeling, bright technical
product render.

## File Paths

- `assets/readme-hero/hero.png`
- `assets/readme-hero/hero_prompt.md`
- `assets/readme-hero/hero_design_note.md`

## README Insertion Position

The hero image is inserted immediately after the H1 title and before the
English introduction.
