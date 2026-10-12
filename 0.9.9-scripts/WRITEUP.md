# CapLtd 0.9.9 CHERI Sail: split repos -> merged repo

This directory replays the CHERI work from the split repositories
(`rvy-sail-cheri-riscv`, whose `src/` becomes `model/cheri/`, and its `sail-riscv` submodule)
onto the merged repository baseline `split-merged-baseline` and rebases the series onto
`origin/codasip`. Everything is scripted:

- `reproduce_all.py`: single script containing the `COMMITS` table (`cheri(...)`, `sail(...)`,
  `patch(...)` dataclass entries) and all branch-building steps (`aligned`, `rebased`, `cleaned`,
  `squashed`, or `all` by default):
  - `build_aligned_branch()` (`rvy-0.9.9-rebased-on-common-base`, 109 commits on
    `split-merged-baseline`): formats patches from `COMMITS`, combining commit messages with
    `Combination of the following commits: Capabilities-Limited/...` and `----` separators for
    squashed `sail-riscv` submodule commits, and applies them with `git am -3` + `rr-cache/` +
    `adjustments/<sha>-*.diff`.
  - `build_rebased_branch()` (`rvy-0.9.9-rebased-on-head`, 78 commits on `origin/codasip`):
    applies `only_on_rebase` patches (`rebased-patches/000[1-4]-*.patch` and
    `split-repo-fixes/000[1-2]-*.patch`), cherry-picks commits from `rvy-0.9.9-rebased-on-common-base`
    (skipping `drop_on_rebase`, folding `fold_on_rebase` RV32 fixups into the preceding commit, and
    applying `rebased-patches/rebase/<sha>-*.diff`).
  - `build_cleaned_branch()` (`rvy-0.9.9-cleaned-history`, 42 commits on `origin/codasip`):
    drops `drop_on_clean` commits (`03960a0`, `5b0712e`), squashes `squash_into="<sha>"` commits into
    their target commit, applies `rebased-patches/cleaned/<sha>-*.diff`, and writes combined commit
    messages (`Combination of the following commits: Capabilities-Limited/...` with `----`
    separators and all individual commit messages, without provenance trailers).
  - `build_squashed_updated_messages_branch()` (`rvy-0.9.9-squashed-updated-messages`, 42 commits on
    `origin/codasip`): has the exact same commits and trees as `rvy-0.9.9-cleaned-history`, but uses
    a single concise combined commit message (`SUMMARY_MESSAGES`) with
    `Combination of the following commits: Capabilities-Limited/...` at the bottom instead of the
    `----`-separated original commit messages.
- `verify_commit_identity.py`: compares every commit on `rvy-0.9.9-rebased-on-common-base` against
  the split repos and writes `output/rvy-0.9.9-rebased-on-common-base/commit-identity/report.md`.
- `check_each_commit_builds.py`: builds every commit (`cmake --build cmake-build-debug`) and runs
  RV64 + RV32 `--self-test` sequentially; known failures on the aligned baseline branch are listed
  in `EXPECTED_FAILURES`.
- `run_testrig_sail_vs_sail.py`: TestRIG comparison of the split and merged RVFI simulators.

## Deviations from the split history (`split-merged-baseline..rvy-0.9.9-rebased-on-common-base`)

### Folded commits

- **`b6a6dda8` "Fixup memory types" is folded into `dc8ec197` and `ea15966c`.**
  `dc8ec197`, `ea15966c`, `cb6b63ae` and `9ef5189d` were written in January 2025 against an older
  sail-riscv (`paddr : xlenbits`, `MemValue`/`MemException`). In March 2025 they were rebased onto
  `de92797` ("Update CHERI code and merge recent 'master'"), which had already introduced the
  `physaddr` newtype and `Ok`/`Err` results, without being rebuilt; `b6a6dda8` repaired the
  whole stack a minute after `9ef5189d`. None of the four commits built in the split repo.
  To keep every commit buildable, `b6a6dda8` is split up:
  - `physaddr_bits()` in `phys_mem_read`/`phys_mem_write` goes into `dc8ec197`
    (`adjustments/dc8ec197-fold-b6a6dda8-memory-types.diff`);
  - `Ok`/`Err` in `rvfi_read`/`rvfi_write` and `physaddr_bits()` in
    `checked_mem_read`/`checked_mem_write` goes into `ea15966c`
    (`adjustments/ea15966c-fold-b6a6dda8-memory-types.diff`).

  The affected commits carry a `(folded in the matching part of ... b6a6dda8 ...)` line. The tree
  after `9ef5189d` is identical to the split history's tree after `b6a6dda8`.

### Skipped commits

- `5d367c45`: `.gitmodules` only.
- sail `29a70382`: identical to merged `4f1dae4d`, already in `split-merged-baseline`.
- sail `b6a6dda8`: folded, see above.

### Merged-repo adjustments and conflict resolutions

Of the **109** commits on `rvy-0.9.9-rebased-on-common-base` (see
`output/rvy-0.9.9-rebased-on-common-base/commit-identity/report.md` from `verify_commit_identity.py`):
- **86** are byte-for-byte identical to the split repo (after `src/` -> `model/cheri/`).
- **5** are merged-repo-only RV32 follow-up commits (`rv32-fixes/`).
- **18** differ from the split repo for one of four reasons:

| # | Split commit | Subject | Why it differs |
|---|---|---|---|
| `0001` | sail `6d8cafdb` | Fixes to work with TestRIG | `Ext_FetchAddr_Ext_Error` handling was already in `split-merged-baseline`; only the remaining whitespace change is applied. |
| `0002` | sail `dc8ec197` | Restore RVFI DII memory region restrictions | Folded `physaddr_bits()` from `b6a6dda8`; the `within_mmio_*` `$ifndef RVFI_DII` guards were already in `split-merged-baseline`. |
| `0003` | sail `ea15966c` | Restore RVFI read and write reporting | Folded `Ok`/`Err` and `physaddr_bits()` from `b6a6dda8`. |
| `0007` | cheri `8dc1750c` | Fixes for running with TestRIG | `adjustments/8dc1750-rvfi-build.diff`: CMake equivalent, `cheri_step_ext_nonrvfi.sail` to keep non-RVFI builds working, and align `riscv_step_rvfi.sail` with split. |
| `0008` | sail `9479bf45` | Fix resets | `adjustments/9479bf45-nonrvfi-reset.diff`: update `cheri_step_ext_nonrvfi.sail` (`ext_reset() = ()`). (`riscv_step_rvfi.sail` was already aligned in `0007`.) |
| `0010` | cheri `82d371e2` | Makefile fixes | `adjustments/82d371e-makefile-dedup-svinval.diff`: remove duplicate `riscv_insts_svinval.sail` line already in `split-merged-baseline`. |
| `0012` | cheri `26788339` | Include zifencei in Makefile | `adjustments/26788339-makefile-dedup-zifencei.diff`: `riscv_insts_zifencei.sail` was already in `split-merged-baseline`; kept as an empty commit for attribution. |
| `0015` | sail `44c7a9b9` | Fix out-of-range xcause length | `c_emulator/riscv_platform.cpp` change was already in `split-merged-baseline`; only the `model/riscv_sys_regs.sail` hunk remains. |
| `0019` | cheri `59586f8b` | Add CHERI CSR extending file to Makefile | `adjustments/59586f8-cmake-csr-ext.diff`: CMake equivalent (`cheri_csr_ext.sail`). |
| `0026` | cheri `629a4361` | Flip polarity of leaf check in CHERI PTE invalid checks | The code fix (`pte_is_ptr`) was already in `split-merged-baseline`; only the comment wording change remains. |
| `0027` | cheri `a0099ab4` | PTE check fixes | The `canC -> Tagged` and `crg != mstatus[UCRG]` fixes were already in `split-merged-baseline`; only the removal of redundant parens remains. |
| `0038` | cheri `512bb944` + sail `764f9f1d` | Re-enable self tests | `adjustments/512bb94-self-tests-build.diff`: CMake self-test wiring (`test_main_ext.sail`, `test_main.sail`, `riscv_rvfi_stub.sail`, remove `cheri_step_ext_nonrvfi.sail`) and rewrite `src/test_main_ext.sail` -> `$(SAIL_CHERI_MODEL_DIR)/test_main_ext.sail` in `Makefile`. |
| `0044` | cheri `ab305566` + sail `4fead739` + `5593d595` | Update to new CHERI fault reporting | `adjustments/ab30556-vext-translate-exception.diff`: merged repo has `riscv_insts_vext_mem.sail`, which also calls the now-2-argument `handle_translate_exception`. |
| `0054` | cheri `9063f09d` | Avoid using separate names for CHERI CSRs | `split-merged-baseline` has the `aligned_epcc` fix in `cheri_insts.sail`; the `epcc -> epc_y` rename applies across those lines. |
| `0059` | cheri `c67ba259` + sail `1567214f` | Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y | `adjustments/c67ba25-seccfg-move.diff`: remove `cheri_sys_regs_seccfg.sail` from CMake and use `extensionEnabled(Ext_Zkr)` in `riscv_sys_regs.sail`. |
| `0066` | cheri `d6bc2cbb` | Massive operand renaming | `split-merged-baseline` has `con = true` and `let typ = ReadWrite(...)` in `cheri_insts.sail`; the `cs2_val -> rs2_cap` rename applies on those context lines. |
| `0067` | cheri `5a95a40a` | Root not infinite caps | `0035` (`0001-rv32-detect-if-no-invalid-addresses.patch`) changed `0xff00_0000_0000_0000` to `0xff @ zeros(xlen - 8)` in `test_main_ext.sail`; the `infinite_cap -> root_cap` rename applies on that line. |
| `0105` | cheri `5a72076b` | Add allowSealedUnchanged operand to setAddrChecked | `adjustments/5a72076-setcapaddrchecked-xret.diff`: pass `true` to `setCapAddrChecked(epc_y, aligned_addr, true)` in `prepare_xret_target`. |

### RV32 follow-up commits

The split repo only built RV64. RV32 fixes are separate commits (authored by Alex Richardson,
`rv32-fixes/`) inserted directly after the commit that broke RV32, so that the picked commits
stay byte-for-byte identical to the originals:
- `0006` (`0000-rv32-rvfi-dii-physaddr.patch`): `out_of_rvfi_dii_range` and `rvfi_read`/`rvfi_write` take `physaddrbits`.
- `0035` (`0001-rv32-detect-if-no-invalid-addresses.patch`): `0xff @ zeros(xlen - 8)` in self test.
- `0045` (`0002-rv32-new-cheri-fault-reporting.patch`): `range(0, 63)` / `< 64` for `num_of_ExceptionType` on RV32.
- `0073` (`0003-rv32-ybndswi-test.patch`): `assert(Y(outR).tag == (xlen == 64))` after max-length `YBNDSWI`.
- `0085` (`0004-rv32-mode-related-renamings.patch`): `PointerMode` in `cheri_prelude_64.sail` (`ap_p_encdec`).

### Drop on rebase

Commits with `drop_on_rebase=True` in `COMMITS` only exist to match the split repo
and are dropped when rebasing onto `origin/codasip`:
- hardware (Toooba/CVA6) and TestRIG-specific hacks;
- Makefile-only commits. The legacy Makefile flow is kept working for this series only; Makefile
  hunks in other commits are resolved to upstream's Makefile during the rebase.

## Known per-commit failures on `rvy-0.9.9-rebased-on-common-base`

See `EXPECTED_FAILURES` in `check_each_commit_builds.py`: the legacy Makefile's RVFI source list is
broken at `split-merged-baseline` (missing `riscv_extensions.sail`) and stays broken until the split
repo's own `82d371e` "Makefile fixes". This is not fixed because the Makefile is dropped on rebase.

## Phase 2: Rebasing onto `origin/codasip` -> `rvy-0.9.9-rebased-on-head`

`build_rebased_branch()` in `reproduce_all.py` constructs the `rvy-0.9.9-rebased-on-head` branch
(78 commits: 4 pre-series fixes + 72 CHERI 0.9.9 commits + 2 split-repo bugfix commits) on top of
`origin/codasip`.

### Pre-series fixes (`rebased-patches/0001-*.patch` .. `0004-*.patch`)

Running TestRIG (`run_testrig_sail_vs_sail.py rebased`) against the split-repo RVFI simulator
uncovered two upstream `sail-riscv` bugs present in `origin/codasip` (fixed in upstream `master`
shortly after `origin/codasip` branched off) and two Part 1 RVFI commits from
`rvy-0.9.9-rebased-on-common-base` that are still required on `origin/codasip`:

- **`rebased-patches/0001-upstream-zba-rtypeuw-encoding.patch`** (`Fix encoding for ZBA_RTYPEUW (#1132, #1712)`):
  `origin/codasip` was branched immediately after upstream PR #1119, which collapsed
  `ADDUW` (`funct7 = 0b0000100`) and `SH1ADDUW`/`SH2ADDUW`/`SH3ADDUW` (`funct7 = 0b0010000`)
  into a single `0b0000100` clause in `model/riscv_insts_zba.sail` (and `ZBA_RTYPEUW_capmode` in
  `model/cheri/cheri_insts_zba.sail`). Cherry-picks upstream #1132 + #1712 and applies the same
  split to `ZBA_RTYPEUW_capmode`.
- **`rebased-patches/0002-upstream-sc-phys-access-and-alignment.patch`** (`Ensure physical access and alignment checks are not bypassed for store-conditionals (#1500, #1603)`):
  Upstream PR #861 refactored `STORECON` (`sc.w`/`sc.d`) to call `vmem_write` in
  `model/riscv_vmem_utils.sail`, bypassing `phys_access_check` when `match_reservation` failed
  and bypassing the alignment check when `plat_enable_misaligned_access` is enabled. Cherry-picks
  upstream #1500 + #1603.
- **`rebased-patches/0003-rvfi-dii-memory-range.patch`** (`Restore RVFI DII memory region restrictions`):
  Cherry-picks split-repo `dc8ec197` + `cb6b63ae` (and the RV32 `physaddr` fix from
  `0000-rv32-rvfi-dii-physaddr.patch`), adding `out_of_rvfi_dii_range` to
  `model/riscv_platform.sail` and checking `get_config_rvfi() & out_of_rvfi_dii_range(paddr, width)`
  in `phys_mem_read` and `phys_mem_write` in `model/riscv_mem.sail`.
- **`rebased-patches/0004-rvfi-ext-reset-cheri.patch`** (`Fixes for running with TestRIG`):
  Cherry-picks split-repo `8dc1750c` on `model/cheri/cheri_step_ext.sail` so `ext_reset()` always
  calls `ext_reset_cheri()` before `if get_config_rvfi() then ext_rvfi_reset();`.

### Commits dropped or folded relative to `rvy-0.9.9-rebased-on-common-base`

Of the 109 commits on `rvy-0.9.9-rebased-on-common-base`:
- **31** Part 1 commits with `drop_on_rebase=True` are dropped (Toooba/CVA6/TestRIG hardware hacks,
  Makefile-only commits, and commits already in `origin/codasip` or folded into
  `rebased-patches/000[1-4]-*.patch`). For TestRIG-only comparisons against the split-repo binary,
  which compiled in the Toooba `envcfg` and CVA6 `tvec` hacks from `82a451fd` and `e3610d6d` (and
  had `sys_pa_bits = 39` instead of `56`), `testrig/match-split-toooba-hacks.diff` (and
  `testrig/disable-extensions-missing-in-split.diff` on `rvy-0.9.9-rebased-on-common-base`) matches
  those settings in a temporary worktree without polluting the branches.
- **4** Part 2 RV32 follow-up commits (`rv32-fixes/0001-*.patch` .. `0004-*.patch`, with
  `fold_on_rebase=True`) are folded directly into the commits they fix (`Detect if no invalid addresses
  in test`, `Update to new CHERI fault reporting`, `Update YBNDSWI encoding`, `Mode-related
  renamings`), because `origin/codasip` compiles both RV32 (`cheri_prelude_64.sail`) and RV64
  (`cheri_prelude_128.sail`) into the single `sail_riscv_sim` binary via `cheri_prelude_xlen.sail`.

### Mid-series build fixes on `rvy-0.9.9-rebased-on-head` (`rebased-patches/rebase/*.diff`)

`build_rebased_branch()` applies 15 small post-rerere diffs in `rebased-patches/rebase/<sha>-*.diff`
so that every commit in `origin/codasip..rvy-0.9.9-rebased-on-head` builds cleanly and passes
`--self-test`:

- **`Re-enable self tests` (`rebased-patches/rebase/512bb94-re-enable-self-tests.diff`):**
  Wires `test_main_ext.sail` into `CMakeLists.txt` with `execute_test` (`Ext_ControlAddr_Check_Failure`
  and `Ext_XRET_Priv_Failure` arms, 3-arg `handle_translate_exception`, and `mseccfg[CRE] = ...`).
- **`Remove CHERI branch exception checks`, `Update to new CHERI fault reporting`, and `xret and cbo.inval all throw illegal if no ASR` (`rebased-patches/rebase/{475e4c2,ab30556,eb7c333}-*.diff`):**
  Stages each `ExecutionResult` change in its respective commit so `Remove CHERI branch
  exception checks` through `Reserve some branch encodings in capmode` stay buildable.
- **`Avoid using separate names for CHERI CSRs` (`rebased-patches/rebase/9063f09-avoid-using-separate-names-for-cheri-csrs.diff`):**
  Preserves `origin/codasip` PR #20 (`Legalize mepcc/sepcc on read, not just on write`) when
  renaming `mepcc`/`sepcc`/`get_mepcc`/`get_sepcc` to `mepc_y`/`sepc_y`/`get_mepc_y`/`get_sepc_y`
  in `model/cheri/cheri_sys_exceptions.sail` and `model/cheri/cheri_sys_regs_access.sail`.
- **`Perform instruction renaming (e.g. ywbase)` (`rebased-patches/rebase/be3d0a2-perform-instruction-renaming.diff`):**
  Keeps `shamt : shamt_zba` in `ZBA_RTYPEYUW` and `ZBA_RTYPE_Y` in
  `model/cheri/cheri_insts_zba.sail` instead of reverting to `bropw_zba`/`brop_zba` (which were
  replaced by `shamt_zba` in `origin/codasip`), until `Add separate YSH<n>ADD[UW] encodings`
  replaces them with `ZBA_Y_RTYPEUW` and `ZBA_Y_RTYPE` (`bropw_zba_y`/`brop_zba_y`).
- **`Add allowSealedUnchanged operand to setAddrChecked` (`rebased-patches/rebase/5a72076-add-allowsealedunchanged.diff`) and `Fix: JALR with non-zero immediate to sentries left tag set and could change their address` (`rebased-patches/rebase/5083802-jalr-non-zero-imm-sentry.diff`):**
  Applies the 3-argument `setCapAddrChecked` update to `model/riscv_pc_access.sail` (`tick_pc` and
  `force_pc`) and `get_mepc_y()` / `get_sepc_y()` in `model/cheri/cheri_sys_regs_access.sail`.
- **`Reset registers to null_cap` (`117b61a`, via `rr-cache`):**
  Replaces the PR #19 GPR canonicalization loop in `ext_reset_cheri()` in
  `model/cheri/cheri_step_ext.sail` with `foreach (i from 1 to 31) wX_full(Regno(i), null_cap);`
  (matching `ext_rvfi_reset()`'s `foreach` loop style from PR #18).

### Split-repo bugfix patches (`split-repo-fixes/0001-*.patch` .. `0002-*.patch`)

- **`split-repo-fixes/0001-Fix-TaggedLoadTrap-to-raise-CHERI-load-page-fault-ex.patch`:**
  Fixes `LoadResCap`, `LoadCapImm`, and `AMOSwapCap` in `cheri_insts.sail` to raise
  `E_Extension(EXC_CHERI(CapCheckType_Pte(CheriPage_Ld)))` instead of `E_Load_Page_Fault()` on
  `TaggedLoadTrap`.
- **`split-repo-fixes/0002-Fix-AMOSwapCap-to-reserve-rs1-zreg-in-CapPtrMode.patch`:**
  Fixes `AMOSwapCap` (`amoswap.y`) in `cheri_insts.sail` to reserve `rs1 = zreg` in `CapPtrMode`
  (`& (rs1 != zreg | effective_cheri_mode() == IntPtrMode)`) and adds `test_cheri_reserved_load_store()`
  in `test_main_ext.sail`.

## Phase 3: Cleaned History for PR -> `rvy-0.9.9-cleaned-history`

`build_cleaned_branch()` in `reproduce_all.py` constructs `rvy-0.9.9-cleaned-history` (42 commits
on `origin/codasip`) from `rvy-0.9.9-rebased-on-head` (78 commits), producing an **identical final
tree** (`git diff rvy-0.9.9-rebased-on-head rvy-0.9.9-cleaned-history` is empty) while removing
mid-series reverts, churn, and fixups of earlier commits in the series:

- **Dropped commit + revert pair (2 -> 0):**
  - `Remove special treatment of DDC as 'YLenNew'` and `Revert "Remove special treatment of DDC as 'YLenNew'"`.
- **Squashed same-series fixups into the commits they fix (47 -> 13):**
  - `Re-enable self tests`: folds the 4 pre-enable `test_main_ext.sail` fixes (`Remove tdc registers from testing`, `Detect if no invalid addresses in test`, `Test modifications to mscratch, not mtvec`, `Fix comment parsing`) so no commit modifies `test_main_ext.sail` before it is wired into `CMakeLists.txt`.
  - `Remove CHERI branch exception checks`: folds `Clear tag if target PCC is unrepresentable`, `Add allowSealedUnchanged operand to setAddrChecked`, `Fix successful jump assertion in tests`, `Fix: JALR must not unseal target cap on non-zero imm`, and `Fix: JALR with non-zero immediate to sentries left tag set and could change their address` so `JALR_capmode`, `tick_pc()`, and `test_cheri_bad_jump()` have the complete, non-buggy unsealing and representability behavior right when branch exception checks are removed.
  - `Update to new CHERI fault reporting`: folds `Promote accessed faults to potentially imply 'both' cheri and non-cheri error`, `Fix inverted CHERI PTE permission check`, `Return to A/D being handled alongside other PTE perm failures`, and `Fix TaggedLoadTrap to raise CHERI load page fault exception` (`0001`).
  - `Implement broader integrity checks`: squashes `ACPERM clears tag if input perms malformed` (whose 5 modified lines were 100% overwritten by `Implement broader integrity checks`).
  - `Reserve some branch encodings in capmode`: folds `Flip reserved branch encodings`.
  - `Avoid using separate names for CHERI CSRs`: folds `xtidc is YLenNew, not extended`.
  - `Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y`: folds `Add misa.Y support` and `Move Y to bit 9 in xenvcfg`.
  - `Update CHERI PTEs to 4-bit Svyrg scheme`: folds the intermediate 3-bit PTE commits (`Rework Svucrg to 3-bit CHERI PTEs`, `Rename PTE CW to CRW`, `Add CRGE ucrg enable bit in xstatus`, `CRGE clear implies reserved CD and CRG`) into `4-bit PTE scheme`.
  - `Add YSUNSEAL`: folds `Fix YSUNSEAL check`.
  - `Rename ybndsiw to ybndswi and update encoding`: folds `Update YBNDSIW encoding`, `Rename ybndsiw to ybndswi`, and `Update YBNDSWI encoding`.
  - `Fix YMODEW to have full integrity checks`: folds `Fix YMODEW to honour "otherwise" in spec`.
  - `Implement new instruction encodings`: folds its 5 immediate encoding fixups (`Fix YSENTRY encoding`, `Fix YMODER encoding`, `Fix SENTRY encoding`, `Fix sentry operand order encoding`, `Fix YMODEW encoding to reserve rd=0`) plus `rs1 != zreg` on `AMOSwapCap`.
  - `Change metadata field arrangement`: folds `Move the mode bit to the bottom of the AP field`.
  - `Memory accesses can use zreg in IntPtrMode`: folds `Fix: SY can have rs1=0 in int_mode` and `Fix AMOSwapCap to reserve rs1=zreg in CapPtrMode` (`0002`).

### Verification summary

- **Per-commit builds & self-tests:**
  - `rvy-0.9.9-rebased-on-common-base` (`split-merged-baseline..rvy-0.9.9-rebased-on-common-base`,
    109 commits): all 109 commits pass CMake RV64 (`riscv_sim_rv64d` + `riscv_sim_rv64d_rvfi`),
    CMake RV32 (`riscv_sim_rv32d`), and Makefile (`ARCH=RV64` + `ARCH=RV32`), with only the 9
    expected pre-`82d371e` Makefile RVFI `XFAIL`s.
  - `rvy-0.9.9-rebased-on-head` (`origin/codasip..rvy-0.9.9-rebased-on-head`, 78 commits): all 78
    commits build cleanly and pass `--sail-check`.
  - `rvy-0.9.9-cleaned-history` (`origin/codasip..rvy-0.9.9-cleaned-history`, 42 commits): all 42
    commits pass a full `cmake --build cmake-build-debug` (`sail_riscv_sim`) build, `--sail-check`,
    and RV64 + RV32 `--self-test` (`0 unexpected failure(s), 0 expected (XFAIL)` in
    `output/rvy-0.9.9-cleaned-history/build-check/summary.txt`), and its final tree is identical to
    `rvy-0.9.9-rebased-on-head`.
- **Self-tests:**
  - RV64 (`./cmake-build-debug/c_emulator/sail_riscv_sim --self-test`) and RV32
    (`./cmake-build-debug/c_emulator/sail_riscv_sim --config config/rv32d.json --self-test`) pass
    on every commit from `Re-enable self tests` through the tip of `rvy-0.9.9-cleaned-history`
    (including `test_cheri_bad_jump()` from `71610658` and `test_cheri_reserved_load_store()` from
    `0002-Fix-AMOSwapCap-to-reserve-rs1-zreg-in-CapPtrMode.patch`).
- **TestRIG (`run_testrig_sail_vs_sail.py`):**
  - `./run_testrig_sail_vs_sail.py baseline`: 29/29 active QCVEngine instruction generator groups
    pass (`output/testrig-baseline/qcvengine.log`).
  - `./run_testrig_sail_vs_sail.py rebased`: 29/29 active QCVEngine instruction generator groups
    pass (`output/testrig-rebased/qcvengine.log`).


