# Commit-by-Commit Byte-Identity Report (`split-merged-baseline..rvy-0.9.9-rebased-on-common-base`)

- **Byte-for-byte identical to split repo** (after `src/` -> `model/cheri/`): **86**
- **Modified for merged repo** (conflict resolution or build/API adjustment): **18**
- **Merged-repo-only RV32 follow-up commits:** **5**
- **Total commits:** **109**

## RV32 Follow-Up Commits (5)

- `0006` `5f22ecac`: Fix RV32 build of the RVFI memory range checks and reporting
- `0035` `60474a97`: Fix RV32 build of the invalid address self test
- `0045` `3177b64f`: Fix RV32 build with the new CHERI exception codes
- `0073` `6a575b76`: Fix the YBNDSWI max length self test on RV32
- `0085` `e2f22079`: Fix RV32 build after the Mode to PointerMode renaming

## Modified Commits (18)

### `0001` `8c80053e` (sail 6d8cafdb): Fixes to work with TestRIG

```diff
--- split/sail 6d8cafdb (Fixes to work with TestRIG)
+++ merged/8c80053e (Fixes to work with TestRIG)
@@ -2,10 +2,10 @@
 --- a/model/riscv_fetch_rvfi.sail
 +++ b/model/riscv_fetch_rvfi.sail
 @@ @@
--    Ext_FetchAddr_Error(e)   => F_Ext_Error(e),
-+    Ext_FetchAddr_Error(e)     => F_Error(e, PC),
-+    Ext_FetchAddr_Ext_Error(e) => F_Ext_Error(e),
+-    Ext_FetchAddr_OK(use_pc)   => {
++    Ext_FetchAddr_OK(use_pc) => {
 @@ @@
--              Ext_FetchAddr_Error(e)      => F_Ext_Error(e),
+-              Ext_FetchAddr_Error(e)      => F_Error(e, PC_hi),
+-              Ext_FetchAddr_Ext_Error(e)  => F_Ext_Error(e),
 +              Ext_FetchAddr_Error(e)     => F_Error(e, PC_hi),
 +              Ext_FetchAddr_Ext_Error(e) => F_Ext_Error(e),
```

### `0002` `c8777bc5` (sail dc8ec197): Restore RVFI DII memory region restrictions

- **Adjustment:** `adjustments/dc8ec197-fold-b6a6dda8-memory-types.diff`

```diff
--- split/sail dc8ec197 (Restore RVFI DII memory region restrictions)
+++ merged/c8777bc5 (Restore RVFI DII memory region restrictions)
@@ -2,13 +2,13 @@
 --- a/model/riscv_mem.sail
 +++ b/model/riscv_mem.sail
 @@ @@
-+  let result : option((bits(8 * 'n), mem_meta)) = if platform_get_rvfi_dii() & out_of_rvfi_dii_range(paddr, width) then None() else result;
++  let result : option((bits(8 * 'n), mem_meta)) = if platform_get_rvfi_dii() & out_of_rvfi_dii_range(physaddr_bits(paddr), width) then None() else result;
 @@ @@
 -  let result = write_ram(wk, paddr, width, data, meta);
 -  if   get_config_print_mem()
 -  then print_mem("mem[" ^ BitStr(physaddr_bits(paddr)) ^ "] <- " ^ BitStr(data));
 -  Ok(result)
-+  if platform_get_rvfi_dii() & out_of_rvfi_dii_range(paddr, width)
++  if platform_get_rvfi_dii() & out_of_rvfi_dii_range(physaddr_bits(paddr), width)
 +  then Err(E_SAMO_Access_Fault())
 +  else {
 +    let result = write_ram(wk, paddr, width, data, meta);
@@ -19,18 +19,6 @@
 diff --git a/model/riscv_platform.sail b/model/riscv_platform.sail
 --- a/model/riscv_platform.sail
 +++ b/model/riscv_platform.sail
-@@ @@
-+$ifndef RVFI_DII
-@@ @@
-+$else
-+function within_mmio_readable forall 'n, 0 < 'n <= max_mem_access . (addr : physaddr, width : int('n)) -> bool = false
-+$endif
-@@ @@
-+$ifndef RVFI_DII
-@@ @@
-+$else
-+function within_mmio_writable forall 'n, 0 < 'n <= max_mem_access . (addr : physaddr, width : int('n)) -> bool = false
-+$endif
 @@ @@
 +
 +/* Function to dynamically check if RVFI_DII is enabled */
```

### `0003` `445cbd1d` (sail ea15966c): Restore RVFI read and write reporting

- **Adjustment:** `adjustments/ea15966c-fold-b6a6dda8-memory-types.diff`

```diff
--- split/sail ea15966c (Restore RVFI read and write reporting)
+++ merged/445cbd1d (Restore RVFI read and write reporting)
@@ -9,11 +9,11 @@
 +  rvfi_mem_data_present = true;
 +  match result {
 +    /* TODO: report tag bit for capability writes and extend mask by one bit. */
-+    MemValue(v, _) => if width <= 16
-+                       then { rvfi_mem_data[rvfi_mem_rdata] = sail_zero_extend(v, 256);
-+                              rvfi_mem_data[rvfi_mem_rmask] = rvfi_encode_width_mask(width) }
-+                       else { internal_error(__FILE__, __LINE__, "Expected at most 16 bytes here!") },
-+    MemException(_) => ()
++    Ok(v, _) => if width <= 16
++               then { rvfi_mem_data[rvfi_mem_rdata] = sail_zero_extend(v, 256);
++                      rvfi_mem_data[rvfi_mem_rmask] = rvfi_encode_width_mask(width) }
++               else { internal_error(__FILE__, __LINE__, "Expected at most 16 bytes here!") },
++    Err(_) => ()
 +  };
 +}
 +$else
@@ -58,7 +58,7 @@
 -  }
 +      },
 +    };
-+  rvfi_read(paddr, width, result);
++  rvfi_read(physaddr_bits(paddr), width, result);
 +  result
 +}
 @@ @@
@@ -69,14 +69,14 @@
 +  rvfi_mem_data_present = true;
 +  match result {
 +    /* Log only the memory address (without the value) if the write fails. */
-+    MemValue(_) => if width <= 16 then {
++    Ok(_) => if width <= 16 then {
 +        /* TODO: report tag bit for capability writes and extend mask by one bit. */
 +        rvfi_mem_data[rvfi_mem_wdata] = sail_zero_extend(value,256);
 +        rvfi_mem_data[rvfi_mem_wmask] = rvfi_encode_width_mask(width);
 +      } else {
 +        internal_error(__FILE__, __LINE__, "Expected at most 16 bytes here!");
 +      },
-+    MemException(_) => ()
++    Err(_) => ()
 +  }
 +}
 +$else
@@ -117,6 +117,6 @@
 -    }
 -  }
 +    };
-+  rvfi_write(paddr, width, data, meta, result);
++  rvfi_write(physaddr_bits(paddr), width, data, meta, result);
 +  result
 +}
```

### `0007` `d509d205` (cheri 8dc1750c): Fixes for running with TestRIG

- **Adjustment:** `adjustments/8dc1750-rvfi-build.diff`

```diff
--- split/cheri 8dc1750c (Fixes for running with TestRIG)
+++ merged/d509d205 (Fixes for running with TestRIG)
@@ -6,9 +6,20 @@
 +                 $(SAIL_RISCV_MODEL_DIR)/riscv_clic_prelude.sail \
 +                 $(SAIL_RISCV_MODEL_DIR)/riscv_convert_invalid_addr.sail \
 @@ @@
++                 $(SAIL_CHERI_MODEL_DIR)/cheri_step_ext_nonrvfi.sail \
+@@ @@
 +                 $(SAIL_CHERI_MODEL_DIR)/cheri_step_ext.sail \
 @@ @@
 +                 $(SAIL_CHERI_MODEL_DIR)/cheri_execute.sail \
+diff --git a/model/CMakeLists.txt b/model/CMakeLists.txt
+--- a/model/CMakeLists.txt
++++ b/model/CMakeLists.txt
+@@ @@
+-                set(riscv_step_ext "riscv_step_rvfi.sail")
++                set(riscv_step_ext "cheri/cheri_step_ext.sail" "riscv_step_rvfi.sail")
+@@ @@
+-                set(riscv_step_ext "cheri/cheri_step_ext.sail")
++                set(riscv_step_ext "cheri/cheri_step_ext.sail" "cheri/cheri_step_ext_nonrvfi.sail")
 diff --git a/model/cheri/cheri_step_ext.sail b/model/cheri/cheri_step_ext.sail
 --- a/model/cheri/cheri_step_ext.sail
 +++ b/model/cheri/cheri_step_ext.sail
@@ -22,4 +33,51 @@
 -function ext_pre_step_hook()  -> unit = ()
 -function ext_post_step_hook() -> unit = ()
 +//function ext_pre_step_hook()  -> unit = ()
-+//function ext_post_step_hook() -> unit = ()++//function ext_post_step_hook() -> unit = ()
+diff --git a/model/cheri/cheri_step_ext_nonrvfi.sail b/model/cheri/cheri_step_ext_nonrvfi.sail
+new file mode 100644
+--- /dev/null
++++ b/model/cheri/cheri_step_ext_nonrvfi.sail
+@@ @@
++/*=======================================================================================*/
++/*  This Sail RISC-V architecture model, comprising all files and                        */
++/*  directories except where otherwise noted is subject the BSD                          */
++/*  two-clause license in the LICENSE file.                                              */
++/*                                                                                       */
++/*  SPDX-License-Identifier: BSD-2-Clause                                                */
++/*=======================================================================================*/
++
++// The split repository (rvy-sail-cheri-riscv) could only build the RVFI simulator between
++// "Fixes for running with TestRIG" and "Re-enable self tests". These definitions keep the
++// non-RVFI build of the merged repository working in the meantime; "Re-enable self tests"
++// removes the step hooks and this file.
++
++function ext_fetch_hook(f : FetchResult) -> FetchResult = f
++
++function ext_pre_step_hook()  -> unit = ()
++function ext_post_step_hook() -> unit = ()
++
++function ext_reset() -> unit = ext_cheri_reset()
+diff --git a/model/riscv_step_rvfi.sail b/model/riscv_step_rvfi.sail
+--- a/model/riscv_step_rvfi.sail
++++ b/model/riscv_step_rvfi.sail
+@@ @@
+-// Print an instruction we are executing. For CHERI we print the mode too.
+-function ext_print_instr forall 'n, 'n in {16, 32} . (
+-  step_no : int, ast : ast, opcode : bits('n)
+-) -> unit = {
+-  if get_config_print_instr()
+-  then {
+-    let cheri_mode : string = match effective_cheri_mode() {
+-      CapPtrMode => "CapPtrMode",
+-      IntPtrMode  => "Integer",
+-    };
+-    print_instr(
+-      "[" ^ dec_str(step_no) ^ "] [" ^ to_str(cur_privilege()) ^ "," ^ cheri_mode ^ "]: " ^
+-      BitStr(PC) ^ " (" ^ BitStr(opcode) ^ ") " ^ to_str(ast)
+-    );
+-  };
+-}
+-
+@@ @@
+-function ext_reset_misa() -> unit = ()
```

### `0008` `855bd544` (sail 9479bf45): Fix resets

- **Adjustment:** `adjustments/9479bf45-nonrvfi-reset.diff`

```diff
--- split/sail 9479bf45 (Fix resets)
+++ merged/855bd544 (Fix resets)
@@ -1,12 +1,11 @@
+diff --git a/model/cheri/cheri_step_ext_nonrvfi.sail b/model/cheri/cheri_step_ext_nonrvfi.sail
+--- a/model/cheri/cheri_step_ext_nonrvfi.sail
++++ b/model/cheri/cheri_step_ext_nonrvfi.sail
+@@ @@
+-function ext_reset() -> unit = ext_cheri_reset()
++function ext_reset() -> unit = ()
 diff --git a/model/riscv_step.sail b/model/riscv_step.sail
 --- a/model/riscv_step.sail
 +++ b/model/riscv_step.sail
 @@ @@
-+  ext_cheri_reset();
-diff --git a/model/riscv_step_rvfi.sail b/model/riscv_step_rvfi.sail
---- a/model/riscv_step_rvfi.sail
-+++ b/model/riscv_step_rvfi.sail
-@@ @@
--function ext_reset() -> unit = ()
--function ext_reset_misa() -> unit = ()
-+function ext_reset() -> unit = ext_rvfi_reset()++  ext_cheri_reset();
```

### `0010` `47757fd1` (cheri 82d371e2): Makefile fixes

- **Adjustment:** `adjustments/82d371e-makefile-dedup-svinval.diff`

```diff
--- split/cheri 82d371e2 (Makefile fixes)
+++ merged/47757fd1 (Makefile fixes)
@@ -1,8 +1,6 @@
 diff --git a/Makefile b/Makefile
 --- a/Makefile
 +++ b/Makefile
-@@ @@
-+                    $(SAIL_RISCV_MODEL_DIR)/riscv_insts_svinval.sail \
 @@ @@
 +                 $(SAIL_RISCV_MODEL_DIR)/riscv_extensions.sail \
 @@ @@
```

### `0012` `5997c902` (cheri 26788339): Include zifencei in Makefile

- **Adjustment:** `adjustments/26788339-makefile-dedup-zifencei.diff`

```diff
--- split/cheri 26788339 (Include zifencei in Makefile)
+++ merged/5997c902 (Include zifencei in Makefile)
@@ -1,5 +0,0 @@
-diff --git a/Makefile b/Makefile
---- a/Makefile
-+++ b/Makefile
-@@ @@
-+                    $(SAIL_RISCV_MODEL_DIR)/riscv_insts_zifencei.sail \
```

### `0015` `d0f5491f` (sail 44c7a9b9): Fix out-of-range xcause length

```diff
--- split/sail 44c7a9b9 (Fix out-of-range xcause length)
+++ merged/d0f5491f (Fix out-of-range xcause length)
@@ -1,9 +1,3 @@
-diff --git a/c_emulator/riscv_platform.cpp b/c_emulator/riscv_platform.cpp
---- a/c_emulator/riscv_platform.cpp
-+++ b/c_emulator/riscv_platform.cpp
-@@ @@
--  return 0xFFFFFFFF;
-+  return 63;
 diff --git a/model/riscv_sys_regs.sail b/model/riscv_sys_regs.sail
 --- a/model/riscv_sys_regs.sail
 +++ b/model/riscv_sys_regs.sail
```

### `0019` `52d52450` (cheri 59586f8b): Add CHERI CSR extending file to Makefile

- **Adjustment:** `adjustments/59586f8-cmake-csr-ext.diff`

```diff
--- split/cheri 59586f8b (Add CHERI CSR extending file to Makefile)
+++ merged/52d52450 (Add CHERI CSR extending file to Makefile)
@@ -2,4 +2,14 @@
 --- a/Makefile
 +++ b/Makefile
 @@ @@
-+                 $(SAIL_CHERI_MODEL_DIR)/cheri_csr_ext.sail \++                 $(SAIL_CHERI_MODEL_DIR)/cheri_csr_ext.sail \
+diff --git a/model/CMakeLists.txt b/model/CMakeLists.txt
+--- a/model/CMakeLists.txt
++++ b/model/CMakeLists.txt
+@@ @@
+-                "riscv_csr_end.sail"
+@@ @@
++            if (variant STREQUAL "rvfi")
++                list(APPEND sail_seq_inst_srcs "cheri/cheri_csr_ext.sail")
++            endif()
++            list(APPEND sail_seq_inst_srcs "riscv_csr_end.sail")
```

### `0026` `c5ee4dbb` (cheri 629a4361): Flip polarity of leaf check in CHERI PTE invalid checks

```diff
--- split/cheri 629a4361 (Flip polarity of leaf check in CHERI PTE invalid checks)
+++ merged/c5ee4dbb (Flip polarity of leaf check in CHERI PTE invalid checks)
@@ -2,5 +2,5 @@
 --- a/model/cheri/cheri_vmem_pte_validity_ext.sail
 +++ b/model/cheri/cheri_vmem_pte_validity_ext.sail
 @@ @@
--    Some(pte_ext) => (pte_ext[CW] != 0b0 | pte_ext[CRG] != 0b0) & not(pte_is_ptr(pte_flags)),
-+    Some(pte_ext) => (pte_ext[CW] != 0b0 | pte_ext[CRG] != 0b0) & pte_is_ptr(pte_flags),+-    // The CRG/CW bits must be 0 for non-leaf nodes.
++    // The CRG/CW bits must be 0 unless this is a leaf node.
```

### `0027` `08560529` (cheri a0099ab4): PTE check fixes

```diff
--- split/cheri a0099ab4 (PTE check fixes)
+++ merged/08560529 (PTE check fixes)
@@ -1,18 +1,6 @@
-diff --git a/model/cheri/cheri_insts.sail b/model/cheri/cheri_insts.sail
---- a/model/cheri/cheri_insts.sail
-+++ b/model/cheri/cheri_insts.sail
-@@ @@
--      match translateAddr(vaddr, Read(if canC(auth_val) then Data else Tagged)) {
-+      match translateAddr(vaddr, Read(if canC(auth_val) then Tagged else Data)) {
-@@ @@
--      match translateAddr(vaddr, Read(if canC(auth_val) then Data else Tagged)) {
-+      match translateAddr(vaddr, Read(if canC(auth_val) then Tagged else Data)) {
-@@ @@
--      match translateAddr(vaddr, ReadWrite(if canC(auth_val) then Data else Tagged, if cs2_val.tag then Tagged else Data)) {
-+      match translateAddr(vaddr, ReadWrite(if canC(auth_val) then Tagged else Data, if cs2_val.tag then Tagged else Data)) {
 diff --git a/model/cheri/cheri_vmem_pte_ext.sail b/model/cheri/cheri_vmem_pte_ext.sail
 --- a/model/cheri/cheri_vmem_pte_ext.sail
 +++ b/model/cheri/cheri_vmem_pte_ext.sail
 @@ @@
--          (0b1, crg) if crg == mstatus[UCRG] => {
+-          (0b1, crg) if (crg != mstatus[UCRG]) & (pte[U] == 0b1) => {
 +          (0b1, crg) if crg != mstatus[UCRG] & (pte[U] == 0b1) => {
```

### `0038` `fce42120` (cheri 512bb944 + sail 764f9f1d): Re-enable self tests

- **Adjustment:** `adjustments/512bb94-self-tests-build.diff`

```diff
--- split/cheri 512bb944 + sail 764f9f1d (Re-enable self tests)
+++ merged/fce42120 (Re-enable self tests)
@@ -6,19 +6,95 @@
 @@ @@
 +                 $(SAIL_CHERI_MODEL_DIR)/cheri_csr_ext.sail \
 @@ @@
+-                 $(SAIL_CHERI_MODEL_DIR)/cheri_step_ext_nonrvfi.sail \
+@@ @@
 -                 $(SAIL_RISCV_MODEL_DIR)/riscv_step.sail
 +                 $(SAIL_RISCV_MODEL_DIR)/riscv_step.sail \
-+                 src/test_main_ext.sail \
++                 $(SAIL_CHERI_MODEL_DIR)/test_main_ext.sail \
 +                 $(SAIL_RISCV_MODEL_DIR)/test_main.sail
 @@ @@
 -                 $(SAIL_RISCV_MODEL_DIR)/riscv_step.sail
 +                 $(SAIL_RISCV_MODEL_DIR)/riscv_step.sail \
-+                 src/test_main_ext.sail \
++                 $(SAIL_CHERI_MODEL_DIR)/test_main_ext.sail \
 +                 $(SAIL_RISCV_MODEL_DIR)/test_main.sail
 @@ @@
 -             --c-preserve tick_platform
 +             --c-preserve tick_platform \
 +             --c-preserve test_main
+diff --git a/c_emulator/riscv_sail.h b/c_emulator/riscv_sail.h
+--- a/c_emulator/riscv_sail.h
++++ b/c_emulator/riscv_sail.h
+@@ @@
++unit ztest_main(unit);
+diff --git a/c_emulator/riscv_sim.cpp b/c_emulator/riscv_sim.cpp
+--- a/c_emulator/riscv_sim.cpp
++++ b/c_emulator/riscv_sim.cpp
+@@ @@
++  OPT_DO_SELF_TEST
+@@ @@
++static bool do_self_test = false;
++
+@@ @@
++    {"self-test",                   no_argument,       0, OPT_DO_SELF_TEST        },
+@@ @@
++    case OPT_DO_SELF_TEST:
++      do_self_test = true;
++      rv_enable_misaligned = true; // Tests assume misaligned allowed
++      break;
+@@ @@
+-  uint64_t entry = load_sail(initial_elf_file, /*main_file=*/true);
++  uint64_t entry;
++  if (do_self_test) {
++    entry = 0x80000000;
++  } else {
++    entry = load_sail(initial_elf_file, /*main_file=*/true);
++  }
+@@ @@
+-  do {
+-    run_sail();
++  if (do_self_test) {
++    ztest_main(UNIT);
++  } else {
++    do {
++      run_sail();
+@@ @@
+-  } while (0);
++    } while (0);
+@@ @@
+-    if (rvfi_dii) {
+-      /* Reset for next test */
+-      reinit_sail(entry);
+-    }
+-  } while (rvfi_dii);
++      if (rvfi_dii) {
++        /* Reset for next test */
++        reinit_sail(entry);
++      }
++    } while (rvfi_dii);
+@@ @@
++  }
+diff --git a/model/CMakeLists.txt b/model/CMakeLists.txt
+--- a/model/CMakeLists.txt
++++ b/model/CMakeLists.txt
+@@ @@
++                "cheri/cheri_csr_ext.sail"
++                "riscv_csr_end.sail"
+@@ @@
+-            if (variant STREQUAL "rvfi")
+-                list(APPEND sail_seq_inst_srcs "cheri/cheri_csr_ext.sail")
+-            endif()
+-            list(APPEND sail_seq_inst_srcs "riscv_csr_end.sail")
+@@ @@
++            else()
++                list(APPEND prelude "riscv_rvfi_stub.sail")
+@@ @@
+-                set(riscv_step_ext "cheri/cheri_step_ext.sail" "cheri/cheri_step_ext_nonrvfi.sail")
++                set(riscv_step_ext "cheri/cheri_step_ext.sail")
+@@ @@
++                "cheri/test_main_ext.sail"
++                "test_main.sail"
+@@ @@
++                        --c-preserve test_main
 diff --git a/model/cheri/cheri_regs.sail b/model/cheri/cheri_regs.sail
 --- a/model/cheri/cheri_regs.sail
 +++ b/model/cheri/cheri_regs.sail
@@ -178,73 +254,25 @@
 -    test_cheri_enables();
 +    //test_cheri_enables(); Disable while cheri enables hardwired high
 +    print("CHERI tests passed\n");
-diff --git a/c_emulator/riscv_sail.h b/c_emulator/riscv_sail.h
---- a/c_emulator/riscv_sail.h
-+++ b/c_emulator/riscv_sail.h
-@@ @@
-+unit ztest_main(unit);
-diff --git a/c_emulator/riscv_sim.cpp b/c_emulator/riscv_sim.cpp
---- a/c_emulator/riscv_sim.cpp
-+++ b/c_emulator/riscv_sim.cpp
-@@ @@
-+  OPT_DO_SELF_TEST
-@@ @@
-+static bool do_self_test = false;
-+
-@@ @@
-+    {"self-test",                   no_argument,       0, OPT_DO_SELF_TEST        },
-@@ @@
-+    case OPT_DO_SELF_TEST:
-+      do_self_test = true;
-+      rv_enable_misaligned = true; // Tests assume misaligned allowed
-+      break;
-@@ @@
--  uint64_t entry = load_sail(initial_elf_file, /*main_file=*/true);
-+  uint64_t entry;
-+  if (do_self_test) {
-+    entry = 0x80000000;
-+  } else {
-+    entry = load_sail(initial_elf_file, /*main_file=*/true);
-+  }
-@@ @@
--  do {
--    run_sail();
-+  if (do_self_test) {
-+    ztest_main(UNIT);
-+  } else {
-+    do {
-+      run_sail();
-@@ @@
--  } while (0);
-+    } while (0);
-@@ @@
--    if (rvfi_dii) {
--      /* Reset for next test */
--      reinit_sail(entry);
--    }
--  } while (rvfi_dii);
-+      if (rvfi_dii) {
-+        /* Reset for next test */
-+        reinit_sail(entry);
-+      }
-+    } while (rvfi_dii);
-@@ @@
-+  }
-diff --git a/model/riscv_rvfi_stub.sail b/model/riscv_rvfi_stub.sail
-new file mode 100644
---- /dev/null
+diff --git a/model/cheri/cheri_step_ext_nonrvfi.sail b/model/riscv_rvfi_stub.sail
+similarity index 56%
+rename from model/cheri/cheri_step_ext_nonrvfi.sail
+rename to model/riscv_rvfi_stub.sail
+--- a/model/cheri/cheri_step_ext_nonrvfi.sail
 +++ b/model/riscv_rvfi_stub.sail
 @@ @@
-+/*=======================================================================================*/
-+/*  This Sail RISC-V architecture model, comprising all files and                        */
-+/*  directories except where otherwise noted is subject the BSD                          */
-+/*  two-clause license in the LICENSE file.                                              */
-+/*                                                                                       */
-+/*  SPDX-License-Identifier: BSD-2-Clause                                                */
-+/*=======================================================================================*/
-+
+-// The split repository (rvy-sail-cheri-riscv) could only build the RVFI simulator between
+-// "Fixes for running with TestRIG" and "Re-enable self tests". These definitions keep the
+-// non-RVFI build of the merged repository working in the meantime; "Re-enable self tests"
+-// removes the step hooks and this file.
 +/* Stubs for RVFI functions when disabled */
-+
+@@ @@
+-function ext_fetch_hook(f : FetchResult) -> FetchResult = f
+-
+-function ext_pre_step_hook()  -> unit = ()
+-function ext_post_step_hook() -> unit = ()
+-
+-function ext_reset() -> unit = ()
 +function ext_rvfi_post_step_hook() -> unit = ()
 diff --git a/model/riscv_step.sail b/model/riscv_step.sail
 --- a/model/riscv_step.sail
```

### `0044` `b92cc130` (cheri ab305566 + sail 4fead739 + sail 5593d595): Update to new CHERI fault reporting

- **Adjustment:** `adjustments/ab30556-vext-translate-exception.diff`

```diff
--- split/cheri ab305566 + sail 4fead739 + sail 5593d595 (Update to new CHERI fault reporting)
+++ merged/b92cc130 (Update to new CHERI fault reporting)
@@ -127,9 +127,9 @@
 -mapping clause csr_name_map = 0x34b <-> "mtval2"
 -mapping clause csr_name_map = 0x14b <-> "stval2"
 -
--function clause read_CSR(0x34b, _) = mtval2.bits
+-function clause read_CSR(0x34b) = mtval2.bits
 -function clause write_CSR(0x34b, value) = { mtval2 = legalize_tval2(mtval2, value); mtval2.bits }
--function clause read_CSR(0x14b, _) = stval2.bits
+-function clause read_CSR(0x14b) = stval2.bits
 -function clause write_CSR(0x14b, value) = { stval2 = legalize_tval2(stval2, value); stval2.bits }
 diff --git a/model/cheri/cheri_insts.sail b/model/cheri/cheri_insts.sail
 --- a/model/cheri/cheri_insts.sail
@@ -568,6 +568,54 @@
 -             excinfo = (None() : option(xlenbits)),
 -             ext     = None() };
 +             excinfo = (None() : option(xlenbits)) };
+diff --git a/model/riscv_insts_vext_mem.sail b/model/riscv_insts_vext_mem.sail
+--- a/model/riscv_insts_vext_mem.sail
++++ b/model/riscv_insts_vext_mem.sail
+@@ @@
+-                TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++                TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-                  if i == 0 then { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL }
++                  if i == 0 then { handle_translate_exception(vaddr, e); return RETIRE_FAIL }
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++            TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+@@ @@
+-              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e, ext_ptw); return RETIRE_FAIL },
++              TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr, e); return RETIRE_FAIL },
+diff --git a/model/riscv_insts_zicboz.sail b/model/riscv_insts_zicboz.sail
+--- a/model/riscv_insts_zicboz.sail
++++ b/model/riscv_insts_zicboz.sail
+@@ @@
+-          TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr - negative_offset, e, ext_ptw); RETIRE_FAIL },
++          TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr - negative_offset, e); RETIRE_FAIL },
 diff --git a/model/riscv_platform.sail b/model/riscv_platform.sail
 --- a/model/riscv_platform.sail
 +++ b/model/riscv_platform.sail
@@ -629,10 +677,4 @@
 +    TR_Failure(translationException(ac, PTW_Invalid_Addr(), init_ext_ptw), init_ext_ptw)
 @@ @@
 -      TR_Failure(f, ext_ptw)  => TR_Failure(translationException(ac, f), ext_ptw)
-+      TR_Failure(f, ext_ptw) => TR_Failure(translationException(ac, f, ext_ptw), ext_ptw)
-diff --git a/model/riscv_insts_zicboz.sail b/model/riscv_insts_zicboz.sail
---- a/model/riscv_insts_zicboz.sail
-+++ b/model/riscv_insts_zicboz.sail
-@@ @@
--          TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr - negative_offset, e, ext_ptw); RETIRE_FAIL },
-+          TR_Failure(e, ext_ptw) => { handle_translate_exception(vaddr - negative_offset, e); RETIRE_FAIL },++      TR_Failure(f, ext_ptw) => TR_Failure(translationException(ac, f, ext_ptw), ext_ptw)
```

### `0054` `33028007` (cheri 9063f09d): Avoid using separate names for CHERI CSRs

```diff
--- split/cheri 9063f09d (Avoid using separate names for CHERI CSRs)
+++ merged/33028007 (Avoid using separate names for CHERI CSRs)
@@ -185,11 +185,17 @@
 +                            Machine    => mepc_y,
 +                            Supervisor => sepc_y,
 @@ @@
--  set_next_pcc(unsealCap(epcc));
-+  set_next_pcc(unsealCap(epc_y));
-@@ @@
--  epcc.address
-+  epc_y.address
+-  let aligned_addr = align_pc(epcc.address);
++  let aligned_addr = align_pc(epc_y.address);
+@@ @@
+-  let aligned_epcc = if aligned_addr == epcc.address
+-                     then epcc
+-                     else setCapAddrChecked(epcc, aligned_addr);
+-  set_next_pcc(unsealCap(aligned_epcc));
++  let aligned_epc_y = if aligned_addr == epc_y.address
++                      then epc_y
++                      else setCapAddrChecked(epc_y, aligned_addr);
++  set_next_pcc(unsealCap(aligned_epc_y));
 diff --git a/model/cheri/cheri_sys_regs.sail b/model/cheri/cheri_sys_regs.sail
 --- a/model/cheri/cheri_sys_regs.sail
 +++ b/model/cheri/cheri_sys_regs.sail
```

### `0059` `bb5cc0b9` (cheri c67ba259 + sail 1567214f): Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y

- **Adjustment:** `adjustments/c67ba25-seccfg-move.diff`

```diff
--- split/cheri c67ba259 + sail 1567214f (Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y)
+++ merged/bb5cc0b9 (Move {mseccfg, xenvcfg}.CRE to {misa, xenvcfg}.Y)
@@ -3,6 +3,11 @@
 +++ b/Makefile
 @@ @@
 -                 ${SAIL_CHERI_MODEL_DIR}/cheri_sys_regs_seccfg.sail \
+diff --git a/model/CMakeLists.txt b/model/CMakeLists.txt
+--- a/model/CMakeLists.txt
++++ b/model/CMakeLists.txt
+@@ @@
+-                "cheri/cheri_sys_regs_seccfg.sail"
 diff --git a/model/cheri/cheri_sys_regs.sail b/model/cheri/cheri_sys_regs.sail
 --- a/model/cheri/cheri_sys_regs.sail
 +++ b/model/cheri/cheri_sys_regs.sail
@@ -55,16 +60,13 @@
 --- a/model/cheri/cheri_sys_regs_seccfg.sail
 +++ /dev/null
 @@ @@
--/* whether Zkr was enabled at boot */
--val sys_enable_zkr = pure "sys_enable_zkr" : unit -> bool
--
 -function legalize_mseccfg(o : Seccfg, v : bits(64)) -> Seccfg = {
 -  let v = Mk_Seccfg(v);
 -  [
 -    o with
 -    /*
--    SSEED = if sys_enable_zkr() then v[SSEED] else 0b0,
--    USEED = if sys_enable_zkr() then v[USEED] else 0b0,
+-    SSEED = if extensionEnabled(Ext_Zkr) then v[SSEED] else 0b0,
+-    USEED = if extensionEnabled(Ext_Zkr) then v[USEED] else 0b0,
 -    */
 -    CRE = 0b1,
 -  ]
@@ -130,9 +132,6 @@
 --- a/model/riscv_sys_regs.sail
 +++ b/model/riscv_sys_regs.sail
 @@ @@
-+
-+/* whether Zkr was enabled at boot */
-+val sys_enable_zkr = pure "sys_enable_zkr" : unit -> bool
 +
 +bitfield Seccfg : bits(64) = {
 +  // Enable access to SEED in S-mode
@@ -147,8 +146,8 @@
 +  let v = Mk_Seccfg(v);
 +  [
 +    o with
-+    SSEED = if sys_enable_zkr() then v[SSEED] else 0b0,
-+    USEED = if sys_enable_zkr() then v[USEED] else 0b0,
++    SSEED = if extensionEnabled(Ext_Zkr) then v[SSEED] else 0b0,
++    USEED = if extensionEnabled(Ext_Zkr) then v[USEED] else 0b0,
 +  ]
 +}
 @@ @@
@@ -185,15 +184,12 @@
 --- a/model/riscv_sys_regs_seccfg.sail
 +++ /dev/null
 @@ @@
--/* whether Zkr was enabled at boot */
--val sys_enable_zkr = pure "sys_enable_zkr" : unit -> bool
--
 -function legalize_mseccfg(o : Seccfg, v : bits(64)) -> Seccfg = {
 -  let v = Mk_Seccfg(v);
 -  [
 -    o with
--    SSEED = if sys_enable_zkr() then v[SSEED] else 0b0,
--    USEED = if sys_enable_zkr() then v[USEED] else 0b0,
+-    SSEED = if extensionEnabled(Ext_Zkr) then v[SSEED] else 0b0,
+-    USEED = if extensionEnabled(Ext_Zkr) then v[USEED] else 0b0,
 -  ]
 -}
 diff --git a/model/riscv_sys_regs_types.sail b/model/riscv_sys_regs_types.sail
```

### `0066` `436a52fe` (cheri d6bc2cbb): Massive operand renaming

```diff
--- split/cheri d6bc2cbb (Massive operand renaming)
+++ merged/436a52fe (Massive operand renaming)
@@ -574,8 +574,8 @@
 -      match translateAddr(vaddr, Write(if cs2_val.tag then Tagged else Data)) {
 +      match translateAddr(vaddr, Write(if rs2_cap.tag then Tagged else Data)) {
 @@ @@
--                match mem_write_cap(addr, pbmt, cs2_val, aq & rl, rl, false) {
-+                match mem_write_cap(addr, pbmt, rs2_cap, aq & rl, rl, false) {
+-                match mem_write_cap(addr, pbmt, cs2_val, aq & rl, rl, true) {
++                match mem_write_cap(addr, pbmt, rs2_cap, aq & rl, rl, true) {
 @@ @@
 - * Capability Pointer Mode:
 - * amoswap.y cd, cs2, offset(cs1)
@@ -599,8 +599,8 @@
 +      let rs2_cap = clearTagIf(rs2_cap, not(canC(auth_val)));
 +      let rs2_cap = legalizeStoredPermissions(rs2_cap, auth_val);
 @@ @@
--      match translateAddr(vaddr, ReadWrite(if canC(auth_val) then Tagged else Data, if cs2_val.tag then Tagged else Data)) {
-+      match translateAddr(vaddr, ReadWrite(if canC(auth_val) then Tagged else Data, if rs2_cap.tag then Tagged else Data)) {
+-      let typ = ReadWrite(if canC(auth_val) then Tagged else Data, if cs2_val.tag then Tagged else Data);
++      let typ = ReadWrite(if canC(auth_val) then Tagged else Data, if rs2_cap.tag then Tagged else Data);
 @@ @@
 -                  match mem_write_cap(addr, pbmt, cs2_val, aq & rl, rl, false) {
 +                  match mem_write_cap(addr, pbmt, rs2_cap, aq & rl, rl, false) {
```

### `0067` `ede7a0f0` (cheri 5a95a40a): Root not infinite caps

```diff
--- split/cheri 5a95a40a (Root not infinite caps)
+++ merged/ede7a0f0 (Root not infinite caps)
@@ -245,8 +245,8 @@
 -    write_ylen_csr(csr_name_map("ddc"), infinite_cap);
 +    write_ylen_csr(csr_name_map("ddc"), root_cap);
 @@ @@
--    let (_, finite_cap) = setCapBounds(infinite_cap, zeros(), zero_extend(0xff00_0000_0000_0000));
-+    let (_, finite_cap) = setCapBounds(root_cap, zeros(), zero_extend(0xff00_0000_0000_0000));
+-    let (_, finite_cap) = setCapBounds(infinite_cap, zeros(), zero_extend(0xff @ zeros(xlen - 8)));
++    let (_, finite_cap) = setCapBounds(root_cap, zeros(), zero_extend(0xff @ zeros(xlen - 8)));
 @@ @@
 -    Y(infiniteR) = {infinite_cap with address=invalidAddr};
 +    Y(infiniteR) = {root_cap with address=invalidAddr};
```

### `0105` `e09feaf1` (cheri 5a72076b): Add allowSealedUnchanged operand to setAddrChecked

- **Adjustment:** `adjustments/5a72076-setcapaddrchecked-xret.diff`

```diff
--- split/cheri 5a72076b (Add allowSealedUnchanged operand to setAddrChecked)
+++ merged/e09feaf1 (Add allowSealedUnchanged operand to setAddrChecked)
@@ -28,6 +28,16 @@
 @@ @@
 -  let c = setCapAddrChecked(c, addr);
 +  let c = setCapAddrChecked(c, addr, false);
+diff --git a/model/cheri/cheri_sys_exceptions.sail b/model/cheri/cheri_sys_exceptions.sail
+--- a/model/cheri/cheri_sys_exceptions.sail
++++ b/model/cheri/cheri_sys_exceptions.sail
+@@ @@
+-  /* Only call setCapAddrChecked() if the address actually changed to
+-   * avoid invalidating sentries that already have the correct address */
+-  let aligned_epc_y = if aligned_addr == epc_y.address
+-                      then epc_y
+-                      else setCapAddrChecked(epc_y, aligned_addr);
++  let aligned_epc_y = setCapAddrChecked(epc_y, aligned_addr, true);
 diff --git a/model/cheri/cheri_sys_regs.sail b/model/cheri/cheri_sys_regs.sail
 --- a/model/cheri/cheri_sys_regs.sail
 +++ b/model/cheri/cheri_sys_regs.sail
```

## Identical Commits (86)

- `0004` `2f21f2f1` (sail cb6b63ae): Fix range checking wrap bug in RVFI memory range
- `0005` `fad20433` (sail 9ef5189d): Add catchall default false extensionEnabled
- `0009` `55d5733c` (cheri d11a7bff): Make lr/sc encdec mapping formatting consistent
- `0011` `ba4f30a2` (cheri c78f5c0f): Comment out tag-clearing reset for testrig
- `0013` `a3ab2145` (cheri 5ea51b6e): Hardwire cre to true in mseccfg rather than ignoring the CSR value
- `0014` `6dc42905` (cheri 82a451fd): Legalise envcfg registers to match hardwired Toooba
- `0016` `4a4efd98` (sail 94e9ab8c): Legalise mtvec by masking
- `0017` `15ed648c` (sail 2a46f0e7): Legalise cause field more aggressively
- `0018` `48307d22` (sail 1fda4b95): Mask mode on SATP writes
- `0020` `b812f790` (cheri 97fc9d5f): Remove features from mseccfg unsupported by Toooba
- `0021` `5b114878` (cheri d6b354e4): Reenable writable fiom
- `0022` `7df86c4b` (sail e3610d6d): Move to CVA6 tvec legalisation function
- `0023` `f8f1a3a2` (sail 2b89f1f0): Preserve all cause bits to match CVA6
- `0024` `234416b0` (sail 12943e2f): Allow compressed hints to be expanded
- `0025` `a399d268` (sail b8c7d8c2): Disable fetch translation checks with RVFI to compare to CVA6
- `0028` `9c55be54` (sail 6707d982): Disable PMA checks with TestRIG
- `0029` `a883b089` (sail 92e25bb9): Remove Toooba-specific satp legalisation
- `0030` `c70f6b24` (cheri 726b5ac3): Promote accessed faults to potentially imply 'both' cheri and non-cheri error
- `0031` `957fb7f3` (sail 74194fdf): Disable napot
- `0032` `f202b463` (cheri 65c7eb95): Add reserved ones to decoded BitPerms
- `0033` `511c368e` (cheri c2bba772): Remove tdc registers from testing
- `0034` `5cbbe441` (cheri 8b492653): Detect if no invalid addresses in test
- `0036` `cbaa8b45` (cheri 8e5ec4c0): Test modifications to mscratch, not mtvec
- `0037` `6ebf53da` (cheri de315332): Fix comment parsing
- `0039` `682dfcec` (cheri 3281cc80): Move from C to Y
- `0040` `a2019601` (cheri a91c2954): Fix ASR checking bug on cbo.inval
- `0041` `7f46f194` (cheri 63ca014b): Require whole-line bounds for cbo.inval
- `0042` `db7ff754` (cheri 185f9d0b): Access fault on misaligned capabilities
- `0043` `60c1b022` (cheri 8a9582fc + sail f36af419): Remove CHERI branch exception checks
- `0046` `f6fb97ff` (cheri f62f7a3b): ACPERM clears tag if input perms malformed
- `0047` `edf3fc0f` (cheri 32be9d4a): Implement broader integrity checks
- `0048` `4654e54b` (cheri 4d592b92): Reserve some branch encodings in capmode
- `0049` `5fe642cc` (cheri 1316336a): Include Zicbo files in CHERI build
- `0050` `901a149f` (cheri 04106dc0 + sail ec4c1fed): xret and cbo.inval all throw illegal if no ASR
- `0051` `d351ba64` (cheri 0d78a407): Clear tag if target PCC is unrepresentable
- `0052` `0ab4bcbf` (cheri aa10d9bb): Rename load and store instructions to use Y datatype
- `0053` `e72f72fe` (cheri 84ace6b2): Remove tdc registers
- `0055` `990f8c2a` (cheri 80b7468f): Perform instruction renaming (e.g. ywbase)
- `0056` `15eaa719` (sail 64206047): Remove option not to expand hints
- `0057` `11a7efc3` (cheri 03960a08): Remove special treatment of DDC as 'YLenNew'
- `0058` `0ef49341` (sail 48f90323): Add misa.Y support
- `0060` `a5539570` (cheri d23b51bd): Another ISA renaming (e.g. YBASER)
- `0061` `b466a1af` (cheri 6ee2813a): Add separate YSH<n>ADD[UW] encodings
- `0062` `b7cd4f0e` (cheri 479f7ff8): SRLIY and PACKY
- `0063` `bae24bcf` (cheri 02afac77): Update YBNDSIW encoding
- `0064` `937c852e` (cheri bfae32c5): Rename ybndsiw to ybndswi
- `0065` `f34212f9` (cheri 28538979): Change YPERMC to bit-clearing
- `0068` `b34c9e2f` (cheri 7788d286 + sail 16bec3cc): Rework Svucrg to 3-bit CHERI PTEs
- `0069` `93dffeff` (cheri b22e1d2c): Rename PTE CW to CRW
- `0070` `ab649618` (cheri 1f14ef1f): Remove some MXLENs
- `0071` `f75cca84` (cheri 60a554b9): Add YSUNSEAL
- `0072` `a7d7cc85` (cheri f9081f53): Update YBNDSWI encoding
- `0074` `166e63bb` (cheri cc4f53c5): Rename CL to GL
- `0075` `d5a10581` (cheri 874aa6e5): Add CRGE ucrg enable bit in xstatus
- `0076` `154c5f2c` (cheri f7106ead): Add YTOPR
- `0077` `4ee30143` (cheri f573e046): Fix YMODEW to have full integrity checks
- `0078` `a773141d` (cheri 083fa151): CRGE clear implies reserved CD and CRG
- `0079` `d4e2f759` (cheri fcf4a2ff): Fix YMODEW to honour "otherwise" in spec
- `0080` `faa99476` (cheri d0385969): 4-bit PTE scheme
- `0081` `8fe734ed` (cheri 8d42af82): Flip reserved branch encodings
- `0082` `b6cf900d` (cheri 8d6ca2d2): Rename ADD(I)Y to YADD(I)
- `0083` `8a03b3a6` (cheri 6d4651c8): YLT -> YSS, SYEQ -> YEQ
- `0084` `c90f0765` (cheri 20c04ad4): Mode-related renamings
- `0086` `dad55634` (cheri 5b0712ef): Revert "Remove special treatment of DDC as 'YLenNew'"
- `0087` `ed90802d` (cheri 157a45a7): Implement new instruction encodings
- `0088` `b9dd4c9d` (cheri 8dbac544 + sail 7512afd0): Prevent disabling Y unless system caps are root
- `0089` `58ea3fb0` (cheri ef9839a8): Fix YSENTRY encoding
- `0090` `c932f304` (cheri 90bcdd2c): Move Y to bit 9 in xenvcfg
- `0091` `e3008b37` (cheri 90e27038): Change metadata field arrangement
- `0092` `7fe6c13e` (cheri e839930b): Memory accesses can use zreg in IntPtrMode
- `0093` `8ba90bca` (cheri 41c40d96): Fix YMODER encoding
- `0094` `ff9b80a8` (cheri 37d1d4d7): Fix SENTRY encoding
- `0095` `f14d9484` (cheri 3992e639): Fix sentry operand order encoding
- `0096` `2550f66d` (cheri 69a87b08): Move the mode bit to the bottom of the AP field
- `0097` `314921a3` (cheri b9b8f242): Add Zcb to Makefile
- `0098` `099c03dd` (cheri 176fde10): Fix YMODEW encoding to reserve rd=0
- `0099` `1f8c97a9` (cheri 12ef78ac): xtidc is YLenNew, not extended
- `0100` `f2694c73` (cheri 8320d28f): Fix inverted CHERI PTE permission check
- `0101` `4913ce04` (cheri 5576a0c7): Fix: SY can have rs1=0 in int_mode
- `0102` `6549edf7` (cheri 543bd62b): Fix YSUNSEAL check
- `0103` `6ed589d1` (cheri 74753ced): Return to A/D being handled alongside other PTE perm failures
- `0104` `2e309ed9` (sail e6752e8a): Don't indicate x in misa
- `0106` `e70e10aa` (cheri f57f7833): Fix successful jump assertion in tests
- `0107` `a2f15fda` (cheri 71610658): Fix: JALR must not unseal target cap on non-zero imm
- `0108` `13bb4168` (cheri 5083802b): Fix: JALR with non-zero immediate to sentries left tag set and could change their address
- `0109` `3a2c6d34` (cheri 117b61a0): Reset registers to null_cap
