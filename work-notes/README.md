# work-notes/

The dated lab notebook. Any agent or person who runs an experiment, changes a version, or hits and fixes a
problem appends here. Notes are history: don't rewrite old entries; add a new one that supersedes them.

## Convention

- File name: `YYYY-MM-DD-<short-topic>.md`. Several sessions on the same day and topic can share a file; add a
  `## HH:MM` section per session.
- Each entry has:
  - **Goal**: one line.
  - **Setup**: versions (copy `~/h3-vid-gen-runtime/versions.txt` when it changed), models, flags.
  - **What was done**: commands, exactly as run.
  - **Results**: numbers (wall/execution seconds from the sidecar JSON), output file names, and what you saw
    (use `tools/contact_sheet.py`).
  - **Conclusions / follow-ups**: and where they went (docs/... updated? research/... note?).
- Don't commit videos. Refer to `outputs/<name>.mp4` by name; the sidecar JSON holds the full settings.

## Index

| Date | Note |
|---|---|
| 2026-11-21 | [Bootstrap: repo, WSL runtime, first renders on the RTX 5090](2026-11-21-bootstrap.md) |
