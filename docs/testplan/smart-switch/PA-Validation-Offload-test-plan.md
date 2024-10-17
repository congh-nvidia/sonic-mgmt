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
The purpose is to test the functionality of PA Validation offloading on the SONIC SmartSwitch DUT.
Feature HLD:

### Scope
For the inbound traffic, the pa validation is implicitly done by the DASH pipeline in DPU. The pa validation of inbound traffic is not offloaded to the NPU, and verification is covered by the DASH vnet-to-vent test, so it is not in scope of this test plan.
For the outbound traffic, the pa validation is offloaded to the switch. This test is targeting to verify the outbound pa validation works and the traffic is dropped on the switch NPU-DPU data port.
No scale and performance tests.

### Testbed
The test will run only on smartswitch testbeds.

### Setup configuration
No setup pre-configuration is required, the test will configure and clean up all the configuration.

Common tests configuration:
- Apply Private link configuration on DPU0 with ENI0.
- The flags for pa validation should all be set to true.
- Apply the data ports IP addresses and static routes for the switch and DPUs.

Common tests cleanup:
- All dash configurations on DPU0 and DPU1.

## Test

## Test cases
### Test case # 1 – PA validation offload enabled
#### Test objective
Verify PA validation offloading is enabled by default for all DPUs
#### Test steps
* Check the values of field pa_validation for all DPUs in DASH_OFFLOAD_STATE_TABLE, the values should be all True.
* Check the ACL table and rules added for the pa validation on the switch.

### Test case # 2 – PA validation single DPU
#### Test objective
Verify PA validation and offloading works on a single DPU
#### Test steps
* Send the ENI0 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Verify the forwarded packet is received by the ptf.
* Send 1000 ENI0 outbound packets with unmatched underlay source IP address from ptf to the smartswitch.
* Verify no packet is received by the ptf.
* Check the TX drop counter of the NPU-DPU data port for DPU0 increases by 1000.
* Add a new pa validation entry for the unmatched source IP address.
* Send the unmatched packet again.
* Verify the packet is received by the ptf.
* Remove the newly added pa validation entry.
* Send the unmatched packet again.
* Verify no packet is received by the ptf.

### Test case # 3 – PA validation multi DPU
#### Test objective
Verify there is no conflict of pa validation among multiple DPUs.
#### Test steps
* Apply the same Private link configuration on DPU1 with ENI1, but the pa validation flag is set to false.
* Send the ENI0 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with matched underlay source IP address from ptf to the smartswitch.
* Verify the forwarded packets are received by the ptf.
* Send the ENI0 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Verify no packet of ENI0 is received by the ptf.
* Verify the forwarded packet of ENI1 is received by the ptf.
* Set the pa_validation flag of ENI0 to false and the pa_validation flag of ENI1 to true.
* Send the ENI0 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Send the ENI1 outbound packet with unmatched underlay source IP address from ptf to the smartswitch.
* Verify the forwarded packet of ENI0 is received by the ptf.
* Verify no packet of ENI1 is received by the ptf.
* Restore the configuration.
  
### Test case # 4 – PA validation DPU reset
#### Test objective

#### Test steps
* 

## TODO

## Open questions
