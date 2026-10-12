#!/usr/bin/env python3
"""Reproduce the CapLtd 0.9.9 CHERI Sail branches."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
MERGED_REPO = Path(
    os.environ.get(
        "MERGED_REPO",
        subprocess.run(
            ["git", "-C", str(SCRIPT_DIR), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip(),
    )
)
SPLIT_CHERI_REPO = Path(
    os.environ.get(
        "SPLIT_CHERI_REPO",
        str(MERGED_REPO.parent / "rvy-sail-cheri-riscv"),
    )
)
SPLIT_SAIL_REPO = Path(
    os.environ.get("SPLIT_SAIL_REPO", str(SPLIT_CHERI_REPO / "sail-riscv"))
)
SAIL_BIN = Path(os.environ.get("SAIL_BIN", shutil.which("sail") or "sail"))


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    author: str
    date: str
    subject: str
    message: str


@dataclass(frozen=True)
class Entry:
    origin_repo: str = ""  # "cheri", "sail", or "" for patch files
    origin_sha: str = ""
    sail_shas: tuple[str, ...] = ()
    patch_path: str = ""
    drop_on_rebase: bool = False
    only_on_rebase: bool = False
    fold_on_rebase: bool = False
    drop_on_clean: bool = False
    squash_into: str = ""
    clean_title: str = ""

    @property
    def entry_id(self) -> str:
        return Path(self.patch_path).stem if self.patch_path else self.origin_sha[:7]


def cheri(sha: str, *sail_shas: str, **kwargs: Any) -> Entry:
    return Entry(origin_repo="cheri", origin_sha=sha, sail_shas=sail_shas, **kwargs)


def sail(sha: str, **kwargs: Any) -> Entry:
    return Entry(origin_repo="sail", origin_sha=sha, **kwargs)


def patch(path: str, **kwargs: Any) -> Entry:
    return Entry(patch_path=path, **kwargs)


# Per-commit adjustment diffs are matched automatically by <entry_id>*.diff in:
#   adjustments/              applied on rvy-0.9.9-rebased-on-common-base
#   rebased-patches/rebase/   applied on rvy-0.9.9-rebased-on-head
#   rebased-patches/cleaned/  applied on rvy-0.9.9-cleaned-history
# fmt: off
COMMITS: list[Entry] = [
    # Pre-series foundation patches for origin/codasip
    patch("rebased-patches/0001-upstream-zba-rtypeuw-encoding.patch", only_on_rebase=True),
    patch("rebased-patches/0002-upstream-sc-phys-access-and-alignment.patch", only_on_rebase=True),
    patch("rebased-patches/0003-rvfi-dii-memory-range.patch", only_on_rebase=True),
    patch("rebased-patches/0004-rvfi-ext-reset-cheri.patch", only_on_rebase=True),

    # Part 1: split-repo baseline (245f6087..726b5ac and sail-riscv up to 74194fd)
    sail("6d8cafdb", drop_on_rebase=True),                      # Fixes to work with TestRIG
    sail("dc8ec197", drop_on_rebase=True),                      # Restore RVFI DII memory region restrictions
    sail("ea15966c", drop_on_rebase=True),                      # Restore RVFI read and write reporting
    sail("cb6b63ae", drop_on_rebase=True),                      # Fix range checking wrap bug in RVFI memory range
    sail("9ef5189d", drop_on_rebase=True),                      # Add catchall default false extensionEnabled
    # skip sail b6a6dda8: Fixup memory types (folded into dc8ec197 and ea15966c)
    patch("rv32-fixes/0000-rv32-rvfi-dii-physaddr.patch", drop_on_rebase=True),
    cheri("8dc1750c", drop_on_rebase=True),                     # Fixes for running with TestRIG
    sail("9479bf45", drop_on_rebase=True),                      # Fix resets
    cheri("d11a7bff", drop_on_rebase=True),                     # Make lr/sc encdec mapping formatting consistent
    cheri("82d371e2", drop_on_rebase=True),                     # Makefile fixes
    # skip cheri 5d367c45: .gitmodules only
    cheri("c78f5c0f", drop_on_rebase=True),                     # Comment out tag-clearing reset for testrig
    cheri("26788339", drop_on_rebase=True),                     # Include zifencei in Makefile
    cheri("5ea51b6e", drop_on_rebase=True),                     # Hardwire cre to true in mseccfg
    cheri("82a451fd", drop_on_rebase=True),                     # Legalise envcfg registers to match hardwired Toooba
    sail("44c7a9b9", drop_on_rebase=True),                      # Fix out-of-range xcause length
    sail("94e9ab8c", drop_on_rebase=True),                      # Legalise mtvec by masking
    sail("2a46f0e7", drop_on_rebase=True),                      # Legalise cause field more aggressively
    sail("1fda4b95", drop_on_rebase=True),                      # Mask mode on SATP writes
    cheri("59586f8b", drop_on_rebase=True),                     # Add CHERI CSR extending file to Makefile
    cheri("97fc9d5f", drop_on_rebase=True),                     # Remove features from mseccfg unsupported by Toooba
    cheri("d6b354e4", drop_on_rebase=True),                     # Reenable writable fiom
    sail("e3610d6d", drop_on_rebase=True),                      # Move to CVA6 tvec legalisation function
    # skip sail 29a70382: Identical to merged-repo commit 4f1dae4d "Add missing mtval write"
    sail("2b89f1f0", drop_on_rebase=True),                      # Preserve all cause bits to match CVA6
    sail("12943e2f", drop_on_rebase=True),                      # Allow compressed hints to be expanded
    sail("b8c7d8c2", drop_on_rebase=True),                      # Disable fetch translation checks with RVFI to compare to CVA6
    cheri("629a4361", drop_on_rebase=True),                     # Flip polarity of leaf check in CHERI PTE invalid checks
    cheri("a0099ab4", drop_on_rebase=True),                     # PTE check fixes
    sail("6707d982", drop_on_rebase=True),                      # Disable PMA checks with TestRIG
    sail("92e25bb9", drop_on_rebase=True),                      # Remove Toooba-specific satp legalisation
    cheri("726b5ac3", squash_into="ab30556"),                   # Promote accessed faults to potentially imply 'both' cheri and non-cheri error
    sail("74194fdf", drop_on_rebase=True),                      # Disable napot

    # Part 2: CapLtd 0.9.9 work (db7355e..74753ce, sail-riscv 74194fd..7512afd)
    cheri("65c7eb9"),                                           # Add reserved ones to decoded BitPerms
    cheri("c2bba77", squash_into="512bb94"),                    # Remove tdc registers from testing
    cheri("8b49265", squash_into="512bb94"),                    # Detect if no invalid addresses in test
    patch("rv32-fixes/0001-rv32-detect-if-no-invalid-addresses.patch", fold_on_rebase=True),
    cheri("8e5ec4c", squash_into="512bb94"),                    # Test modifications to mscratch, not mtvec
    cheri("de31533", squash_into="512bb94"),                    # Fix comment parsing
    cheri("512bb94", "764f9f1"),                                # Re-enable self tests
    cheri("3281cc8"),                                           # Move from C to Y
    cheri("a91c295"),                                           # Fix ASR checking bug on cbo.inval
    cheri("63ca014"),                                           # Require whole-line bounds for cbo.inval
    cheri("185f9d0"),                                           # Access fault on misaligned capabilities
    cheri("8a9582f", "f36af41"),                                # Remove CHERI branch exception checks
    cheri("ab30556", "4fead73", "5593d59"),                     # Update to new CHERI fault reporting
    patch("rv32-fixes/0002-rv32-new-cheri-fault-reporting.patch", fold_on_rebase=True),
    cheri("f62f7a3", squash_into="32be9d4"),                    # ACPERM clears tag if input perms malformed
    cheri("32be9d4"),                                           # Implement broader integrity checks
    cheri("4d592b9"),                                           # Reserve some branch encodings in capmode
    cheri("1316336", drop_on_rebase=True),                      # Include Zicbo files in CHERI build
    cheri("04106dc", "ec4c1fe"),                                # xret and cbo.inval all throw illegal if no ASR
    cheri("0d78a40", squash_into="8a9582f"),                    # Clear tag if target PCC is unrepresentable
    cheri("aa10d9b"),                                           # Rename load and store instructions to use Y datatype
    cheri("84ace6b"),                                           # Remove tdc registers
    cheri("9063f09"),                                           # Avoid using separate names for CHERI CSRs
    cheri("80b7468"),                                           # Perform instruction renaming (e.g. ywbase)
    sail("6420604", drop_on_rebase=True),                       # Remove option not to expand hints
    cheri("03960a0", drop_on_clean=True),                       # Remove special treatment of DDC as 'YLenNew'
    sail("48f9032", squash_into="c67ba25"),                     # Add misa.Y support
    cheri("c67ba25", "1567214"),                                # Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y
    cheri("d23b51b"),                                           # Another ISA renaming (e.g. YBASER)
    cheri("6ee2813"),                                           # Add separate YSH<n>ADD[UW] encodings
    cheri("479f7ff"),                                           # SRLIY and PACKY
    cheri("02afac7", squash_into="f9081f5"),                    # Update YBNDSIW encoding
    cheri("bfae32c", squash_into="f9081f5"),                    # Rename ybndsiw to ybndswi
    cheri("2853897"),                                           # Change YPERMC to bit-clearing
    cheri("d6bc2cb"),                                           # Massive operand renaming
    cheri("5a95a40"),                                           # Root not infinite caps
    cheri("7788d28", "16bec3c", clean_title="Update CHERI PTEs to 4-bit Svyrg scheme"),  # Rework Svucrg to 3-bit CHERI PTEs
    cheri("b22e1d2", squash_into="7788d28"),                    # Rename PTE CW to CRW
    cheri("1f14ef1"),                                           # Remove some MXLENs
    cheri("60a554b"),                                           # Add YSUNSEAL
    cheri("f9081f5", clean_title="Rename ybndsiw to ybndswi and update encoding"),  # Update YBNDSWI encoding
    patch("rv32-fixes/0003-rv32-ybndswi-test.patch", fold_on_rebase=True),
    cheri("cc4f53c"),                                           # Rename CL to GL
    cheri("874aa6e", squash_into="7788d28"),                    # Add CRGE ucrg enable bit in xstatus
    cheri("f7106ea"),                                           # Add YTOPR
    cheri("f573e04"),                                           # Fix YMODEW to have full integrity checks
    cheri("083fa15", squash_into="7788d28"),                    # CRGE clear implies reserved CD and CRG
    cheri("fcf4a2f", squash_into="f573e04"),                    # Fix YMODEW to honour "otherwise" in spec
    cheri("d038596", squash_into="7788d28"),                    # 4-bit PTE scheme
    cheri("8d42af8", squash_into="4d592b9"),                    # Flip reserved branch encodings
    cheri("8d6ca2d"),                                           # Rename ADD(I)Y to YADD(I)
    cheri("6d4651c"),                                           # YLT -> YSS, SYEQ -> YEQ
    cheri("20c04ad"),                                           # Mode-related renamings
    patch("rv32-fixes/0004-rv32-mode-related-renamings.patch", fold_on_rebase=True),
    cheri("5b0712e", drop_on_clean=True),                       # Revert "Remove special treatment of DDC as 'YLenNew'"
    cheri("157a45a"),                                           # Implement new instruction encodings
    cheri("8dbac54", "7512afd"),                                # Prevent disabling Y unless system caps are root
    cheri("ef9839a", squash_into="157a45a"),                    # Fix YSENTRY encoding
    cheri("90bcdd2", squash_into="c67ba25"),                    # Move Y to bit 9 in xenvcfg
    cheri("90e2703"),                                           # Change metadata field arrangement
    cheri("e839930"),                                           # Memory accesses can use zreg in IntPtrMode
    cheri("41c40d9", squash_into="157a45a"),                    # Fix YMODER encoding
    cheri("37d1d4d", squash_into="157a45a"),                    # Fix SENTRY encoding
    cheri("3992e63", squash_into="157a45a"),                    # Fix sentry operand order encoding
    cheri("69a87b0", squash_into="90e2703"),                    # Move the mode bit to the bottom of the AP field
    cheri("b9b8f24", drop_on_rebase=True),                      # Add Zcb to Makefile
    cheri("176fde1", squash_into="157a45a"),                    # Fix YMODEW encoding to reserve rd=0
    cheri("12ef78a", squash_into="9063f09"),                    # xtidc is YLenNew, not extended
    cheri("8320d28", squash_into="ab30556"),                    # Fix inverted CHERI PTE permission check
    cheri("5576a0c", squash_into="e839930"),                    # Fix: SY can have rs1=0 in int_mode
    cheri("543bd62", squash_into="60a554b"),                    # Fix YSUNSEAL check
    cheri("74753ce", squash_into="ab30556"),                    # Return to A/D being handled alongside other PTE perm failures
    sail("e6752e8"),                                            # Don't indicate x in misa.
    cheri("5a72076", squash_into="8a9582f"),                    # Add allowSealedUnchanged operand to setAddrChecked
    cheri("f57f783", squash_into="8a9582f"),                    # Fix successful jump assertion in tests
    cheri("7161065", squash_into="8a9582f"),                    # Fix: JALR must not unseal target cap on non-zero imm
    cheri("5083802", squash_into="8a9582f"),                    # Fix: JALR with non-zero immediate to sentries left tag set and could change their address
    cheri("117b61a"),                                           # Reset registers to null_cap

    # Split-repo bugfix patches (applied on origin/codasip and squashed on cleaned branch)
    patch("split-repo-fixes/0001-Fix-TaggedLoadTrap-to-raise-CHERI-load-page-fault-ex.patch", only_on_rebase=True, squash_into="ab30556"),
    patch("split-repo-fixes/0002-Fix-AMOSwapCap-to-reserve-rs1-zreg-in-CapPtrMode.patch", only_on_rebase=True, squash_into="e839930"),
]
# fmt: on


def run_git(
    repo: Path,
    *args: str | Path,
    check: bool = True,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "-C", str(repo), *(str(a) for a in args)]
    run_env = {**os.environ, **env} if env else None
    res = subprocess.run(
        cmd, input=input_text, text=True, capture_output=True, env=run_env, check=False
    )
    if check and res.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {res.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
    return res


def git_stdout(repo: Path, *args: str | Path, strip: bool = True) -> str:
    out = run_git(repo, *args).stdout
    return out.strip() if strip else out


def get_commits(repo: Path, rev_range: str) -> list[CommitInfo]:
    shas = git_stdout(repo, "rev-list", "--reverse", rev_range).splitlines()
    commits: list[CommitInfo] = []
    for sha in shas:
        meta = git_stdout(repo, "log", "-1", "--format=%an <%ae>%n%aD%n%s", sha).splitlines()
        msg = git_stdout(repo, "log", "-1", "--format=%B", sha)
        commits.append(CommitInfo(sha, meta[0], meta[1], meta[2], msg))
    return commits


def prepare_worktree(worktree: Path, base_ref: str) -> None:
    if not worktree.exists():
        worktree.parent.mkdir(parents=True, exist_ok=True)
        run_git(MERGED_REPO, "worktree", "add", "--detach", worktree, base_ref)
    for op in ("am", "cherry-pick", "rebase"):
        run_git(worktree, op, "--abort", check=False)
    run_git(worktree, "checkout", "-q", "--detach")
    run_git(worktree, "reset", "--hard", "-q", base_ref)
    run_git(
        worktree,
        "clean",
        "-fdq",
        "-e",
        "cmake-build-debug",
        "-e",
        "model/sail_smt_cache",
        "-e",
        "sail_smt_cache",
    )
    run_git(worktree, "config", "rerere.enabled", "true")
    run_git(worktree, "config", "rerere.autoupdate", "true")
    rr_src = SCRIPT_DIR / "rr-cache"
    if rr_src.is_dir():
        common_dir = Path(git_stdout(worktree, "rev-parse", "--git-common-dir"))
        if not common_dir.is_absolute():
            common_dir = (worktree / common_dir).resolve()
        rr_dst = common_dir / "rr-cache"
        rr_dst.mkdir(parents=True, exist_ok=True)
        for item in rr_src.iterdir():
            if item.is_dir():
                dest = rr_dst / item.name
                dest.mkdir(parents=True, exist_ok=True)
                for f in item.iterdir():
                    shutil.copy2(f, dest / f.name)


def update_branch(branch: str, sha: str) -> None:
    wt = MERGED_REPO / ".worktrees" / branch
    if wt.is_dir():
        run_git(wt, "checkout", "-q", "--detach", check=False)
    run_git(MERGED_REPO, "branch", "-f", branch, sha)


def resolve_conflicts_with_rerere(worktree: Path, drop_makefile: bool = False) -> None:
    unmerged = git_stdout(worktree, "diff", "--name-only", "--diff-filter=U").splitlines()
    if drop_makefile and "Makefile" in unmerged:
        run_git(worktree, "checkout", "HEAD", "--", "Makefile")
    for path in unmerged:
        if drop_makefile and path == "Makefile":
            continue
        stages = {
            line.split()[2]
            for line in git_stdout(worktree, "ls-files", "-u", "--", path).splitlines()
        }
        if "2" not in stages or "3" not in stages:
            run_git(worktree, "rm", "-q", "--", path)
    run_git(worktree, "rerere")
    remaining = git_stdout(worktree, "diff", "--name-only", "--diff-filter=U").splitlines()
    if remaining:
        raise RuntimeError(f"Unresolved conflict after rerere: {remaining}")


def am_3way(worktree: Path, patch_text: str) -> None:
    res = run_git(worktree, "am", "-3", "-q", "--empty=keep", input_text=patch_text, check=False)
    if res.returncode != 0:
        resolve_conflicts_with_rerere(worktree)
        run_git(worktree, "add", "-u")
        run_git(worktree, "am", "--continue", env={"GIT_EDITOR": "true"})


def cherry_pick_rerere(worktree: Path, sha: str, drop_makefile: bool = False) -> None:
    res = run_git(worktree, "cherry-pick", "-n", "-X", "no-renames", sha, check=False)
    if res.returncode != 0:
        resolve_conflicts_with_rerere(worktree, drop_makefile=drop_makefile)


TRAILER_PREFIXES = (
    "(cherry picked from ",
    "(squashed with ",
    "Merged-repo-adjustment-applied:",
)
RE_COMBINATION_LINE = re.compile(
    r"(?:\n\n|^)(?:This is a combination of \d+ commits\.|Combination of the following commits:[\s\S]*)$"
)
RE_CAPLTD_TRAILER = re.compile(
    r"^\((?:cherry picked from|squashed with) (rvy-sail-cheri-riscv(?:/sail-riscv)?) commit ([0-9a-f]{40})"
)
RE_RISCV_CHERI_REFS = re.compile(
    r"\briscv-cheri(?:\s+commit)?\s+([0-9a-f]{7,40}(?:(?:\s*,\s*|\s+and\s+|\s*,\s+and\s+)[0-9a-f]{7,40})*)"
)

SUMMARY_MESSAGES: dict[str, str] = {
    "0003-rvfi-dii-memory-range": """Restore RVFI DII memory region restrictions

Restrict physical memory reads and writes to [0x80000000, 0x80800000)
when running in RVFI mode (get_config_rvfi()), without wrapping at the
top of the address space.""",
    "0004-rvfi-ext-reset-cheri": """Fixes for running with TestRIG

Ensure ext_reset_cheri() is always called in ext_reset() before
ext_rvfi_reset() when running in RVFI mode.""",
    "512bb94": """Re-enable self tests

Enable running the CHERI self-tests via --self-test, update the CSR self
tests to use mscratch instead of mtvec and remove tdc, and skip invalid
address checks when xlen_val == 32 or no invalid addresses exist.""",
    "8a9582f": """Remove CHERI branch exception checks

Remove CHERI exception checks and branch hooks on jumps and branches as
required by the 0.9.9 specification. Since nextPCC and nextPC can now
become desynchronised, check representability in tick_pc() and clear the
tag if the target PCC is unrepresentable or sealed (unless unsealing a
sentry on JALR with a zero immediate).

Credit to Ben Laurie & Claude (Opus 5.5) for highlighting the JALR
non-zero immediate sentry bug and the security concerns as part of a
Rocq monotonicity proof, plus suggesting the fix.

Advanced Research and Innovation Agency (ARIA) Contract MSAI-PR01-P060,
"AI Verified Hardware for AI (AIVHAI)"

From riscv/riscv-cheri@a4527b8b""",
    "ab30556": """Update to new CHERI fault reporting

Replace the xcheri_trap CSR fault reporting fields with dedicated CHERI
exception cause codes for capability bounds/tag/seal/permission/mode
faults and CHERI page faults, and check PTE A/D bits alongside other PTE
permission checks.

From riscv/riscv-cheri@8046b598""",
    "32be9d4": """Implement broader integrity checks

Clear tags on malformed capabilities across capability manipulation
instructions (including ACPERM when input permissions are malformed).

Note there seems to be a bit of ambiguity in how ACPERM should read
the permissions in the malformed cases. I've implemented this as
mirroring GCPERM for now.

From riscv/riscv-cheri@7dd8a4bf and riscv/riscv-cheri@d85efae7""",
    "4d592b9": """Reserve some branch encodings in capmode

Reserve BEQ/BNE encodings with rs1 == rs2 in CapPtrMode.

From riscv/riscv-cheri@d636fd74 and riscv/riscv-cheri@a3cb83d8""",
    "04106dc": """xret and cbo.inval all throw illegal if no ASR

Share the extension privilege-checking hook between xret and cbo.inval
so that missing ASR raises an illegal instruction exception rather than
a CHERI fault.

From riscv/riscv-cheri@c875b2ea and riscv/riscv-cheri@8e9d0812""",
    "9063f09": """Avoid using separate names for CHERI CSRs

Unfortunately, actually using the same register names would require
a fairly major refactor of the base model, so leave a _y postfix for
accesses to the actual registers. Also mark xtidc as YlenNew rather than
YlenExt.

From riscv/riscv-cheri@c37e238e""",
    "c67ba25": """Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y

Replace mseccfg.CRE and xenvcfg.CRE with misa.Y and xenvcfg.Y (at bit 9
of menvcfg/senvcfg/henvcfg) and remove the CHERI-specific mseccfg
handling.

From riscv/riscv-cheri@ad1c61a8 and riscv/riscv-cheri@4a340114""",
    "7788d28": """Update CHERI PTEs to 4-bit Svyrg scheme

Update the CHERI PTE bits to the 4-bit Svyrg encoding (YD, YRG, YRW,
YDT), add the xstatus.YRGE enable bit, and split ext_ptw reserved into
high and low fields.

From riscv/riscv-cheri@5e9d91c2, riscv/riscv-cheri@542e6999,
riscv/riscv-cheri@91b59fba, riscv/riscv-cheri@a3ab4951, and
riscv/riscv-cheri@e52a581e""",
    "60a554b": """Add YSUNSEAL

From riscv/riscv-cheri@8a024a66 and riscv/riscv-cheri@28781921""",
    "f9081f5": """Rename ybndsiw to ybndswi and update encoding

From riscv/riscv-cheri@9994769b, riscv/riscv-cheri@c21cdf34, and
riscv/riscv-cheri@29cea229""",
    "f573e04": """Fix YMODEW to have full integrity checks

Perform full capability integrity checks in YMODEW and preserve the tag
only when the capability is unsealed and has X permission.

From riscv/riscv-cheri@b89ac4de""",
    "157a45a": """Implement new instruction encodings

Update instruction encodings for the 0.9.9 specification, including
YSENTRY, YMODER, and YMODEW (reserving rd=0).

From riscv/riscv-cheri@8e6d67ed, riscv/riscv-cheri@0f249b68,
riscv/riscv-cheri@9a8b9709, riscv/riscv-cheri@64385508,
riscv/riscv-cheri@d5e918ba, and riscv/riscv-cheri@48971fc7""",
    "8dbac54": """Prevent disabling Y unless system caps are root

Add a hook to legalize_misa() and prevent clearing misa.Y unless all
system capabilities hold root capabilities.

From riscv/riscv-cheri@ce64aa26, riscv/riscv-cheri@7d160a17, and
riscv/riscv-cheri@e38a013f""",
    "90e2703": """Change metadata field arrangement

Update the capability metadata bit layout and move the pointer mode bit
to the bottom of the architectural permissions (AP) field.

From riscv/riscv-cheri@ac16ea08""",
    "e839930": """Memory accesses can use zreg in IntPtrMode

Allow rs1=zreg in IntPtrMode while reserving rs1=zreg in CapPtrMode for
capability loads, stores, LR.Y, SC.Y, and AMOSWAP.Y.

From riscv/riscv-cheri@e919dab5""",
}


def linkify_riscv_cheri_refs(msg: str) -> str:
    def _replace_match(m: re.Match[str]) -> str:
        shas = re.findall(r"[0-9a-f]{7,40}", m.group(1))
        refs = [f"riscv/riscv-cheri@{s[:8]}" for s in shas]
        if len(refs) == 1:
            return refs[0]
        if len(refs) == 2:
            return f"{refs[0]} and {refs[1]}"
        return f"{', '.join(refs[:-1])}, and {refs[-1]}"

    msg = msg.replace(
        "but the conrete reset caps are renamed root caps",
        "but the concrete reset caps are renamed root caps.",
    )
    msg = re.sub(r"^Don't indicate x in misa\.", "Don't indicate x in misa", msg)

    out_lines: list[str] = []
    for line in msg.splitlines():
        new_line = RE_RISCV_CHERI_REFS.sub(_replace_match, line)
        if new_line.startswith("from riscv/riscv-cheri@"):
            new_line = "F" + new_line[1:]
        if new_line != line and len(new_line) > 72:
            new_line = textwrap.fill(
                new_line, width=72, break_long_words=False, break_on_hyphens=False
            )
        out_lines.append(new_line)
    return "\n".join(out_lines)


def extract_capltd_refs(trailers: list[str]) -> list[str]:
    refs: list[str] = []
    for line in trailers:
        m = RE_CAPLTD_TRAILER.match(line.strip())
        if m:
            repo = (
                "Capabilities-Limited/sail-cheri-riscv"
                if m.group(1) == "rvy-sail-cheri-riscv"
                else "Capabilities-Limited/sail-riscv"
            )
            ref = f"{repo}@{m.group(2)[:8]}"
            if ref not in refs:
                refs.append(ref)
    return refs


def format_combination_line(refs: list[str], fallback_count: int = 0) -> str:
    if len(refs) < 2:
        return f"This is a combination of {fallback_count} commits."
    prefix = "Combination of the following commits: "
    lines: list[str] = []
    cur = prefix
    for i, ref in enumerate(refs):
        sep = ", " if i < len(refs) - 1 else ""
        token = f"{ref}{sep}"
        if cur != prefix and len(cur) + len(token) > 80:
            lines.append(cur.rstrip())
            cur = token
        else:
            cur += token
    if cur:
        lines.append(cur.rstrip())
    return "\n".join(lines)


def split_into_constituent_messages(msg: str) -> tuple[list[str], list[str]]:
    body_lines: list[str] = []
    trailers: list[str] = []
    for line in msg.strip().splitlines():
        if line.startswith(TRAILER_PREFIXES):
            trailers.append(line)
        else:
            body_lines.append(line)
    cleaned = "\n".join(body_lines).strip()
    chunks = [c.strip() for c in cleaned.split("\n\n----\n\n") if c.strip()]
    if chunks:
        chunks[0] = RE_COMBINATION_LINE.sub("", chunks[0]).strip()
    return [c for c in chunks if c], trailers


def combine_commit_messages(
    messages: list[str],
    clean_title: str = "",
    trailers: list[str] | None = None,
    ref_trailers: list[str] | None = None,
) -> str:
    messages = [linkify_riscv_cheri_refs(m.strip()) for m in messages if m.strip()]
    refs = extract_capltd_refs(ref_trailers if ref_trailers is not None else (trailers or []))
    combo = format_combination_line(refs, fallback_count=len(messages))
    if clean_title:
        header = f"{clean_title}\n\n{combo}"
        body = "\n\n----\n\n".join([header, *messages])
    elif len(messages) > 1:
        first = f"{messages[0]}\n\n{combo}"
        body = "\n\n----\n\n".join([first, *messages[1:]])
    else:
        body = messages[0] if messages else ""
    if trailers:
        trailer_block = "\n".join(trailers)
        body = f"{body}\n\n{trailer_block}" if body else trailer_block
    return body


# ---------------------------------------------------------------------------
# Step 1: rvy-0.9.9-rebased-on-common-base (109 commits on split-merged-baseline)
# ---------------------------------------------------------------------------
def build_aligned_branch(
    branch: str = "rvy-0.9.9-rebased-on-common-base",
    base_ref: str = "split-merged-baseline",
    worktree: Path | None = None,
) -> None:
    if worktree is None:
        worktree = MERGED_REPO / ".worktrees" / "build-check"
    prepare_worktree(worktree, base_ref)
    entries = [e for e in COMMITS if not e.only_on_rebase]

    for e in entries:
        if e.patch_path:
            am_3way(worktree, (SCRIPT_DIR / e.patch_path).read_text())
            continue

        src_repo = SPLIT_CHERI_REPO if e.origin_repo == "cheri" else SPLIT_SAIL_REPO
        repo_label = (
            "rvy-sail-cheri-riscv"
            if e.origin_repo == "cheri"
            else "rvy-sail-cheri-riscv/sail-riscv"
        )
        full_sha = git_stdout(src_repo, "rev-parse", f"{e.origin_sha}^{{commit}}")
        header = git_stdout(
            src_repo,
            "log",
            "-1",
            "--format=From %H Mon Sep 17 00:00:00 2001%nFrom: %an <%ae>%nDate: %aD",
            full_sha,
        )
        orig_msg = git_stdout(src_repo, "log", "-1", "--format=%B", full_sha).strip()
        trailers = [f"(cherry picked from {repo_label} commit {full_sha})"]

        if e.origin_repo == "cheri":
            diff_text = git_stdout(
                SPLIT_CHERI_REPO,
                "diff",
                "--full-index",
                f"{full_sha}^",
                full_sha,
                "--",
                "src/",
                "Makefile",
                strip=False,
            )
            diff_text = diff_text.replace("a/src/", "a/model/cheri/").replace(
                "b/src/", "b/model/cheri/"
            )
        else:
            diff_text = git_stdout(
                SPLIT_SAIL_REPO, "diff", "--full-index", f"{full_sha}^", full_sha, strip=False
            )

        squashed_msgs: list[str] = []
        for s_sha in e.sail_shas:
            full_s = git_stdout(SPLIT_SAIL_REPO, "rev-parse", f"{s_sha}^{{commit}}")
            s_subj = git_stdout(SPLIT_SAIL_REPO, "log", "-1", "--format=%s", full_s)
            squashed_msgs.append(git_stdout(SPLIT_SAIL_REPO, "log", "-1", "--format=%B", full_s))
            trailers.append(
                f"(squashed with rvy-sail-cheri-riscv/sail-riscv commit {full_s}: {s_subj})"
            )
            diff_text += git_stdout(
                SPLIT_SAIL_REPO, "diff", "--full-index", f"{full_s}^", full_s, strip=False
            )

        full_msg = combine_commit_messages([orig_msg, *squashed_msgs], trailers=trailers)
        msg_subj, _, msg_body = full_msg.partition("\n")
        msg_body = msg_body.lstrip("\n")
        am_3way(worktree, f"{header}\nSubject: [PATCH] {msg_subj}\n\n{msg_body}\n---\n{diff_text}")

        for adj_file in sorted((SCRIPT_DIR / "adjustments").glob(f"{e.entry_id}*.diff")):
            rel_adj = adj_file.relative_to(SCRIPT_DIR)
            run_git(worktree, "apply", "--index", adj_file)
            msg = git_stdout(worktree, "log", "-1", "--format=%B")
            run_git(
                worktree,
                "commit",
                "-q",
                "--amend",
                "--allow-empty",
                "-m",
                f"{msg}\nMerged-repo-adjustment-applied: {rel_adj}",
            )

    update_branch(branch, git_stdout(worktree, "rev-parse", "HEAD"))
    print(f"Built {branch} ({len(entries)} commits on {base_ref})")


# ---------------------------------------------------------------------------
# Step 2: rvy-0.9.9-rebased-on-head (78 commits on origin/codasip)
# ---------------------------------------------------------------------------
def build_rebased_branch(
    branch: str = "rvy-0.9.9-rebased-on-head",
    base_ref: str = "origin/codasip",
    aligned_branch: str = "rvy-0.9.9-rebased-on-common-base",
    worktree: Path | None = None,
) -> None:
    if worktree is None:
        worktree = MERGED_REPO / ".worktrees" / "build-check"
    prepare_worktree(worktree, base_ref)

    aligned_entries = [e for e in COMMITS if not e.only_on_rebase]
    aligned_commits = get_commits(MERGED_REPO, f"split-merged-baseline..{aligned_branch}")
    aligned_by_id = {e.entry_id: c for e, c in zip(aligned_entries, aligned_commits)}
    rebase_diff_dir = SCRIPT_DIR / "rebased-patches" / "rebase"

    rebased_entries = [e for e in COMMITS if not e.drop_on_rebase]
    for i, e in enumerate(rebased_entries):
        if e.fold_on_rebase:
            continue
        if e.only_on_rebase:
            patch_text = (
                (SCRIPT_DIR / e.patch_path)
                .read_text()
                .replace("a/src/", "a/model/cheri/")
                .replace("b/src/", "b/model/cheri/")
                .replace("extensionEnabled(", "currentlyEnabled(")
                .replace("execute(ext_decode(", "execute_test(ext_decode(")
                .replace("maybe_aq(aq) ^ maybe_rl(rl)", "maybe_aqrl(aq, rl)")
            )
            am_3way(worktree, patch_text)
            continue

        c = aligned_by_id[e.entry_id]
        cherry_pick_rerere(worktree, c.sha, drop_makefile=True)
        msgs, trailers = split_into_constituent_messages(c.message)
        if i + 1 < len(rebased_entries) and rebased_entries[i + 1].fold_on_rebase:
            rv32_c = aligned_by_id[rebased_entries[i + 1].entry_id]
            cherry_pick_rerere(worktree, rv32_c.sha, drop_makefile=True)
        msg = combine_commit_messages(msgs, trailers=trailers)
        run_git(worktree, "checkout", "HEAD", "--", "Makefile")
        for diff_file in sorted(rebase_diff_dir.glob(f"{e.entry_id}*.diff")):
            run_git(worktree, "apply", "--index", "--whitespace=nowarn", diff_file)
        run_git(
            worktree,
            "commit",
            "-q",
            "--author",
            c.author,
            "--date",
            c.date,
            "-m",
            msg,
        )

    total = git_stdout(worktree, "rev-list", "--count", f"{base_ref}..HEAD")
    update_branch(branch, git_stdout(worktree, "rev-parse", "HEAD"))
    print(f"Built {branch} ({total} commits on {base_ref})")


# ---------------------------------------------------------------------------
# Step 3: rvy-0.9.9-cleaned-history (42 reviewable commits on origin/codasip)
# ---------------------------------------------------------------------------
def build_cleaned_branch(
    branch: str = "rvy-0.9.9-cleaned-history",
    base_ref: str = "origin/codasip",
    rebased_branch: str = "rvy-0.9.9-rebased-on-head",
    worktree: Path | None = None,
) -> None:
    if worktree is None:
        worktree = MERGED_REPO / ".worktrees" / "build-check"
    prepare_worktree(worktree, base_ref)

    rebased_entries = [e for e in COMMITS if not e.drop_on_rebase and not e.fold_on_rebase]
    rebased_commits = get_commits(MERGED_REPO, f"{base_ref}..{rebased_branch}")
    rebased_pairs = list(zip(rebased_entries, rebased_commits))
    cleaned_diff_dir = SCRIPT_DIR / "rebased-patches" / "cleaned"

    for e, c in rebased_pairs:
        if e.drop_on_clean or e.squash_into:
            continue
        group = [
            (ge, gc)
            for ge, gc in rebased_pairs
            if ge.entry_id == e.entry_id or ge.squash_into == e.entry_id
        ]
        for _, gc in group:
            cherry_pick_rerere(worktree, gc.sha, drop_makefile=True)
        for diff_file in sorted(cleaned_diff_dir.glob(f"{e.entry_id}*.diff")):
            run_git(worktree, "apply", "--index", "--whitespace=nowarn", diff_file)

        msg_commits = (
            [gc for _, gc in group]
            if e.clean_title
            else [c] + [gc for ge, gc in group if ge.entry_id != e.entry_id]
        )
        all_msgs: list[str] = []
        all_trailers: list[str] = []
        for gc in msg_commits:
            gc_msgs, gc_trailers = split_into_constituent_messages(gc.message)
            all_msgs.extend(gc_msgs)
            all_trailers.extend(gc_trailers)
        run_git(
            worktree,
            "commit",
            "-q",
            "--author",
            c.author,
            "--date",
            c.date,
            "-m",
            combine_commit_messages(
                all_msgs, clean_title=e.clean_title, ref_trailers=all_trailers
            ),
        )

    if git_stdout(worktree, "diff", rebased_branch, "HEAD"):
        raise RuntimeError(f"Tree mismatch between {rebased_branch} and {branch}")

    total = git_stdout(worktree, "rev-list", "--count", f"{base_ref}..HEAD")
    update_branch(branch, git_stdout(worktree, "rev-parse", "HEAD"))
    print(f"Built {branch} ({total} commits on {base_ref}, tree identical to {rebased_branch})")


# ---------------------------------------------------------------------------
# Step 4: rvy-0.9.9-squashed-updated-messages (42 commits with concise messages)
# ---------------------------------------------------------------------------
def build_squashed_updated_messages_branch(
    branch: str = "rvy-0.9.9-squashed-updated-messages",
    base_ref: str = "origin/codasip",
    rebased_branch: str = "rvy-0.9.9-rebased-on-head",
    cleaned_branch: str = "rvy-0.9.9-cleaned-history",
    worktree: Path | None = None,
) -> None:
    if worktree is None:
        worktree = MERGED_REPO / ".worktrees" / "build-check"
    prepare_worktree(worktree, base_ref)

    rebased_entries = [e for e in COMMITS if not e.drop_on_rebase and not e.fold_on_rebase]
    rebased_commits = get_commits(MERGED_REPO, f"{base_ref}..{rebased_branch}")
    rebased_pairs = list(zip(rebased_entries, rebased_commits))
    cleaned_entries = [
        e for e, _ in rebased_pairs if not e.drop_on_clean and not e.squash_into
    ]
    cleaned_commits = get_commits(MERGED_REPO, f"{base_ref}..{cleaned_branch}")

    for e, cleaned_c in zip(cleaned_entries, cleaned_commits):
        group = [
            (ge, gc)
            for ge, gc in rebased_pairs
            if ge.entry_id == e.entry_id or ge.squash_into == e.entry_id
        ]
        msg_commits = (
            [gc for _, gc in group]
            if e.clean_title
            else [gc for ge, gc in group if ge.entry_id == e.entry_id]
            + [gc for ge, gc in group if ge.entry_id != e.entry_id]
        )
        all_trailers: list[str] = []
        for gc in msg_commits:
            _, gc_trailers = split_into_constituent_messages(gc.message)
            all_trailers.extend(gc_trailers)
        refs = extract_capltd_refs(all_trailers)

        if e.entry_id in SUMMARY_MESSAGES:
            msg = SUMMARY_MESSAGES[e.entry_id].strip()
            if len(refs) > 1:
                msg = f"{msg}\n\n{format_combination_line(refs)}"
        else:
            msg = cleaned_c.message.strip()

        run_git(worktree, "cherry-pick", "-n", cleaned_c.sha)
        run_git(
            worktree,
            "commit",
            "-q",
            "--author",
            cleaned_c.author,
            "--date",
            cleaned_c.date,
            "-m",
            msg,
        )

    if git_stdout(worktree, "diff", cleaned_branch, "HEAD"):
        raise RuntimeError(f"Tree mismatch between {cleaned_branch} and {branch}")

    total = git_stdout(worktree, "rev-list", "--count", f"{base_ref}..HEAD")
    update_branch(branch, git_stdout(worktree, "rev-parse", "HEAD"))
    print(f"Built {branch} ({total} commits on {base_ref}, tree identical to {cleaned_branch})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "step",
        nargs="?",
        default="all",
        choices=("all", "aligned", "rebased", "cleaned", "squashed"),
    )
    parser.add_argument("--build-check", action="store_true", help="Build and test every commit")
    args = parser.parse_args()

    if args.step in ("all", "aligned"):
        build_aligned_branch()
    if args.step in ("all", "rebased"):
        build_rebased_branch()
    if args.step in ("all", "cleaned"):
        build_cleaned_branch()
    if args.step in ("all", "squashed"):
        build_squashed_updated_messages_branch()

    if args.step == "all":
        from verify_commit_identity import verify_commit_identity

        verify_commit_identity()

    if args.build_check:
        from check_each_commit_builds import check_each_commit_builds

        if not check_each_commit_builds(
            branch="rvy-0.9.9-cleaned-history",
            base_ref="origin/codasip",
            run_self_test=True,
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
