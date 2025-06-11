
# DASH ENI Based Forwarding test plan

* [Overview](#Overview)
   * [Scope](#Scope)
   * [Testbed](#Testbed)
   * [Setup configuration](#Setup%20configuration)
* [Test](#Test)
* [Test cases](#Test%20cases)
* [TODO](#TODO)
* [Open questions](#Open%20questions)

## Overview
Feature HLD: https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/high-availability/eni-based-forwarding.md  
  
### Scope
There are [2 phases](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/high-availability/eni-based-forwarding.md?plain=1#L102-L115) for the ENI Based Forwarding feature.
Currently we are focusing on phase1 only.

The full tests for ENI Based Forwarding feature include three parts:
1. Migrate existing Private Link tests to use ENI Forwarding Approach. Until HaMgrd is available, test should write configuration to the DASH_ENI_FORWARD_TABLE.
2. Add individual test cases which verify forwarding to remote endpoint and also Tunnel Termination. This should not require HA availability.
3. HA test cases should work by just writing the expected configuration to DASH_ENI_FORWARD_TABLE. **This is not in the scope of this test plan.**

The configration is not persistent, it disappears after reload/reboot. So, the reload/reboot test is not in the scope.

### Testbed
The test will run on a single dut Smartswitch testbed.

### Setup configuration
Until HaMgrd is available, we can only write configuration to the DASH_ENI_FORWARD_TABLE.  
DASH_ENI_FORWARD_TABLE schema: https://github.com/r12f/SONiC/blob/user/r12f/ha2/doc/smart-switch/high-availability/smart-switch-ha-detailed-design.md#2321-dash_eni_forward_table  

Common tests configuration:
- Test will be based on the basic PL link configuration 

Common tests cleanup:
- Remove the basic PL link configuration

The configuration for DASH_ENI_FORWARD_TABLE is applied via swssconfig in json format.
Configuration example for the DASH_ENI_FORWARD_TABLE:
```
[​
    {​
        "DASH_ENI_FORWARD_TABLE:Vnet1": {},​
        "OP": "SET"​
    }​,
    {​
        "DASH_ENI_FORWARD_TABLE:497f23d7-f0ac-4c99-a98f-59b470e8c7bd":
        {
            "vdpu_ids": ["vdpu_id1", "vdpu_id2"],
            "primary_vdpu": "vdpu_id1",
            "outbound_vni": "1000",
            "outbound_eni_mac_lookup": ""
        },​
        "OP": "SET"​
    }​
]​
```

## Test
### Test case # 1 – test_privatelink_basic_transform migrate to ENI based fowarding
#### Test objective
This is the basic test for PL inbound and outbound packets validation. Migrate this test case to ENI based fowarding.
#### Test steps
* Update the APPLIANCE_VIP to the NPU VIP(switch Loopback0 IP).
* Update the outer IP dst of the inbound/outbound sent packets to the NPU VIP.
* Add the configuration for DASH_ENI_FORWARD_TABLE according to the existing dash config.  
* Add a step to check the ACL rules, there should be an flag to enable this check. It's enabled by default.
  * Check the ACL rules for the tested ENI are generated: totally 4 rules - 2 (inbound and outbound) * 2 (with/without Tunnel Termination)
  * Check the ACL rules are correct.
* Keep the other steps unchanged.

### Test case # 2 – test_privatelink_standby_eni_encap
#### Test objective
This is to validate when the PL packets land on NPU which has the currrent ENI as standby ENI, the packets should be double encaped and sent to the NPU-NPU tunnel.
#### Test steps
* Apply the basic PL dash configrations which is migrated to ENI based forwarding.
* Apply the config for the NPU-NPU tunnel.(how?)
* Change the tested ENI to standby on the dut.(how?)
* Send inbound/outbound packets with dst IP of NPU VIP
* Check the packet is sent out through the tunnel.
* Check the received packets has double encaped vxlan header and the src mac/ip are the dut and the dst mac/ip are the HA peer NPU.
* Check the tunnel termination flag is set in the out most vxlan header.
* Check the inner inbound/outbound packets are not changed.

### Test case # 3 – test_privatelink_tunnel_termination
#### Test objective
This is to validate when the double encaped PL packets land on NPU, the tunnel is terminated, and packets are decaped and sent to the local nexthop(DPU).
#### Test steps
* Apply the basic PL dash configrations which is migrated to ENI based forwarding.
* Apply the config for the NPU-NPU tunnel.(how?)
* Set the tested ENI to active on the dut.(how?)
* Send double encaped inbound/outbound packets to the NPU.
* The dst IP of the original PL outer header should be NPU VIP.
* The dst mac/ip of the out most vxlan header should be the dut, the tunnel termination flag should be set.
* Check the inbound/outbound packets are fowarded by the dpu and can be received by ptf.
* Check the received packets are as expected after PL transform.

## TODO


## Open questions
