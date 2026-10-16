# Chameleon6S ASIC and CPO firmware upgrade test plan

HLD: https://github.com/nvidia-sonic/SONiC/blob/e43e25e6c90b09972c11062ef372c0a127f5f125/doc/nvidia-cpo-fw-upgrade/Chameleon6S-ASIC-and-CPO-FW-Upgrade-HLD.md

## Table of contents

- [Shortcut map](#shortcut-map)
- [The core idea](#the-core-idea-mental-model)
- [Test case summary & coverage](#test-case-summary--coverage)
- [Overview](#overview)
- [Scope](#scope)
- [References](#references)
- [Testbed and topology](#testbed-and-topology)
- [Prerequisites / setup](#prerequisites--setup)
- [Command validation system](#command-validation-system)
- [Module prerequisites](#module-prerequisites)
- [Test cases](#test-cases)
- [Conventions](#conventions)
- [Known limitations](#known-limitations)
- [Open / action items](#open--action-items)
- [Future automation](#future-automation)
- [Edge-case checklist](#edge-case-checklist)
- [Reboot scope](#reboot-scope)

## Shortcut map

| Shortcut | Meaning |
|----------|---------|
| HLD | Design linked above, Rev 1.1 |
| QG | Quality guarantees workbook for vModule auto firmware upgrade |
| OE | Optical engine firmware, component `OE_FW` |
| MFA | Combined ASIC and optical-engine firmware archive shipped in the image |
| CPO | Co-packaged optics platform, Chameleon6S / SPC6 |
| DUT | Device under test |

## The core idea (mental model)

Two existing install paths already burn firmware when the image firmware differs. A later sanity check reads the versions. One new install, using another flavor of the same image such as PRC, proves the burn does not run when the firmware matches.

```
test_deploy_and_upgrade (sonic | onie, firmware differs) -> test_component_version_check
new same-firmware flavor install -> status up to date, no flash write
```

## Test case summary & coverage

Three cases. P0 is a skip gate and stays under 2 minutes. P1 is two full installs: the regression deploy the lab already runs, plus one extra install of the same-firmware flavor. Each install can spend 600 seconds waiting for SSH to drop and 600 seconds waiting for SSH to return, then docker readiness. Expect P0+P1 to take longer than 30 minutes. That time is the existing regression install plus one extra install.

| TC | What it proves (plain language) | Pri | Area | HLD § |
|----|---------------------------------|-----|------|-------|
| TC-PRE-01 — CPO suite skips cleanly | A non-CPO DUT skips the new checks. A CPO DUT with no OE_FW row fails | P0 | PRE fixture (module) | §2.13, AF-7, AF-10 |
| TC-DELTA-01 — Differing firmware install converges | An install of two images with different firmware leaves ASIC and OE versions at the image | P1 | Functionality | AF-2, AF-3, AF-8, AF-9, AF-10, AF-12, §3.1 |
| TC-SKIP-01 — Same-firmware flavor skips burn | A second flavor with the same firmware does not burn | P1 | Functionality | AF-3, §2.3.1, §3.1 item 2 |

Area disposition, including areas with no standalone case:

| Area | Disposition |
|------|-------------|
| 1 Functionality | TC-DELTA-01, TC-SKIP-01. TC-PRE-01 is the module skip gate, not a functionality case |
| 2 Interoperability | No new case. The original non-CPO `test_deploy_and_upgrade` and `FW` row in `test_component_version_check` must pass (AF-7) |
| 3 Reliability | No new case and no new timer. TC-DELTA-01 and TC-SKIP-01 pass only if the waits those paths already use return. `deploy_sonic` and `install_image_onie` both call `check_port_status_till_alive` with the default 300 tries and 2 seconds (600 seconds per SSH-down or SSH-up wait). ONIE also requires `SonicOnieCli.install_image` to return (`timeout=60`, `num_retry=10` on the install prompt). `upgrade_switch` calls `verify_dockers_are_up` (`tries=25`, `delay=10`) after the target image for both deploy types, and that call must return. The existing `sudo get_component_versions.py` call inside `test_component_version_check` must return; that is the about-5-second first-call allowance. The about-40-second and about-5-second reboot allowances sit inside the 600-second SSH waits |
| 4 Performance | N/A. The quality guarantee marks performance N/A |
| 5 Scale | N/A as a suite. One `mlxfwmanager` session per ASIC is a log check inside TC-DELTA-01 (AF-12). The quality guarantee assigns no Ver or QA mark to scale |
| 6 Installation, Setup, Upgrade | N/A. The quality guarantee marks upgrade and downgrade N/A. SONiC and ONIE installs are area 1 |
| 7 Logging and Debugability | N/A as a suite. The quality guarantee assigns no Ver or QA mark. TC-DELTA-01 and TC-SKIP-01 count `mlxfwmanager -u` burn lines in the log for that install path (pre-reboot console on sonic, post-boot syslog on ONIE) |
| 8 Customer Scenarios | N/A. The quality guarantee names no customer setup |
| Template 10 Scale | Same as area 5 |
| Template 11 Logging | Same as area 7 |
| Template 12 Security | N/A. No new API. Corrupt-MFA coverage stays in `test_secure_corrupt_fw` and is not this feature |
| Longevity (template 9) | Omitted |

## Overview

Canonical ngts. The feature is the boot-time auto upgrade of ASIC and vModule firmware inside an image install. Assertions are added to `ngts/scripts/sonic_deploy/test_deploy_and_upgrade.py` and to `test_component_version_check`. The push-gate fixture uses the same `deploy_image` and gets no new case.

## Scope

### In scope

- `--deploy_type sonic`: `sonic-installer install` plus reboot (`SonicGeneralCli.deploy_sonic`).
- `--deploy_type onie`: `onie-nos-install` (`SonicGeneralCli.deploy_onie`).
- After that deploy, `sudo get_component_versions.py` shows `FW` and `OE_FW`. `COMPILATION` is the image version in the form the device reports. `ACTUAL` is the running version.
- `sudo mlnx-fw-manager --status` and `--dry-run` show the `OE` line from HLD §2.3.1, with the exit codes in that section.
- A new install of another flavor of the tested image, for example PRC, whose ASIC and OE firmware match the installed image. The test must show that no flash write happened.
- syncd is up after the existing deploy readiness check.
- Existing install waits still complete. No new timer.

### Out of scope

- A new non-CPO test. The original deploy and `FW` check must pass.
- Push-gate cases in `ngts/tests/push_build_tests/conftest.py`.
- HLD §7 `--auto-upgrade` and `--burn`.
- ELS / `cpoutil` / `sfputil` firmware update (HLD §0.2).
- Warm reboot and fast reboot (HLD §1.6). The control-plane downtime sentence in §1.6 applies when warm boot exists.
- Upgrade from 202605. HLD §2.3.1 says 202605 does not support a CPO platform. Non-CPO behavior stays on the original flow.
- Injecting an unreadable `OE_FW` version. The quality guarantee does not include that branch. HLD unit tests cover the compare rule (AF-13).
- A FW-control versus SW-control matrix. The quality guarantee has no such row. The deploy runs in the DUT's current mode (AF-4).
- Partial-ASIC failure injection (`FirmwareUpgradePartialError`, HLD §1.7). The quality guarantee does not include it.
- Keyword interaction pairs that do not share a resource with this feature: generic config updater (no CONFIG_DB, HLD §1.3), telemetry, gNMI, and SNMP (no northbound API, HLD §4.1), QoS, SRv6, decap, tunnel QoS remap, and packet trimming (no header rewrite), thermal control and SED password management (no shared platform daemon state; syncd only has to start), and transceiver (OE firmware is in ASIC flash, not a pluggable; ELS via CDB is HLD §0.2). Warm reboot and the NSWARCH ISSU page are already listed above.
- Port-lifecycle practice. OE firmware is written once per ASIC in ASIC flash (AF-12). A port admin toggle does not program it.
- Performance, scale, image upgrade/downgrade, syslog-as-a-suite, and customer scenarios. The quality guarantee marks them N/A or leaves Ver and QA unmarked.
- The NSWARCH page "CPO FW Control Architecture" (ISSU / NVUE / ELS). The HLD cold-reboot path is authoritative.
- HLD §2.9 syslog events other than the `mlxfwmanager -u` count. The quality guarantee assigns no Ver or QA mark to logging. Partial-burn ERROR injection is already out of scope.
- HLD §5.1 and §5.2. Both say none. §5.3 points at the lower-layer commands already used above.
- snappi / traffic-generator tests. This feature has no dataplane claim.
- Pytest files. This document is the test plan only.

## References

- HLD Rev 1.1, link above.
- Quality guarantee workbook: Support auto firmware upgrade for vModule.
- `ngts/scripts/sonic_deploy/test_deploy_and_upgrade.py`
- `ngts/cli_wrappers/sonic/sonic_general_clis.py` (`deploy_sonic`, `deploy_onie`, `install_image`)
- `ngts/cli_wrappers/sonic/sonic_onie_clis.py` (`onie-nos-install`)
- `ngts/tests/nightly/sanity_checker/test_sanity_checker.py` (`test_component_version_check`)
- `devts/infra/tools/validations/traffic_validations/port_check/port_checker.py` (`check_port_status_till_alive`, tries=300, delay=2)

## Testbed and topology

Canonical ngts DUT with the usual deploy testbed. Positive checks need a Chameleon6S / CPO switch. Non-CPO switches keep running the existing deploy and sanity checker; they do not run TC-DELTA-01 or TC-SKIP-01.

No traffic generator. No extra hosts beyond the deploy setup.

## Prerequisites / setup

Feature readiness gate: TC-PRE-01 runs first. A non-CPO DUT skips TC-DELTA-01 and TC-SKIP-01, and that skip is not a suite failure. A CPO DUT with no `OE_FW` row fails the suite.

### Command validation system

Steps run on the DUT shell as admin, unless the step says the ngts deploy host. `sudo` is required for `get_component_versions.py`, `mlnx-fw-manager`, `flint`, and `redis-cli` when admin is not root. Install commands run on the deploy host through `SonicGeneralCli`. The DUT must already answer SSH before TC-PRE-01. Image files and READMEs are on the deploy host. There is no CONFIG_DB key for this feature.

Image pairs:

| Pair | Used by | Firmware |
|------|---------|----------|
| Regression base and target | TC-DELTA-01 | Different, as the deploy job already passes them |
| Tested image and another flavor, example PRC | TC-SKIP-01 | Same ASIC and OE firmware. The HLD does not name PRC; the flavor is the one the user supplied |

Component observation inside TC-DELTA-01:

| Component | When the two images differ in it | When they do not |
|-----------|----------------------------------|------------------|
| `FW` (ASIC) | `ACTUAL` equals the target image version after reboot | `ACTUAL` unchanged |
| `OE_FW` | `ACTUAL` equals the translated MFA version (HLD §2.3.1: middle field divided by 2, last two digits) | `ACTUAL` unchanged |

HLD §3.1 item 1 is the case where only `OE_FW` differs. The regression pair is whatever two images the deploy job uses, and the user stated those firmware versions differ. Each component is checked on its own. A burn that rewrites ASIC with the same version still leaves `FW` `ACTUAL` equal to that version.

## Module prerequisites

- Module: TC-PRE-01. Skip TC-DELTA-01 and TC-SKIP-01 when the DUT is not CPO.
- The regression already runs `test_deploy_and_upgrade` before `test_sanity_checker.py`. TC-DELTA-01 does not install a third image.
- TC-SKIP-01 is a separate install and is not part of that default pair.

## Test cases

### Functionality

**TC-PRE-01 — CPO suite skips cleanly**

**Priority: P0**

Objective: the new checks run only on a CPO DUT that can report `OE_FW`.

Steps:

1. On the DUT shell, run `sudo get_component_versions.py`.
2. Read the hwsku with `redis-cli -n 4 hget "DEVICE_METADATA|localhost" hwsku` (the same read as `get_sonic_hwsku` in `ngts/scripts/test_rpc_check_and_set_topology.py`). The image's own CPO check is `device_info.get_cpo_data()` (HLD §2.3.1). If that hwsku is not the Chameleon6S SKU in the testbed `platform_params.hwsku`, skip TC-DELTA-01 and TC-SKIP-01. That skip is not a failure. The existing non-CPO deploy and `FW` check continue as they do today.
3. If the hwsku is the Chameleon6S SKU and the table has no `OE_FW` row, fail. Do not skip.

Expected result: a CPO DUT shows an `OE_FW` row. A CPO DUT without that row fails. Any other DUT skips the new checks.

Cleanup: none.

---

**TC-DELTA-01 — Differing firmware install converges**

**Priority: P1**

Objective: after the regression install of two images with different firmware, ASIC and OE versions match the image, syncd is up, and the existing SSH wait still finishes.

Parameter: `--deploy_type` is `sonic` or `onie`. Both are runs of `test_deploy_and_upgrade`. `sonic` uses `sudo sonic-installer install <bin> -y` and `sudo reboot`. `onie` uses `onie-nos-install`.

Steps:

1. Run the existing `test_deploy_and_upgrade` with the regression base and target images. Do not add a push-gate case.
2. Pass only if the waits that path already uses return. Do not add a timer. For `--deploy_type sonic`, `deploy_sonic` calls `check_port_status_till_alive` (default 300 tries, 2 seconds) for SSH down and SSH up. For `--deploy_type onie`, `install_image_onie` uses that same helper for SSH down and SSH up, and `SonicOnieCli.install_image` must return within `timeout=60` and `num_retry=10`.
3. On the DUT, run `sudo get_component_versions.py`. The existing `test_component_version_check` invocation must return. That covers the about-5-second first-call allowance. Do not add a timer.
4. On the DUT, run `sudo mlnx-fw-manager --status` and `sudo mlnx-fw-manager --dry-run`.
5. Confirm syncd is running with `verify_dockers_are_up` (tries=25, delay=10). `upgrade_switch` already calls this after the target image for both deploy types.
6. Count burn lines, meaning `mlxfwmanager -u` (HLD §2.6). Query lines (`--query-format`, `--list-content`) do not count. On `--deploy_type sonic` the burn is in `pre_reboot_hook` before shutdown (HLD §2.1 row 1, §3.2.1 item 11): count those lines in the reboot console of the session that runs `sudo reboot`, or in `/var/log/syslog` copied before SSH drops. Do not use the syslog taken after SSH returns; that file is the new image's boot-time run, which is already up to date if the hook burned. On `--deploy_type onie` the burn is the boot-time service (HLD §2.1 row 2): count `mlxfwmanager -u` in post-boot syslog (HLD §3.2.1 item 9). Expect one burn per ASIC that burned (AF-12, §2.3.2). Do not use LogAnalyzer for this count. `analyze()` in `tests/common/plugins/loganalyzer/loganalyzer.py` reads live DUT `/var/log` after SSH returns, which on the sonic path is the new image's boot log. On ONIE, `onie-nos-install` wipes the partition (`sonic_onie_clis.py`), so a start marker written before the install does not bound the new syslog.

Expected result:

- `OE_FW` `COMPILATION` is the image MFA version in device form. `ACTUAL` is the running bank. An unreadable version would show `N/A`; this pair is readable.
- `FW` `ACTUAL` matches the target image ASIC version when that version differs, and is unchanged when it does not.
- `--status` exits 0 and prints `OE: up to date (<version>)` once the running bank holds the image (HLD §2.3.1). Exit is non-zero only on a remaining delta.
- `--dry-run` prints `Firmware is up to date.` and `ASIC N OE: up to date (<version>)`, and exits 0. A remaining delta exits 10.
- syncd is up.
- The SSH waits returned inside 300 attempts.
- One `mlxfwmanager -u` burn per ASIC that differed, in the log window for that deploy type.

Cleanup: the DUT stays on the target image, which is the regression's normal end state.

---

**TC-SKIP-01 — Same-firmware flavor skips burn**

**Priority: P1**

Objective: installing another flavor with the same firmware does not burn flash.

Steps:

1. Start from a DUT already on the image under test. Record `sudo get_component_versions.py` (`FW` and `OE_FW` `ACTUAL`).
2. Before installing, compare firmware. Parse `FW` from both image READMEs the way `parse_readme_versions` does in `test_sanity_checker.py`. The two `FW` values must be equal. For the installed image, `OE_FW` comes from the MFA already on the DUT at `/etc/mlnx/fw-<asic>.mfa` (HLD §2.6.1), queried with `mlxfwmanager -i <mfa> --psid <psid> -extract --extract-file <fwpkg>` then `flint -i <fwpkg> --component_type VMOD q` (HLD §1.5). The flavor installer still needs that MFA pulled out of the SONiC bin, which is `[TBD — mechanism unverified; requires DUT confirmation]`. If the versions differ, or that extract is not available, fail the precondition. Do not install, and do not call that a product failure.
3. Install the other flavor. The example is PRC. Use the same `deploy_image` path (`deploy_type` `sonic` or `onie`).
4. Capture the burn log for this install with the same window as TC-DELTA-01 step 6: reboot console or pre-drop syslog on sonic, post-boot syslog on ONIE.
5. After SSH is back, run `sudo get_component_versions.py`, `sudo mlnx-fw-manager --status`, and `sudo mlnx-fw-manager --dry-run`.
6. The SSH waits are the same `check_port_status_till_alive` defaults as TC-DELTA-01. They must return. `verify_dockers_are_up` must return.

Expected result:

- `ACTUAL` for `FW` and `OE_FW` is unchanged. That alone is not a pass.
- `--status` exits 0 and shows `OE: up to date (<version>)`.
- `--dry-run` exits 0 and shows `Firmware is up to date.`
- The burn log for this install contains zero `mlxfwmanager -u` lines (HLD §3.1 item 2). One or more is a failure. Query-only `mlxfwmanager` lines do not count.
- `verify_dockers_are_up` returns, so syncd is up.

Cleanup: leave the DUT on the flavor that was just installed, or restore the regression target image with the existing deploy path if a later test requires it.

## Conventions

Commands run on the DUT as admin, with `sudo` where shown. Install commands run from the ngts deploy host through `SonicGeneralCli`. Pass and fail are the expected strings and exit codes above. There is no CONFIG_DB key to clear.

## Known limitations

- The device may report a different OE middle field on a staged bank (`95.10` running, `95.5` staged, HLD §6). A check between burn and ASIC reset can say `upgrade needed` until the firmware workaround matches a staged bank. TC-DELTA-01 samples `--status` after the reboot that activates the image, when the running bank should match.
- Version translation (middle field divided by 2) is a temporary workaround (HLD §2.3.1).
- SimX / KVM is skipped by `_exit_if_qemu` (HLD §2.13).
- The NSWARCH firmware-control page describes ISSU and NVUE. This plan follows the HLD cold-reboot auto path.
- PRC is an example flavor. The HLD does not name it.

## Open / action items

- Confirm which same-firmware flavor the lab will use for TC-SKIP-01. PRC is the example from the user. The HLD does not name it.
- Confirm how the test host extracts the combined MFA from a SONiC installer before TC-SKIP-01. The OE compare command is the HLD query. The unpack step is not an existing ngts helper.
- HLD §1.5 sample reboot-to-ping on Chameleon is 209 seconds with a burn and 89 seconds without. The quality guarantee says about 40 seconds and about 5 seconds of added delay. This plan does not measure those samples. It only requires the existing waits to return. The 600-second SSH wait covers both figures.
- Confirm the regression's `--deploy_type`. Both `sonic` and `onie` are in scope as runs of the same test. A job that passes only one of them covers only that install path.
- Before TC-DELTA-01, compare the two images the way TC-SKIP-01 compares `FW` and `OE_FW`. Fail the precondition unless at least one component differs, and set the `mlxfwmanager -u` count from that delta. Recorded from the stage 6 review. The steps above were not changed after that review.
- Name the PSID read `flint -d <pci> q` (HLD §2.3.1) before the MFA extract on `/etc/mlnx/fw-<asic>.mfa`. The flavor-installer unpack stays the existing TBD.
- HLD §6 item 3: `flint -d <pci> --vmod --downstream_device_ids 0 q` can return the ASIC image or fail until a fixed MFT. An unknown `OE_FW` read on that lab image is an environment block, not a product miss.
- TC-SKIP-01 dry-run currently requires `Firmware is up to date.` TC-DELTA-01 also requires `ASIC N OE: up to date (<version>)`. Use that second line on the skip case as well when the test is written.

## Future automation

| TC | Pytest |
|----|--------|
| TC-PRE-01 — CPO suite skips cleanly | extend `test_component_version_check`: skip the new OE checks when the platform is not CPO; fail when it is CPO and `OE_FW` is absent |
| TC-DELTA-01 — Differing firmware install converges | extend `test_deploy_and_upgrade` and `test_component_version_check` |
| TC-SKIP-01 — Same-firmware flavor skips burn | `test_cpo_same_firmware_flavor_skips_burn` |

`test_secure_corrupt_fw` and `test_startup_time_degradation` have no row. They are not this feature.

## Edge-case checklist

| Category | Disposition |
|----------|-------------|
| Boundary values | Out of scope. No configuration (HLD §1.3) |
| Absent config | Out of scope. No knob |
| Churn / toggle | Out of scope. No enable flag in this phase (HLD §7 deferred) |
| Ordering | Covered. Pre-reboot install path and boot-before-syncd path are the two `--deploy_type` values |
| Scale | Out of scope as a suite. One burn per ASIC is a log check in TC-DELTA-01 |
| No-op | TC-SKIP-01 |
| Persistence across config reload | Out of scope. No CONFIG_DB |
| Malformed input | Out of scope. No packet path. Corrupt MFA stays in `test_secure_corrupt_fw` |
| Recovery / partial failure | Out of scope. Quality guarantee does not include `FirmwareUpgradePartialError` |
| All ASICs | TC-DELTA-01 checks one burn session per ASIC present on the DUT |

## Reboot scope

| Reboot | Disposition |
|--------|-------------|
| Cold reboot that follows sonic-installer or ONIE install | In scope. It is the install path |
| `config reload` | Out of scope. No configuration |
| Warm reboot | Out of scope until the platform supports it (HLD §1.6) |
| Fast reboot | Out of scope (HLD §0.2) |
| syncd restart as a config restore | Out of scope. The in-scope check is that syncd is up after install (AF-9) |
