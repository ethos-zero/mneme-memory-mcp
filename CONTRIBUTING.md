# Contributing

Before opening a PR:

- Run `python -m pip install -e '.[dev]'`.
- Run `python -m pytest`.
- Run `python -m build` when packaging or installer behavior changed.
- Keep local memory stores, `.env` files, agent briefs, logs, and scratch output out of git.

Installer changes must preserve the explicit setup-profile confirmation rule in `AGENTS.md`.
