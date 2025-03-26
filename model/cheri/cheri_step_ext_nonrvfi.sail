/*=======================================================================================*/
/*  This Sail RISC-V architecture model, comprising all files and                        */
/*  directories except where otherwise noted is subject the BSD                          */
/*  two-clause license in the LICENSE file.                                              */
/*                                                                                       */
/*  SPDX-License-Identifier: BSD-2-Clause                                                */
/*=======================================================================================*/

// The split repository (rvy-sail-cheri-riscv) could only build the RVFI simulator between
// "Fixes for running with TestRIG" and "Re-enable self tests". These definitions keep the
// non-RVFI build of the merged repository working in the meantime; "Re-enable self tests"
// removes the step hooks and this file.

function ext_fetch_hook(f : FetchResult) -> FetchResult = f

function ext_pre_step_hook()  -> unit = ()
function ext_post_step_hook() -> unit = ()

function ext_reset() -> unit = ()
