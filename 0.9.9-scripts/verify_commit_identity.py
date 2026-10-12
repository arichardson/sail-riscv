#!/usr/bin/env python3
"""Compare every commit on a replayed merged-repo branch against the original split-repo commits."""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path
import re

from reproduce_all import (
    MERGED_REPO,
    SCRIPT_DIR,
    SPLIT_CHERI_REPO,
    SPLIT_SAIL_REPO,
    get_commits,
    git_stdout,
)

RE_CHERRY_PICKED = re.compile(r"\(cherry picked from ([^\s]+) commit ([0-9a-f]{40})\)")
RE_SQUASHED_WITH = re.compile(r"^\(squashed with [^\s]+ commit ([0-9a-f]{40}):.*\)$", re.MULTILINE)
RE_ADJUSTED = re.compile(r"^Merged-repo-adjustment-applied: (.*)$", re.MULTILINE)


def normalize_patch(patch_text: str) -> str:
    """Normalize `src/` -> `model/cheri/` paths, drop `index` lines, and strip hunk line numbers."""
    out: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("index "):
            continue
        line = line.replace("a/src/", "a/model/cheri/").replace("b/src/", "b/model/cheri/")
        if line.startswith("@@ "):
            line = "@@ @@"
        out.append(line)
    return "\n".join(out)


def verify_commit_identity(
    base_ref: str = "split-merged-baseline",
    target_ref: str = "rvy-0.9.9-rebased-on-common-base",
    out_dir: Path | None = None,
) -> Path:
    if out_dir is None:
        out_dir = SCRIPT_DIR / "output" / target_ref / "commit-identity"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_diff in out_dir.glob("diff-*.patch"):
        old_diff.unlink()
    report_file = out_dir / "report.md"

    commits = get_commits(MERGED_REPO, f"{base_ref}..{target_ref}")
    identical_lines: list[str] = []
    diff_sections: list[str] = []
    rv32_lines: list[str] = []

    for idx, c in enumerate(commits, 1):
        short_c = c.sha[:8]
        m = RE_CHERRY_PICKED.search(c.message)
        if not m:
            rv32_lines.append(f"- `{idx:04d}` `{short_c}`: {c.subject}")
            continue

        origin_repo, orig_sha = m.group(1), m.group(2)
        squashed_sail = RE_SQUASHED_WITH.findall(c.message)
        adj_notes = ", ".join(RE_ADJUSTED.findall(c.message))

        merged_patch = normalize_patch(
            git_stdout(MERGED_REPO, "diff", "-U0", f"{c.sha}^", c.sha, strip=False)
        )
        if origin_repo == "rvy-sail-cheri-riscv":
            parts = [
                git_stdout(
                    SPLIT_CHERI_REPO,
                    "diff",
                    "-U0",
                    f"{orig_sha}^",
                    orig_sha,
                    "--",
                    "src/",
                    "Makefile",
                    strip=False,
                )
            ]
            for sc in squashed_sail:
                parts.append(
                    git_stdout(SPLIT_SAIL_REPO, "diff", "-U0", f"{sc}^", sc, strip=False)
                )
            split_patch = normalize_patch("".join(p for p in parts if p))
            origin_label = f"cheri {orig_sha[:8]}"
        else:
            split_patch = normalize_patch(
                git_stdout(SPLIT_SAIL_REPO, "diff", "-U0", f"{orig_sha}^", orig_sha, strip=False)
            )
            origin_label = f"sail {orig_sha[:8]}"

        for sc in squashed_sail:
            origin_label += f" + sail {sc[:8]}"

        if merged_patch == split_patch:
            identical_lines.append(f"- `{idx:04d}` `{short_c}` ({origin_label}): {c.subject}")
        else:
            patch_diff = "".join(
                difflib.unified_diff(
                    split_patch.splitlines(keepends=True),
                    merged_patch.splitlines(keepends=True),
                    fromfile=f"split/{origin_label} ({c.subject})",
                    tofile=f"merged/{short_c} ({c.subject})",
                )
            )
            (out_dir / f"diff-{idx:04d}-{short_c}.patch").write_text(patch_diff)
            sec = [f"### `{idx:04d}` `{short_c}` ({origin_label}): {c.subject}", ""]
            if adj_notes:
                sec.extend([f"- **Adjustment:** `{adj_notes}`", ""])
            sec.extend(["```diff", patch_diff.rstrip("\n"), "```", ""])
            diff_sections.append("\n".join(sec))

    report_lines = [
        f"# Commit-by-Commit Byte-Identity Report (`{base_ref}..{target_ref}`)",
        "",
        f"- **Byte-for-byte identical to split repo** (after `src/` -> `model/cheri/`): **{len(identical_lines)}**",
        f"- **Modified for merged repo** (conflict resolution or build/API adjustment): **{len(diff_sections)}**",
        f"- **Merged-repo-only RV32 follow-up commits:** **{len(rv32_lines)}**",
        f"- **Total commits:** **{len(commits)}**",
        "",
        f"## RV32 Follow-Up Commits ({len(rv32_lines)})",
        "",
        *rv32_lines,
        "",
        f"## Modified Commits ({len(diff_sections)})",
        "",
        *diff_sections,
        f"## Identical Commits ({len(identical_lines)})",
        "",
        *identical_lines,
        "",
    ]
    report_file.write_text("\n".join(report_lines))
    print(
        f"Summary: {len(identical_lines)} identical, {len(diff_sections)} modified, "
        f"{len(rv32_lines)} RV32 follow-ups (total {len(commits)})."
    )
    return report_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_ref", nargs="?", default="split-merged-baseline")
    parser.add_argument("target_ref", nargs="?", default="rvy-0.9.9-rebased-on-common-base")
    parser.add_argument("out_dir", nargs="?", type=Path, default=None)
    args = parser.parse_args()
    verify_commit_identity(args.base_ref, args.target_ref, args.out_dir)


if __name__ == "__main__":
    main()
