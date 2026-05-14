# Skills Subtree Rules

This file applies to everything under [.codex/skills/](../skills/).

- Keep each skill narrow: one trigger family, one repeatable procedure.
- Frontmatter must contain only `name` and `description`.
- Put trigger conditions in `description`, not in body headings.
- Keep `SKILL.md` concise and operational; prefer short workflows over essays.
- Every skill must include a `## Do not use` section with explicit boundaries.
- Do not add `agents/openai.yaml`, extra docs, scripts, or references unless the skill truly needs them.
- Do not mirror enhancer-owned skills into `.agents/skills/`; that root is external/Spec Kit-owned compatibility surface.
- If a workflow needs many references or multiple procedures, document it in [docs/ai/](../../docs/ai/) instead of creating a broad skill.
- After any skill edit, run `python scripts/check.py` and `python -m unittest discover -s tests -p "test_*.py" -v`.
