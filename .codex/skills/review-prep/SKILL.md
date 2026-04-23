---
name: review-prep
description: Prepare a change in this repository for review or PR handoff. Use when a patch updates AGENTS files, docs, skills, or helper scripts and needs a concise validation summary, explicit omissions, and reviewer-oriented risk notes.
---

# Prepare the patch for review

1. Run `python scripts/check.py`.
2. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
3. Re-read the diff with reviewer questions in mind:
   - Is each file necessary?
   - Are commands and paths real?
   - Does the change overbuild for the current repo state?
4. Summarize the patch in five short parts:
   - what changed
   - why it belongs in the repo
   - validation performed
   - deliberately omitted additions
   - follow-up only if the repo grows into needing it
5. If a skill changed, verify the trigger is narrow and the `## Do not use` section is still accurate.
6. If `AGENTS.md` changed, verify the repo map and canonical commands still match the filesystem.
7. If repo commands changed, verify [.github/workflows/validate.yml](../../../.github/workflows/validate.yml) changed too.

## Review priorities
- stale or incorrect instructions
- unnecessary new abstractions
- weak validation
- missing risk callouts
- generic skills that should have been docs instead

## Do not use
- Do not use before the implementation is stable enough to review.
- Do not use as a substitute for domain-specific testing once the repo has real product code.
- Do not turn the review summary into a file-by-file changelog unless a reviewer explicitly needs that detail.
