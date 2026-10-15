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
| HLD | Design linked above |
| TC | Test case |
| PRE | Readiness gate |
| OE | Optical engine firmware, component `OE_FW` |
| MFA | Combined ASIC and optical-engine firmware archive |
| CPO | Co-packaged optics platform, Chameleon6S / SPC6 |
| ASIC | Switch ASIC that stores `OE_FW` for the optical engines behind it |
| DUT | Device under test |

## The core idea (mental model)

An existing SONiC-to-SONiC install or ONIE install is the only stimulus. After the reboot that install already performs, optical-engine firmware on a CPO switch matches the image, stays put when the policy file is present, or stays absent on a non-CPO switch. `syncd` still starts.

```
install (sonic-installer | onie-nos-install) -> reboot -> OE_FW ACTUAL + syncd + syslog
```

## Test case summary & coverage

Nine cases. P0 is the readiness read. P1 is one SONiC install pair plus the policy file and the log check. Each P2 case is another install and runs weekly.

| TC | What it proves (plain language) | Pri | QG area | HLD § |
|----|---------------------------------|-----|---------|-------|
| TC-PRE-01 — CPO install baseline is recorded | CPO DUT exposes `OE_FW` before any install | P0 | PRE fixture (scope: module) | §2.13, AF-10 |
| TC-SONIC-01 — SONiC install converges OE firmware | SONiC-to-SONiC install applies an OE delta or skips a match | P1 | Functionality | AF-2, AF-3, AF-9, QG-1, QG-2 |
| TC-POLICY-01 — Disabled policy survives SONiC install | Marker file blocks the burn across a SONiC install | P1 | Customer Scenarios | AF-6, OF-2, OF-5, §2.3.1 |
| TC-LOG-01 — Install syslog records OE result | Saved install logs contain the auto-flow events the install cases do not already assert | P1 | Logging & Debugability | §2.9 |
| TC-ONIE-01 — ONIE install converges OE firmware | ONIE install applies the image OE and clears the marker | P2 | Installation/Setup/Upgrade | AF-2, §2.13 |
| TC-ASIC-01 — Install burns once per ASIC | The oe-delta install log shows one OE burn per ASIC | P2 | Scale | AF-12, §1.7 |
| TC-PLAT-01 — Non-CPO install ignores OE | Existing non-CPO install grows no OE row | P2 | Interoperability | AF-7 |
| TC-PERF-01 — OE burn extends install reboot | Syncd-up times saved by the SONiC install stay within the HLD samples | P2 | Performance | §1.5 |
| TC-FAIL-01 — Partial ASIC failure is logged | A partial burn is an error, not a silent success | P2 | Reliability | §1.7, §2.9 |

## Overview

The install, reboot, and post-install health steps already exist. This plan adds the optical-engine result on top of those steps. Feature behavior is defined in the HLD.

## Scope

### In scope

- SONiC-to-SONiC install via the existing `deploy_type='sonic'` path, or `install_sonic` plus cold reboot.
- ONIE install via the existing `onie-nos-install` path.
- `OE_FW` in `get_component_versions.py` after those installs.
- Policy marker file created on the DUT, then left in place across a SONiC install.
- ONIE clearing that file.
- One OE burn per ASIC.
- Non-CPO run of the same install flows.
- Syncd-up timing against HLD §1.5.
- Auto-flow syslog events from HLD §2.9 Table 1.

### Out of scope

- `mlnx-fw-manager` as a test action, including `--auto-upgrade`, `--burn`, `--dry-run`, `--status`, and prompts. HLD §2.10. Kickoff exclusion.
- Image unit tests in HLD §3.2.
- Fast reboot. HLD §0.2.
- Warm reboot until the platform supports it. HLD §1.6.
- `config reload` as a firmware trigger. It does not burn.
- GA `cpoutil` path. HLD §0.3.
- ELS firmware, SAI, platform API, YANG, gNMI, and SONiC counters. HLD §2.5, §2.11.
- Template area 12 (security / malformed input). HLD §4 and §2.7. No new network API and no SONiC counters. Scale and logging are in this plan.
- Mid-burn power cut. Recovery is operator `--burn`, which this plan does not call.
- SimX and KVM. HLD §2.13.

## References

- HLD linked above, commit `e43e25e6c90b09972c11062ef372c0a127f5f125`.
- `ngts/cli_wrappers/sonic/sonic_general_clis.py` `deploy_image`, called from `ngts/tests/push_build_tests/conftest.py`.
- `ngts/cli_wrappers/sonic/sonic_onie_clis.py` `install_image`.
- `tests/common/helpers/upgrade_helpers.py` `install_sonic`, `check_services`, `check_sonic_version`.
- `tests/upgrade_path/test_upgrade_path.py` `test_upgrade_path`.
- `ngts/tests/nightly/sanity_checker/test_sanity_checker.py` `get_component_versions.py`.
- `tests/common/devices/sonic.py` `num_asics`.

## Testbed and topology

Any physical DUT topology the existing install test already uses. Documentation only. No VS-only topology. No traffic generator.

## Prerequisites / setup

- CPO positive cases: Chameleon6S or another CPO-capable SPC6. Skip the CPO cases otherwise.
- Non-CPO case: one of SPC1–SPC5, BlueField, or SN2201.
- Two images supplied by the run (the HLD does not name the URLs): one whose combined MFA changes only OE firmware, one with no firmware delta.
- Images staged on the controller before the suite, so a case does not download during the measured window.
- DUT shell as `admin`. Commands that write the marker use `sudo`.

### Feature readiness gate

TC-PRE-01 runs once per module. If it skips, CPO cases skip. TC-PLAT-01 still runs on a non-CPO DUT.

## Module prerequisites

| Step | Scope | Used by |
|------|-------|---------|
| TC-PRE-01 readiness gate | module | all CPO cases |
| Stage both images on the controller | module | TC-SONIC-01, TC-POLICY-01, TC-ONIE-01 |
| Each install row reads `OE_FW` immediately before it installs | function | TC-SONIC-01, TC-POLICY-01, TC-ONIE-01 |
| Save that row's syslog and syncd-up seconds | function | TC-LOG-01, TC-ASIC-01, TC-PERF-01 read the TC-SONIC-01 saves. They do not install again |
| Remove `/host/fw_auto_upgrade_disabled` after the case | function | TC-POLICY-01 |

## Test cases

### Preconditions (mandatory)

DUT is reachable by the existing install harness. TC-PRE-01 has recorded syncd state and `show interfaces status`, unless the case is TC-PLAT-01. An install row does not reuse that version token. It runs `sudo get_component_versions.py` immediately before its own install and judges the result against that pre-state.

### TC-PRE-01 — CPO install baseline is recorded

**Priority: P0**

**Goal:** Record optical-engine firmware before any install in this suite.

**Steps:**

1. On the DUT shell run `show version` and `sudo get_component_versions.py` (`ngts/tests/nightly/sanity_checker/test_sanity_checker.py`).
2. Skip the CPO suite unless the platform is Chameleon6S or a CPO-capable SPC6. HLD §2.13. A non-CPO DUT runs TC-PLAT-01 only.
3. Skip on SimX or KVM. HLD §2.13.
4. Record the `OE_FW` line, `docker ps` (syncd), and `show interfaces status`.

**Pass:** The script prints an `OE_FW` row whose `COMPILATION` cell is `-` and whose `ACTUAL` cell is a non-empty version. `docker ps` shows syncd `Up`.

**Cleanup:** None.

### TC-SONIC-01 — SONiC install converges OE firmware

**Priority: P1**

**Goal:** A SONiC-to-SONiC install leaves OE firmware at the image result.

Run the no-delta row first, then the oe-delta row. Each row reads its own pre-state.

| Row | Image | `OE_FW` `ACTUAL` after reboot | Syslog (HLD §2.9 Table 1) |
|-----|-------|-------------------------------|---------------------------|
| no-delta | Image whose MFA matches the pre-state (reinstall the running image) | Equal to this row's pre-state | `Component up to date` |
| oe-delta | The other image, combined MFA changes only OE | Different from this row's pre-state | `Component upgrade started` and `Component upgrade completed` for `OE_FW` and for `ASIC_FW` |

**Steps:**

1. On the DUT shell run `sudo get_component_versions.py` and store `OE_FW` `ACTUAL` and `FW` `ACTUAL` as this row's pre-state.
2. Install the row's image with `deploy_image(..., deploy_type='sonic')` (`ngts/cli_wrappers/sonic/sonic_general_clis.py`, invoked from `ngts/tests/push_build_tests/conftest.py`). Community alternate: `install_sonic(duthost, image_url, tbinfo)` then the cold reboot in `upgrade_test_helper` (`tests/common/helpers/upgrade_helpers.py`, `tests/upgrade_path/test_upgrade_path.py`).
3. Record seconds from that reboot until `docker ps` shows syncd `Up`.
4. Run `sudo get_component_versions.py`, `show version`, and `show interfaces status`.
5. Copy `/var/log/syslog` and the syncd-up seconds. TC-LOG-01, TC-ASIC-01, and TC-PERF-01 read these copies.

**Pass:** `show version` is the installed image (`check_sonic_version` on the community path). `OE_FW` `COMPILATION` is `-`. `ACTUAL` matches the row against this row's pre-state. `FW` `ACTUAL` equals this row's pre-state. `docker ps` shows syncd `Up`. Every port that was oper up in TC-PRE-01 is oper up. Syslog contains the row's event text. The oe-delta copy also contains `Component upgrade completed` naming `ASIC_FW` (same version rewritten, QG-1).

**Cleanup:** None.

### TC-POLICY-01 — Disabled policy survives SONiC install

**Priority: P1**

**Goal:** A pre-created policy file still suppresses OE burn after a SONiC install.

**Steps:**

1. On the DUT shell run `sudo get_component_versions.py` and store `OE_FW` `ACTUAL` as this case's pre-state.
2. Run `sudo touch /host/fw_auto_upgrade_disabled` and `sudo chmod 0644 /host/fw_auto_upgrade_disabled`. Do not call `mlnx-fw-manager`. HLD §2.3.1.
3. Install the image whose MFA differs from that pre-state, using the same SONiC-to-SONiC entry as TC-SONIC-01.
4. After reboot run `test -f /host/fw_auto_upgrade_disabled`, `sudo get_component_versions.py`, and `docker ps`.
5. Keep `/var/log/syslog` with this case's record. TC-LOG-01 does not read it; this case already checks the policy warning.

**Pass:** `test -f` succeeds. `OE_FW` `ACTUAL` equals this case's pre-state, so the running firmware stays different from the installed image. Syslog contains `Auto firmware upgrade skipped — policy disabled`. `docker ps` shows syncd `Up`. This is the intentional mismatch AF-9 describes.

**Cleanup:** `sudo rm -f /host/fw_auto_upgrade_disabled`.

### TC-LOG-01 — Install syslog records OE result

**Priority: P1**

**Goal:** The install logs name the auto-flow events the install cases do not already require.

**Steps:**

1. Read the syslog copy saved by the oe-delta row of TC-SONIC-01. No extra install.
2. Search for `Firmware manager started` and `Firmware manager finished`, and for a per-ASIC line that shows current and available versions (HLD §2.9 Table 1).

**Pass:** The copy contains the literals `Firmware manager started` and `Firmware manager finished`. It also contains the HLD §2.9 Table 1 event for per-ASIC per-component versions, with a current value and an available value on that line. Do not re-check `Component upgrade completed` or the policy-disabled warning here; TC-SONIC-01 and TC-POLICY-01 already require those.

**Cleanup:** None.

### TC-ONIE-01 — ONIE install converges OE firmware

**Priority: P2**

**Goal:** ONIE install activates the image OE firmware.

| Row | Marker before install | Marker after boot | `OE_FW` `ACTUAL` |
|-----|----------------------|-------------------|------------------|
| clear | Absent | Absent | Image running-bank version |
| wipe | File created as in TC-POLICY-01 | Absent | Image running-bank version |

**Steps:**

1. Run `sudo get_component_versions.py` and store `OE_FW` `ACTUAL` as this row's pre-state.
2. For the wipe row only, create `/host/fw_auto_upgrade_disabled` the same way as TC-POLICY-01.
3. Install the image whose MFA differs from that pre-state with `SonicOnieCli.install_image(image_path)`, which runs `onie-nos-install` (`ngts/cli_wrappers/sonic/sonic_onie_clis.py`).
4. After boot run `test -f /host/fw_auto_upgrade_disabled`, `sudo get_component_versions.py`, `docker ps`, and `show interfaces status`.

**Pass:** `test -f` fails on both rows. `OE_FW` `COMPILATION` is `-` and `ACTUAL` differs from this row's pre-state. `docker ps` shows syncd `Up`. Ports that were oper up in TC-PRE-01 are oper up.

**Cleanup:** None. ONIE already removed the marker.

### TC-ASIC-01 — Install burns once per ASIC

**Priority: P2**

**Goal:** A multi-ASIC install burns optical-engine firmware once per ASIC.

**Steps:**

1. Skip when `num_asics` is 1 (`tests/common/devices/sonic.py`).
2. Read the syslog copy saved by the oe-delta row of TC-SONIC-01. Do not install again.
3. Count lines that contain both `Component upgrade completed` and `OE_FW` (HLD §2.9 Table 1).

**Pass:** The copy does not contain `OE_FW left non-uniform across ASICs` (HLD §2.9 Table 3). Whether one `Component upgrade completed` line exists per ASIC is `[TBD — per-ASIC log line shape requires DUT confirmation]`. Do not treat a line count as a failure until a DUT sample shows that shape. The count must not be compared to the CPO front-panel port count.

**Cleanup:** None.

### TC-PLAT-01 — Non-CPO install ignores OE

**Priority: P2**

**Goal:** A non-CPO install does not add an OE firmware row.

**Steps:**

1. Skip unless the DUT is SPC1–SPC5, BlueField, or SN2201.
2. Run that platform's existing SONiC-to-SONiC or ONIE install (`deploy_type` `sonic` or `onie`).
3. Run `sudo get_component_versions.py` and `docker ps`.

**Pass:** `OE_FW` `ACTUAL` is `N/A` (HLD §3.2). Syslog has no `Component upgrade completed` line naming `OE_FW`. `docker ps` shows syncd `Up`. The existing post-install checks of that flow pass.

**Cleanup:** None.

### TC-PERF-01 — OE burn extends install reboot

**Priority: P2**

**Goal:** Install reboot reaches syncd inside the HLD's published samples.

**Steps:**

1. Skip unless the DUT is 1-ASIC Chameleon6S and TC-SONIC-01 saved both intervals.
2. Read the syncd-up seconds saved by the no-delta row and the oe-delta row. Do not install again. Do not add ping or a traffic generator.

**Pass:** No-delta interval ≤ 89 seconds. OE-delta interval ≤ 209 seconds. Both numbers are the HLD §1.5 reboot-to-ping samples for 1-ASIC Chameleon6S, applied here to syncd-up.

**Cleanup:** None.

### TC-FAIL-01 — Partial ASIC failure is logged

**Priority: P2**

**Goal:** A burn that fails on one ASIC is logged as an error.

**Steps:**

1. Skip until a DUT method exists. Injection is `[TBD — failure injection method requires DUT confirmation]`.
2. After the install reboot, run `sudo get_component_versions.py` and read syslog.

**Pass:** Syslog contains `Partial ASIC burn failure` at ERROR (HLD §2.9 Table 1, §1.7). The run is not reported as every component up to date.

**Cleanup:** Restore the DUT with the lab image using the same SONiC install path. Do not call `mlnx-fw-manager --burn`.

## Conventions

- Commands run in the DUT shell over the existing install-test SSH session, user `admin`.
- Version oracle: `sudo get_component_versions.py`.
- Service oracle: `docker ps` shows syncd `Up`. HLD manual plan item 12.
- Port oracle: `show interfaces status`. Compare with TC-PRE-01. No new traffic.
- Policy oracle: `test -f /host/fw_auto_upgrade_disabled`.
- Log oracle: event strings in HLD §2.9 Table 1, searched in `/var/log/syslog`.
- Install entry points are the functions cited in References. This plan does not add a firmware-manager command.

## Known limitations

- Warm reboot is not supported yet. HLD §1.6. Fast reboot is out of scope. HLD §0.2.
- `config reload` does not burn firmware.
- ONIE `onie-nos-install` and `onie-uninstall` reformat `/host` and clear the policy file. ONIE self-update does not. HLD §2.13.
- `COMPILATION` for `OE_FW` is `-`. Quality-guarantee item 4a disagrees; AF-10 and §2.6.1 are authoritative.
- Version compare ignores the middle field. HLD open question (`95.10.0752` vs `95.2020.0752`).
- Image URLs are not in the HLD. The run supplies the pair (the HLD does not name the URLs).
- These Table 1 events are not injected: `OE_FW` absent from the MFA, `OE_FW` unreadable or corrupt, and version-query retry or failure. The image pair is a valid combined MFA, and no install-path injection is specified.
- AF-4 (firmware control and software control behave the same) is not a separate case. The install path does not select that mode.
- Single-ASIC DUT skips TC-ASIC-01 (no chassis is named).
- Partial-burn injection is not specified (no injection method is specified). TC-FAIL-01 stays skipped until a method is confirmed.
- Bank repair after a failed burn is operator `--burn`, which is out of scope.
- SimX and KVM skip. HLD §2.13.
- Timing caps are the HLD ping samples applied to syncd-up, because the test environment was not specified and this plan does not add ping.
- Manual-plan item 18 disagrees with §2.10.3. Direct `--burn` is out of scope, so the plan does not pick a winner in a case.
- Non-CPO `get_component_versions.py` prints `OE_FW` `ACTUAL` as `N/A` (HLD §3.2). Manual plan item 5 says the manager prints no `OE_FW` row. This plan calls the component script, so the pass string is `N/A`.
- No platform API. HLD §2.5. Nothing to map under `tests/common/helpers/platform_api/`.
- Keyword joins to QoS, packet trimming, tunnel QoS, WRED/ECN, SRv6, telemetry, gNMI, SNMP, transceiver, thermal control, SED password management, generic config updater, and platform tests do not share a header, CONFIG_DB table, or management API with this feature.
- CLI rejection, enable/disable churn, and daemon CONFIG_DB replay are unit-tested or do not apply: there is no CONFIG_DB schema (HLD §2.11), and the plan does not call `mlnx-fw-manager`.
- Port admin toggle does not apply. OE firmware is ASIC flash, not a port object (AF-12).

## Open / action items

- Name the oe-delta and no-delta image URLs. The HLD does not.
- Name a partial-ASIC failure injection that does not call `mlnx-fw-manager`.
- Name the multi-ASIC CPO chassis for TC-ASIC-01.
- Confirm whether syncd-up on 1-ASIC Chameleon6S is inside 89s and 209s, or whether those samples must stay tied to ping.
- HLD conflict: quality-guarantee item 4a vs AF-10. This plan follows AF-10.

## Future automation

| TC | Proposed test | Existing code to call |
|----|---------------|------------------------|
| TC-PRE-01 — CPO install baseline is recorded | `test_cpo_install_baseline_recorded` | `get_component_versions.py` as in `test_sanity_checker.py` |
| TC-SONIC-01 — SONiC install converges OE firmware | `test_sonic_install_converges_oe_firmware` | `deploy_image(deploy_type='sonic')` or `install_sonic` |
| TC-POLICY-01 — Disabled policy survives SONiC install | `test_disabled_policy_survives_sonic_install` | same install helper, plus the marker file |
| TC-LOG-01 — Install syslog records OE result | `test_install_syslog_records_oe_result` | syslog scan patterned on `test_log_analyzer_errors_during_deploy_sonic.py` |
| TC-ONIE-01 — ONIE install converges OE firmware | `test_onie_install_converges_oe_firmware` | `SonicOnieCli.install_image` |
| TC-ASIC-01 — Install burns once per ASIC | `test_install_burns_once_per_asic` | `num_asics` plus the SONiC install helper |
| TC-PLAT-01 — Non-CPO install ignores OE | `test_non_cpo_install_ignores_oe` | existing `deploy_type` `sonic` or `onie` |
| TC-PERF-01 — OE burn extends install reboot | `test_oe_burn_extends_install_reboot` | timing approach of `test_startup_time_degradation` |
| TC-FAIL-01 — Partial ASIC failure is logged | `test_partial_asic_failure_logged` | no helper until a failure-injection method is named |

## Unmapped pytest

These tests install or time a reboot and do not assert `OE_FW`. They stay the baseline; they are not new TCs:

- `test_upgrade_path`, `test_double_upgrade_path`, `test_upgrade_path_t2`, `test_upgrade_path_t2_delayed`
- `test_deploy_sonic_image`
- `test_startup_time_degradation`
- `test_check_errors_in_log_during_deploy_sonic_image`
- `test_validate_config_db_json_during_upgrade`

No pytest in this repo asserts CPO `OE_FW` after an install.

## Unmapped helpers

No OE firmware function exists under `tests/common/helpers/platform_api/`. HLD §2.5 says the platform API is unchanged.

## Edge-case checklist

| Category | Decision |
|----------|----------|
| Absent policy file | Covered by TC-SONIC-01 and TC-ONIE-01 clear row |
| Policy file present | Covered by TC-POLICY-01 and TC-ONIE-01 wipe row |
| No-op / versions already match | TC-SONIC-01 no-delta row |
| Scale / one ASIC vs many | TC-ASIC-01; single-ASIC skip in Known limitations |
| Partial failure | TC-FAIL-01, injection TBD |
| All affected entities | One `OE_FW` ACTUAL; non-uniform warning must be absent |
| Persistence across SONiC install | TC-POLICY-01 |
| Persistence across ONIE | TC-ONIE-01 wipe row |
| Boundary CLI values | Out of scope. Direct CLI is excluded and unit-tested (HLD §3.2) |
| Malformed packets | N/A. No data plane |
| Port admin toggle | Waived. Not a port feature (AF-12) |
| Daemon CONFIG_DB replay | Waived. No CONFIG_DB (HLD §2.11). Syncd start is a pass check |

## Reboot scope

| Reboot | Decision | HLD |
|--------|----------|-----|
| Cold reboot after SONiC install | In scope. It is the install path | AF-2, §2.3 |
| Cold reboot after ONIE install | In scope | §2.13 |
| Config reload | Out of scope. Does not burn | §2.11 |
| Fast reboot | Out of scope | §0.2 |
| Warm reboot | Out of scope until supported | §1.6 |
| syncd / container restart as a trigger | Out of scope. Syncd must start after install; that is a pass check, not a separate reboot case | AF-9 |

## Firmware checklist

| Check | Where |
|-------|-------|
| Install vs field update | Install only. Field `--burn` is out of scope |
| Flavor | Combined MFA that changes only OE, and a no-delta image |
| Post-upgrade power cycle | The reboot the install flow already performs |
| API rollback | No platform API. Cleanup is another install, not `--burn` |

## Sibling plans

`docs/testplan/nvidia-cpo-fw-upgrade/` has no earlier plan. This test plan is the first file in that directory's design set.

## Execution budget

| Tier | Cases | Estimate |
|------|-------|----------|
| P0 | TC-PRE-01 | 2 min. No install |
| P1 | TC-SONIC-01 (two local images), TC-POLICY-01, TC-LOG-01 | 25 min. Images already on the controller. Each install reboot is the HLD sample, not a download |
| P2 | TC-ONIE-01, TC-ASIC-01, TC-PLAT-01, TC-PERF-01, TC-FAIL-01 | Weekly. ONIE and the non-CPO install are the extra reboots. TC-ASIC-01 and TC-PERF-01 only read TC-SONIC-01 saves. TC-FAIL-01 adds none until injection exists |

P0 stays under 10 minutes. P0+P1 stays under 30 minutes when images are local. The weekly total exceeds 60 minutes because the feature runs only as part of an install reboot. There is no shorter stimulus.
