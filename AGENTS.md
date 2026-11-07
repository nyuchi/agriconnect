# AGENTS.md

AgriConnect: open, aggregated agricultural data, no personal information.
Nyuchi-owned, part of the data layer (nyuchi/data-infra).

## Rules

- **The rule in `src/agriconnect/policy.py` is the product.** Do not weaken
  `K_MIN`, add a licence to `OPEN_LICENCES`, or enable a dataset without a
  named approver in the same reviewed change, and keep the tests that fail when
  any of them is broken.
- Never select, group or return an identifier or personal column. Never log a
  row.
- Read-only on Doris. No writes, no DDL.
- **Big work lives in GitHub issues** in this repo: plan, decisions and status.
  Open or update the issue before starting and link it from the PR.
- Branches: feature PRs target `staging`. `staging` to `main` is a release.
- Never print, commit or pass a secret in argv. Secrets live on the Fly app.
- Nothing here creates or deploys a Fly app. That needs the owner.
- British spelling: licence (noun), license (verb).
