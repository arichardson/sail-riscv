#!/usr/bin/env python3
"""Run QuickCheckVEngine (TestRIG) comparing the split-repo and merged-repo Sail RVFI-DII binaries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Sequence

from reproduce_all import MERGED_REPO, SCRIPT_DIR, SPLIT_CHERI_REPO

RE_BACKSPACE = re.compile(r"[^\x08]*\x08")


def strip_progress_backspaces(text: str) -> str:
    """Strip QuickCheck progress backspaces and carriage returns for readable logs."""
    while "\x08" in text:
        new_text = RE_BACKSPACE.sub("", text)
        if new_text == text:
            break
        text = new_text
    return text.replace("\r", "")


def run_testrig_sail_vs_sail(
    mode: str = "baseline",
    extra_args: Sequence[str] = (),
) -> int:
    qcvengine = Path(
        os.environ.get(
            "QCVENGINE",
            str(
                MERGED_REPO.parent
                / "rvy-quickcheckvengine/dist-newstyle/build/x86_64-linux/ghc-9.10.3/QCVEngine-0.1.0.0/x/QCVEngine/build/QCVEngine/QCVEngine"
            ),
        )
    )
    split_sail_rvfi = Path(
        os.environ.get(
            "SPLIT_SAIL_RVFI",
            str(SPLIT_CHERI_REPO / "c_emulator/cheri_riscv_rvfi_RV64"),
        )
    )
    base_sail_rvfi = Path(
        os.environ.get(
            "BASE_SAIL_RVFI",
            str(MERGED_REPO / ".worktrees/testrig-noext/cmake-build-debug/c_emulator/riscv_sim_rv64d_rvfi"),
        )
    )
    new_sail_rvfi = Path(
        os.environ.get(
            "NEW_SAIL_RVFI",
            str(MERGED_REPO / ".worktrees/build-check/cmake-build-debug/c_emulator/sail_riscv_sim"),
        )
    )
    rebased_config = Path(
        os.environ.get(
            "REBASED_CONFIG",
            str(SCRIPT_DIR / "testrig/rv64d-testrig.json"),
        )
    )

    num_runs = os.environ.get("NUM_RUNS", "20")
    arch_string = os.environ.get("ARCH_STRING", "rv64imafdc_s_xcheri_zicsr_zifencei")
    port_a = os.environ.get("PORT_A", "55001")
    port_b = os.environ.get("PORT_B", "55002")
    csr_exclude_regex = os.environ.get("CSR_EXCLUDE_REGEX", "reserved")
    timeout_us = os.environ.get("QCV_TIMEOUT_US", "10000000")

    if mode not in ("baseline", "rebased"):
        raise ValueError(f"Unknown mode: {mode} (expected 'baseline' or 'rebased')")

    log_dir = SCRIPT_DIR / "output" / f"testrig-{mode}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_a_path = log_dir / "impl-a.log"
    log_b_path = log_dir / "impl-b.log"
    qcv_log_path = log_dir / "qcvengine.log"

    cmd_a = [
        str(split_sail_rvfi),
        "--disable-writable-misa",
        "--mtval-has-illegal-inst-bits",
        "--rvfi-dii",
        port_a,
        *(["--enable-misaligned"] if mode == "baseline" else []),
        "--no-trace",
        "--disable-vector-ext",
    ]
    if mode == "baseline":
        cmd_b = [
            str(base_sail_rvfi),
            "--disable-writable-misa",
            "--mtval-has-illegal-inst-bits",
            "--rvfi-dii",
            port_b,
            "--enable-misaligned",
            "--no-trace",
            "--disable-vector-ext",
        ]
    else:
        cmd_b = [
            str(new_sail_rvfi),
            "--config",
            str(rebased_config),
            "--rvfi-dii",
            port_b,
            "--no-trace",
        ]

    proc_a: subprocess.Popen[bytes] | None = None
    proc_b: subprocess.Popen[bytes] | None = None
    try:
        print(f"Starting Impl A (split-repo Sail RVFI) on port {port_a}...")
        with log_a_path.open("wb") as fa:
            proc_a = subprocess.Popen(cmd_a, stdout=fa, stderr=subprocess.STDOUT)

        print(f"Starting Impl B (merged-repo {mode} Sail RVFI) on port {port_b}...")
        with log_b_path.open("wb") as fb:
            proc_b = subprocess.Popen(cmd_b, stdout=fb, stderr=subprocess.STDOUT)

        time.sleep(1.0)
        if proc_a.poll() is not None:
            sys.stderr.write(f"Impl A failed to start:\n{log_a_path.read_text()}\n")
            return 1
        if proc_b.poll() is not None:
            sys.stderr.write(f"Impl B failed to start:\n{log_b_path.read_text()}\n")
            return 1

        print(f"Running QCVEngine ({num_runs} tests per group, arch={arch_string})...")
        qcv_cmd = [
            str(qcvengine),
            "-a",
            port_a,
            "-b",
            port_b,
            "-r",
            arch_string,
            "-n",
            num_runs,
            "-T",
            timeout_us,
            f"--csr-exclude-regex={csr_exclude_regex}",
            "--no-save",
            "--verbose=1",
            *extra_args,
        ]
        with qcv_log_path.open("w") as qlog:
            qproc = subprocess.Popen(
                qcv_cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert qproc.stdout is not None
            for raw_line in qproc.stdout:
                cleaned = strip_progress_backspaces(raw_line)
                sys.stdout.write(cleaned)
                sys.stdout.flush()
                qlog.write(cleaned)
                qlog.flush()
            qcv_status = qproc.wait()

        if proc_a.poll() is not None:
            sys.stderr.write(f"WARNING: Impl A exited during the run; see {log_a_path}\n")
        if proc_b.poll() is not None:
            sys.stderr.write(f"WARNING: Impl B exited during the run; see {log_b_path}\n")
        print(f"QCVEngine exit status: {qcv_status} (log: {qcv_log_path})")
        return qcv_status
    finally:
        for p in (proc_a, proc_b):
            if p is not None and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    p.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="baseline", choices=("baseline", "rebased"))
    args, extra = parser.parse_known_args()
    raise SystemExit(run_testrig_sail_vs_sail(args.mode, extra))


if __name__ == "__main__":
    main()
