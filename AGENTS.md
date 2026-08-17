# Codex Instructions

This repository's engineering standards, architecture, roadmap, security
boundaries, and mentoring workflow live in `CLAUDE.md` at the project root.
Read `CLAUDE.md` in full before making any change — it is the single source
of truth for this project. This file exists only to point you there, so the
two docs don't drift out of sync with each other.

Multiple AI coding agents (Claude Code and Codex) are used on this
repository at different times, but never concurrently on the same branch.
Before editing anything, run `git status`, `git log --oneline -5`, and
`git branch --show-current` to confirm what branch you're on and that no
other agent's work is uncommitted or in progress, per `CLAUDE.md`'s Git
Workflow and Handoff Rule sections.
