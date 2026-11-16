# M5 pre-registration revision 8: narrow review of commit 23d3a9f (diff against d9933fe)

**Verdict: ACCEPTABLE AS IS.**

Scope: only the changes in 23d3a9f, in `experiments/E5_scored_m5/run.py`, `tests/test_scored_m5.py`, `experiments/PHASE_1_M5_PREREGISTRATION.md` and `docs/DECISION_LOG.md` (rows P-47 to P-49 only). I ran no scored simulation and no smoke run. I edited no repository file. I did not read anything under E4 results/. Scratch files and a test junction were created only in my own scratch directory, and the junction was removed afterwards.

## Required changes

None.

## Optional changes

1. **Paths below REPO are not resolved one by one** (INFERENCE). `require_local_location` resolves the repository, OUT, OUT_NOMAG, M4's runner, the package and the smoke folder (`run.py:594-599`). It does not resolve the near-field tables (`E4 run.py:74`, `TABLES = D8/"results"/"tables"`), the V3 records in `D8/results`, or `d8_1b_stage1`.
   - A junction placed later under the repository, for example `tables` pointing into OneDrive, would not be caught.
   - Today there are no links of any kind under `C:\dev\Rubiknetic` (FACT, checked with `find -type l` in WSL and the reparse-point attribute on Windows).
   - These paths are read only, and the manifest pins the table SHA-256s, so a run cannot pass with wrong data. The only exposure is the online-only/lock risk that review 6 X4 described.
   - Two possible fixes: add `M4.TABLES` and `M4.D8 / "results"` to the paths that are checked, or narrow the docstring at `run.py:579-581`. It says "no path the run reads or writes"; §2 lists exactly what is checked and is already accurate.
2. **The check matches folder names, not sync roots** (INFERENCE).
   - `^onedrive\b` (`run.py:575`) misses SharePoint libraries that OneDrive syncs to `%USERPROFILE%\<Org>\…`, and it misses other sync clients such as Dropbox and Google Drive.
   - It flags harmless names such as `OneDrive.old` and `OneDrive-Org`, which is a safe false positive.
   - On this machine the only OneDrive mount point is `C:\Users\abdul\OneDrive` (FACT, from `HKCU\Software\Microsoft\OneDrive\Accounts\*\ScopeIdToMountPointPathCache`; Business1 has no UserFolder), and `C:\dev` is not a reparse point. The check is sufficient for this run.
3. **The retired copy can still start a mixed-provenance run** (INFERENCE). The old OneDrive copy (HEAD d9933fe, clean) still holds revision 7's `run.py`. Because the venv `.pth` now points at `/mnt/c/dev/Rubiknetic/src`:
   - running that copy's runner with OneDrive exited would load the runner and M4 from OneDrive but the package from `C:\dev`;
   - its clean-commit check and recorded commit would describe `C:\dev` (`scored._git` uses `scored.REPO`), not the runner that actually ran.

   Revision 8's check cannot guard a runner that does not contain it. Consider renaming or removing the old copy's `experiments/E5_scored_m5/` before the run, or adding a note to the run checklist.
4. **Text nits** (FACT):
   - P-49 says "469 files". `third_party_cad/` has 463 files and the tables 6, which makes 469; the CAD archive zip makes 470. All 470 match the old copy's SHA-256s.
   - §9 rev-8 row "Provenance … (review 7, Y2)" (`PREREGISTRATION.md:557`) adopts Y2. Neither P-49 nor the Status bullet (`:10`, "Y1–Y5 were not adopted") says this.
   - The §6.1 item 3 bullets for revisions 6 and 7 still list "a scored start is refused while OneDrive runs" (`:420`) and the `tasklist` X4 test (`:426`). Both tests are removed. The rev-8 bullet (`:427`) says they are replaced, so the text is readable as history; an inline "(replaced in revision 8)" would be clearer.
   - Provenance has a double "and" (`:40-41`), and line `:384` exceeds the file's wrap width.
5. **The `.pth` was edited by hand** (FACT). `_editable_impl_rubiknetic.pth` now contains `/mnt/c/dev/Rubiknetic/src`, and `direct_url.json` says `file:///mnt/c/dev/Rubiknetic`. The RECORD hash (`jBHiXT…`) no longer matches the file (`Te2u23…`). This is harmless for imports; a reinstall with `pip install -e`/`uv` from `C:\dev` would make the metadata consistent.

## Checks that passed

1. **The check is correct for its purpose.**
   - It is called for every start that is not a dry run, scored or smoke, before `git rev-parse`, the clean-commit check, `prepare`, the manifest and any write (`run.py:656-657`).
   - The smoke folder is resolved against the working directory, which is the same place the runner writes to (`run.py:685`).
   - The results folders, the temporary manifest next to `results/` (`HERE`, already resolved through `__file__`) and the records all lie under the paths that are checked.
   - Junction test: I made a Windows junction in scratch pointing to `C:\Users\abdul\OneDrive\Desktop`. WSL reports it as a symlink, `Path.resolve()` follows it, and `location_problems` flags it.
   - Case: `/mnt/c/users/abdul/onedrive/x` is flagged, because the regex is case-insensitive.
   - Regex: `OneDriveTemp` and `OneDrive_Org` pass; `OneDrive`, `OneDrive - Personal` and `OneDrive-Org` are flagged; `Dropbox` and `My OneDrive` pass.
   - A relative smoke folder with the working directory in OneDrive is flagged.
   - The real paths of this checkout give `[]`.
2. **The package check holds.**
   - From `/tmp`, the venv imports `rubiknetic` from `/mnt/c/dev/Rubiknetic/src/rubiknetic/__init__.py`.
   - `scored.REPO` is `/mnt/c/dev/Rubiknetic`, and PYTHONPATH is empty.
   - `magnets`, `cube_logic`, the M4 runner and `d8_1b_stage1` all resolve under `/mnt/c/dev/Rubiknetic`.
   - `scored._git` therefore runs `git -C` against this repository.
   - Workers use the `fork` context (`run.py:561`), so they inherit these modules.
   - `analyze.py` loads `run.py` from its own folder and gets the same package.
3. **The move is faithful.**
   - `d9933fe^{tree}` is `de4e3ef…` in both the clone and the old copy, and the old copy has no uncommitted changes.
   - `git ls-remote origin refs/heads/main` returns `23d3a9f`, which is the clone's HEAD and `origin/main`.
   - All 6 tables, 463 `third_party_cad` files and the zip are byte-identical to the old copy (SHA-256, 0 differences).
   - The `d8_1b_checks*.json` V3/pair records are identical, with LF endings (`git ls-files --eol`: i/lf w/lf).
   - The dry run gives 440 runnable, 2 not run (4×1.5 N35, "failed V3") and 0 refused, with the same per-experiment seed ranges.
   - `git status` is clean except for the separate smoke folder and its log, which are untracked and outside the frozen paths.
4. **Removing the old check broke nothing.**
   - No references to `subprocess` or `onedrive_running` remain anywhere in E5 or the tests.
   - The full suite passes: `tests/test_scored_m5.py`, 83 passed.
   - Mutation test: I used a pytest plugin in scratch to replace `R.require_local_location` with a no-op. All 3 parametrised scored-start tests and the smoke-start test then fail with `AssertionError: the test reached a real start`. So the tests are sensitive to the check, and X1-style stubs still stop any real start.
   - `test_location_problems_*` exercises the function directly, including a symlink.
   - `test_this_checkout_passes_the_location_check` does not call `main`.
5. **The text matches the code.** §2 (`:181-187`), §6.1 item 3 (`:384`, `:427-430`), §8, the §9 rev-8 table, Status and P-49 describe the code accurately, apart from the nits in optional item 4.
6. **Resume and validity are unaffected.**
   - The change sits in frozen paths (`run.py`, the pre-registration) and comes before any manifest, so the frozen-path diff between the manifest commit and HEAD is unaffected, provided the Status commit precedes the first start, as §8 requires.
   - The manifest stores no absolute paths that the move would change.
   - The check is applied identically on resume.
   - I found no path by which a correct run is refused, INVALID or INCOMPLETE because of this commit, and none by which an incorrect run passes.

Commands: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -c "cd /mnt/c/dev/Rubiknetic && … pytest -p no:cacheprovider tests/test_scored_m5.py -q"`, the same with `-p mutnocheck -k onedrive`, and `run.py all --dry-run`. Scratch scripts are in `C:\Users\abdul\AppData\Local\Temp\claude\b6672f8dce1e00f4\3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350\scratchpad\`.
