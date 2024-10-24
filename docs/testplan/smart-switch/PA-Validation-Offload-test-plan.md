# SmartSwitch PA Validation Offload test plan

* [Overview](#Overview)
   * [Scope](#Scope)
   * [Testbed](#Testbed)
   * [Setup configuration](#Setup%20configuration)
* [Test](#Test)
* [Test cases](#Test%20cases)
* [TODO](#TODO)
* [Open questions](#Open%20questions)

## Overview
The purpose is to test the functionality of PA Validation offload feature on the SONIC SmartSwitch DUT.

Feature HLD: https://github.com/Yakiv-Huryk/SONiC/blob/pa_validation_offload_update/doc/smart-switch/PA-Validation/SmartSwitchPAValidationOffload.md

### Scope
Currently, there is already an implicit pa validation in the DASH pipeline for the inbound traffic, which is handled in the DPU. This will keep the same as it is and the verification is covered by the DASH vnet-to-vent test, which is not in scope of this test plan.
The pa validation offload feature will support the validation for traffic of all directions(inbound and outbound), and the validation is done on the switch side.
This test is targeting to verify the outbound pa validation offload functionality works as expected.
No scale and performance tests.

### Testbed
The test will run only on smartswitch testbeds.

### Setup configuration
No setup pre-configuration is required, the test will configure and clean up all the configuration.

Common tests configuration:
- Apply the data ports IP addresses and static routes for the switch and DPUs.
- Apply Private link configuration on DPU0 with ENI0.

Common tests cleanup:
- IP addresses and static routes.
- All dash configurations on DPU0 and DPU1.

## Test

## Test cases
### Test case # 1 – PA validation single DPU
#### Test objective
Verify PA validation and offloading works on a single DPU.
#### Test steps
* Check on the switch that there is already an egress ACL table attached to the DPU0 port and contains the rules for pa validation.
* Send the ENI0 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Verify the packet is received by the ptf.
* Send 1000 ENI0 outbound packets with unmatched underlay source IP address from ptf to the smartswitch.
* Verify no packet is received by the ptf.
* Check the TX drop counter of the NPU-DPU data port for DPU0, it should increase by 1000.
* Add a new pa validation entry for the unmatched source IP address.
* Check a new ACL rule is added to the egress ACL table to allow the unmatched source IP.
* Send the unmatched packet again.
* Verify the packet is received by the ptf.
* Remove the newly added pa validation entry.
* Check the the new ACL rule is removed.
* Send the matched and unmatched packets again.
* Verify the pa matched packet is received by the ptf.
* Verify the pa unmatched packet is not received by the ptf.

### Test case # 2 – PA validation multiple DPUs
#### Test objective
Verify there is no conflict of pa validation configurations among multiple DPUs.
#### Test steps
* Apply the same Private link configuration as DPU0 on DPU1 only with a different ENI - ENI1.
* Send the ENI0 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Verify the packets of ENI0 and ENI1 are both received by the ptf.
* Send the ENI0 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Verify no packet is received by the ptf.
* Add a new pa validation entry for the unmatched source IP address on DPU1. 
* Send the ENI0 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Verify no packet of ENI0 is received by the ptf.
* Verify the packet of ENI1 is received by the ptf.
* Remove the newly added pa validation entry on DPU1.
* Add the same pavalidation entry on DPU0.
* Send the ENI0 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Verify the forwarded packet of ENI0 is received by the ptf.
* Verify no packet of ENI1 is received by the ptf.
* Restore the configuration.
  
### Test case # 3 – PA validation DPU shutdown
#### Test objective
Verify the pa validation config is removed when the dpu is shutdown.
#### Test steps
* Check the egress ACL table and rules for DPU0, there should be the rules for the pa validation.
* Shutdown the dpu.
* Check the egress ACL table and the rules are removed.
* Restart the dpu and wait for it to boot up.
* Check there is no new ACL table and rules added.

## TODO

## Open questions
