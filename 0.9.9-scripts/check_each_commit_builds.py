#!/usr/bin/env python3
"""Build simulator targets and run checks at every commit in BASE..BRANCH."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
from typing import Sequence

from reproduce_all import MERGED_REPO, SAIL_BIN, SCRIPT_DIR, get_commits, run_git


EXPECTED_FAILURES: dict[str, set[str]] = {
    # Legacy Makefile RVFI source list broken until 82d371e "Makefile fixes"
    "6d8cafdb": {"make-RV64-rvfi", "make-RV32-rvfi"},
    "dc8ec197": {"make-RV64-rvfi", "make-RV32-rvfi", "make-RV32"},
    "ea15966c": {"make-RV64-rvfi", "make-RV32-rvfi", "make-RV32"},
    "cb6b63ae": {"make-RV64-rvfi", "make-RV32-rvfi", "make-RV32"},
    "9ef5189d": {"make-RV64-rvfi", "make-RV32-rvfi", "make-RV32"},
    "Fix RV32 build of the RVFI memory range checks": {"make-RV64-rvfi", "make-RV32-rvfi"},
    "8dc1750c": {"make-RV64-rvfi", "make-RV32-rvfi"},
    "9479bf45": {"make-RV64-rvfi", "make-RV32-rvfi"},
    "d11a7bff": {"make-RV64-rvfi", "make-RV32-rvfi"},
    # RV32-only failures fixed by the immediately following rv32-fixes/*.patch commit
    "8b49265": {"make-RV32", "make-RV32-rvfi"},
    "ab30556": {"make-RV32", "make-RV32-rvfi"},
    "20c04ad": {"make-RV32", "make-RV32-rvfi"},
}


def check_each_commit_builds(
    branch: str = "rvy-0.9.9-cleaned-history",
    base_ref: str = "origin/codasip",
    keep_going: bool = False,
    run_self_test: bool = True,
    run_make: bool = False,
    make_arches: Sequence[str] = ("RV64",),
) -> bool:
    worktree = MERGED_REPO / ".worktrees" / "build-check"
    build_dir = worktree / "cmake-build-debug"
    out_dir = SCRIPT_DIR / "output" / branch / "build-check"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.txt"

    env = {**os.environ, "PATH": f"{SAIL_BIN.parent}:{os.environ.get('PATH', '')}"}
    if not worktree.exists():
        run_git(MERGED_REPO, "worktree", "add", "--detach", worktree, base_ref)
    if not (build_dir / "build.ninja").is_file():
        subprocess.run(
            [
                "cmake",
                "-S",
                str(worktree),
                "-B",
                str(build_dir),
                "-G",
                "Ninja",
                "-DCMAKE_BUILD_TYPE=Debug",
                "-DDOWNLOAD_GMP=OFF",
                f"-DSAIL_BIN={SAIL_BIN}",
            ],
            env=env,
            check=True,
        )

    commits = get_commits(MERGED_REPO, f"{base_ref}..{branch}")
    summary_lines: list[str] = []
    failures = 0
    xfails = 0

    for idx, c in enumerate(commits, 1):
        short_sha = c.sha[:10]
        log_path = out_dir / f"{idx:04d}-{short_sha}.log"
        run_git(worktree, "checkout", "-q", "-f", "--detach", c.sha)

        failed: list[str] = []
        with log_path.open("w") as log_file:
            def run_cmd(cmd: Sequence[str]) -> int:
                return subprocess.run(
                    cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT, check=False
                ).returncode

            if run_cmd(["cmake", "--build", str(build_dir)]) != 0:
                failed.append("cmake")

            sim = build_dir / "c_emulator" / "sail_riscv_sim"
            if run_self_test and not failed and sim.is_file():
                if run_cmd([str(sim), "--self-test"]) != 0:
                    failed.append("self-test-rv64")
                if (
                    run_cmd([str(sim), "--config", str(worktree / "config/rv32d.json"), "--self-test"])
                    != 0
                ):
                    failed.append("self-test-rv32")

            if run_make:
                for arch in make_arches:
                    if run_cmd(["make", "-C", str(worktree), f"ARCH={arch}", "check"]) != 0:
                        failed.append(f"make-{arch}")

        all_xfail = all(
            any(key in c.message and chk in chks for key, chks in EXPECTED_FAILURES.items())
            for chk in failed
        )
        if not failed:
            status = "OK"
        elif all_xfail:
            status = "XFAIL"
            xfails += 1
        else:
            status = "FAIL"
            failures += 1

        suffix = f" [failed: {' '.join(failed)}]" if failed else ""
        line = f"{idx:04d} {status:<5} {short_sha} {c.subject}{suffix}"
        print(line, flush=True)
        summary_lines.append(line)

        if status == "FAIL" and not keep_going:
            break

    summary_path.write_text("\n".join(summary_lines) + "\n")
    print(f"{failures} unexpected failure(s), {xfails} expected (XFAIL); summary in {summary_path}")
    return failures == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="rvy-0.9.9-cleaned-history")
    parser.add_argument("--base", default="origin/codasip")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--no-self-test", action="store_true")
    parser.add_argument("--make", action="store_true")
    parser.add_argument("--make-arches", default="RV64")
    args = parser.parse_args()

    ok = check_each_commit_builds(
        branch=args.branch,
        base_ref=args.base,
        keep_going=args.keep_going,
        run_self_test=not args.no_self_test,
        run_make=args.make,
        make_arches=args.make_arches.split(),
    )
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
