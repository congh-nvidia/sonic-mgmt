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

### Testbed
The test will run only on smartswitch testbeds.

### Setup configuration
No setup pre-configuration is required, the test will configure and clean up all the configuration.

Common tests configuration:
- Apply Private link configuration on DPU0 with ENI0.
- The flags for pa validation should all be set to true.
- Apply the IP addresses on the data ports and static routes for the switch and DPUs.

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

### Test case # 3 – PA validation multi DPU
#### Test objective
Verify there is no conflict of pa validation among multiple DPUs.
#### Test steps
* Apply the same Private link configuration on DPU1 with ENI1, but the pa validation flag is set to false.
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 3 – ENI
#### Test objective
Verify "ENI" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("percentage", "used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 4 – ENI Ethernet Addresses
#### Test objective
Verify "ENI Ethernet Addresses" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 5 – IPv4 Inbound Routes
#### Test objective
Verify "IPv4 Inbound Routes" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 6 – IPv6 Inbound Routes
#### Test objective
Verify "IPv6 Inbound Routes" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 7 – IPv4 Outbound Routes
#### Test objective
Verify "IPv4 Outbound Routes" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 8 – IPv6 Outbound Routes
#### Test objective
Verify "IPv6 Outbound Routes" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 9 – IPv4 Outbound CA to PA
#### Test objective
Verify "IPv4 Outbound CA to PA" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 10 – IPv6 Outbound CA to PA
#### Test objective
Verify "IPv6 Outbound CA to PA" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 11 – IPv4 PA Validation
#### Test objective
Verify "IPv4 PA Validation" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 12 – IPv6 PA Validation
#### Test objective
Verify "IPv6 PA Validation" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 13 – IPV4 ACL Groups
#### Test objective
Verify "IPV4 ACL Groups" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 14 – IPV6 ACL Groups
#### Test objective
Verify "IPV6 ACL Groups" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 15 – IPv4 ACL Rules
#### Test objective
Verify "IPv4 ACL Rules" CRM resource.
#### Test steps
* Set polling interval to 1 sec.
* Configure 1 "IPv4 ACL Rules" and observe that counters were updated as expected.
* Remove 1 "IPv4 ACL Rules" and observe that counters were updated as expected.
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).
* Restore default configuration.

### Test case # 16 – IPv6 ACL Rules
#### Test objective
Verify "IPv6 ACL Rules" CRM resource.
#### Test steps
* Check CRM resources used/available
* Perform the following steps for all threshold types ("used", "free"):
	* Set low and high thresholds according to current usage and type.
	* Verify that "EXCEEDED" message is logged (using log analyzer).
	* Set low and high thresholds to default values.
	* Verify that "CLEAR" message is logged (using log analyzer).

### Test case # 17 – Cleanup
#### Test objective
Verify cleanup for CRM resources.
#### Test steps
* Remove CRM resources by applying swss config
* Check CRM resources used/available

## TODO

## Open questions
