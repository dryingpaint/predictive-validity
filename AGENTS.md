# Working in this repository

The checkout at `/Users/melissadu/Documents/projects/capable/predictive-validity` is the primary
checkout. It always holds `main`, as merged on GitHub. Never switch its branch or commit in it.

- Do all work in a worktree off `origin/main`:
  `git worktree add ../predictive-validity-<topic> -b <branch> origin/main`
  Give it its own `.env` (copied) and venv (`uv sync`).
- Land changes through a pull request into `main`.
- After a PR merges, bring the primary checkout up to date:
  `git -C /Users/melissadu/Documents/projects/capable/predictive-validity pull --ff-only`
- Remove a worktree once its branch has merged: `git worktree remove ../predictive-validity-<topic>`.

Git hooks in `.git/hooks` enforce this on this machine. `pre-commit` refuses commits in the
primary checkout, and `post-checkout` switches it back to `main` if anything moves it.

The database is shared by every session. Announce DB-writing steps (pipeline runs, migrations) to the
other sessions before starting them. Never edit an applied migration; add the next number
(`db/migrate.py`, with migrations after `db/schema.sql`).
