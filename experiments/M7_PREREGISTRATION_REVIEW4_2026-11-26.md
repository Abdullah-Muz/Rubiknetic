# M7 pre-registration — independent review 4 (2026-11-26)

One reviewer subagent (P-86 Q8). A narrow review of revision 4 (text only) and DECISION_LOG P-91 at `d3caf5a`,
compared with `dfae488`. Reproduced as returned, lightly condensed. Read-only: no files changed, no simulation run,
no scored seed touched.

---

**Verdict: ACCEPTABLE AS IS**

## R1 status (review 3's only required change)
**R1 (a): RESOLVED.** §6.8 gives both full SHA-256s, each verified independently:
- `run.py`, working copy: `576e221c…747b82b1b9a0a`; LF blob: `1636a3e1…dcb5d4c6f`;
- `analyze.py`, working copy: `07950313…125f978804f6ce4`; LF blob: `095f71f9…877163444265`.

The working-copy hashes match `sha256sum`, `selfcheck.json` (head `1b5c7582…`, `tree_clean_for_m7_paths` true,
`dirty` []) and the smoke provenance file (clean). The LF blobs are identical at `d3caf5a`. Converting each LF blob
to CRLF reproduces the working-copy hashes exactly, so "both pairs identify the same committed content" is confirmed.

**R1 (b): RESOLVED.** The revision-3 status bullet says "Response in §10".

## REQUIRED changes
None.

## OPTIONAL changes (none affects a criterion, the configuration or the evidence; none blocks freezing)
- **O1.** "O3: Adopted" is slightly broad. Three of review 3's four O3 sub-items were done; the fourth (§6.8
  precedes §6.7) was not. This is cosmetic, because both sections say which replaces which.
- **O2.** The O6 line citation would be exact as E4 `run.py:472-474, 517` rather than `472-473, 517`. The function
  belongs to M4's runner, and M5's frozen `run_job` calls it (E5 `run.py:315`).
- **O3.** §5's malformed-record examples are illustrative, not exhaustive: "a missing `members`" is not named, and a
  `None` field crashes only past the short-circuit conditions. The wording ("Other malformations (…)") does not claim
  to be complete, so it is acceptable as written.

## What I checked
1. **Hashes.**
   - Checked with `sha256sum`, `git show 1b5c758:<path> | sha256sum`, the CRLF-converted blobs, and both evidence
     JSONs.
   - `git ls-files --eol` gives `i/lf w/crlf attr/text=auto eol=lf`.
   - `git status` is clean with CRLF working copies, which supports the claim that line endings do not affect the
     freeze check.
2. **No code or evidence changed in revision 4.**
   - `git diff --stat dfae488 d3caf5a` touches only DECISION_LOG, the review-3 file and the text.
   - `1b5c758 → d3caf5a` adds only the revision-3 evidence committed at `dfae488`.
   - `run.py`, `analyze.py`, tests, `src/`, E4 and E5 are unchanged.
   - `5e74b69^ → d3caf5a` over `src`, E4, E5, the master spec, VALIDATION_PLAN and `test_scored_m5.py` is empty.
3. **Accuracy of the changes.**
   - **§6.2 against §6.8 and `selfcheck.json`:** 17 trials, all 0 differences, and SC3/SC5 list them correctly.
   - **§11 on O5:** accurate. `analyze.py` runs `_exec("e7_scored_m7_run", run.py)`. When `run.py` runs as
     `__main__`, that creates a second instance, which gets the cached M4 and wraps `M4.run_trial` again
     (`run.py:241, 258`). The double wrap would be harmful: the outer wrapper pops `edge_radius` and `noslip`, so the
     inner one would install the defaults.
   - **§11 on O6:** substantively accurate (see O2). Exception records set both flags False.
   - **§11 on O7:** accurate.
   - **§5 wording:** describes the code and relaxes no check.
   - **§6 heading, status bullets and P-91:** consistent with the log. The Status line still says NOT APPROVED,
     which is consistent with the conditional approval.
   - No stale "16 / 16" (except §6.7, historical), no "…9b1b9a0a", and no stale "replaces these".
4. **No loosening.** The diff changes only status bullets, a §5 description sentence, the §6 heading, §6.2's prose
   and results column, the §6.8 hash listing and §11.

## UNVERIFIED
- The user's conditional approval (recorded only in the log).
- That the 384-test suite passes.
- The six stray workers and the self-check's worker count.
- The final seed search (not part of this review).
