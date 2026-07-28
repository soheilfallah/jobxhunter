<!-- Thanks for contributing. Keep this short — a few honest lines beat a filled-in form. -->

## What and why

<!-- What changes, and what problem it solves. The "why" matters more than the "what". -->

## How you verified it

<!-- What you actually ran or observed. "Didn't test" is an acceptable answer — just say so. -->

## Checklist

- [ ] `python scripts/check_release.py` passes
- [ ] `claude plugin validate . --strict` passes
- [ ] Tested with `claude --plugin-dir .` from a directory **outside** the repo, if this touches paths, connectors, or `SKILL.md`
- [ ] `CHANGELOG.md` updated, if this affects users
- [ ] No API keys, real profiles, or real personal details added

## The truth rule

<!-- Delete if not applicable. -->

- [ ] This change does **not** loosen the rule that jobxhunter never invents a fact about a candidate

<!-- If it touches that rule at all, explain here why the line still holds. -->
