# Generic Hash Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| SONiC Generic Hash | [https://github.com/sonic-net/SONiC/doc/hash/hash-design.md]|


## Overview
The hashing algorithm is used to make traffic-forwarding decisions for traffic exiting the switch.
It makes hashing decisions based on values in various packet fields, as well as on the hash seed value.
The packet fields used by the hashing algorithm varies by the configuration on the switch.

For ECMP, the hashing algorithm determines how incoming traffic is forwarded to the next-hop device.
For LAG, the hashing algorithm determines how traffic is placed onto the LAG member links to manage
bandwidth by evenly load-balancing traffic across the outgoing links.

GH is a feature which allows user to configure which hash fields suppose to be used by hashing algorithm.
GH provides global switch hash configuration for ECMP and LAG.


## Requirements

#### The Generic Hash feature supports the following functionality:
1. Ethernet packet hashing configuration with inner/outer IP frames
2. Global switch hash configuration for ECMP and LAG
3. Warm/Fast reboot

#### This feature will support the following commands:

1. config: set switch hash global configuration
2. show: display switch hash global configuration

#### This feature will provide error handling for the next situations:

1. Frontend
  1.1 Invalid parameter value
2. Backend
  2.1 Missing parameters
  2.2 Invalid parameter value
  2.3 Parameter removal
  2.4 Configuration removal

### Scope

The test is to verify the hash configuration can be added/updated/removed by the generic hash, and the behavior of ECMP and lag hashing will change according to the generic hash config.   

### Scale / Performance

No scale or performance test related

### Related **DUT** CLI commands

#### Config
The following command can be used to configure generic hash:
```
config
|--- switch-hash
     |--- global
          |--- ecmp-hash ARGS
          |--- lag-hash ARGS
```

Examples:
The following command updates switch hash global:
```
config switch-hash global ecmp-hash \
'DST_MAC' \
'SRC_MAC' \
'ETHERTYPE' \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'INNER_DST_MAC' \
'INNER_SRC_MAC' \
'INNER_ETHERTYPE' \
'INNER_IP_PROTOCOL' \
'INNER_DST_IP' \
'INNER_SRC_IP' \
'INNER_L4_DST_PORT' \
'INNER_L4_SRC_PORT'
```
```
config switch-hash global lag-hash \
'DST_MAC' \
'SRC_MAC' \
'ETHERTYPE' \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'INNER_DST_MAC' \
'INNER_SRC_MAC' \
'INNER_ETHERTYPE' \
'INNER_IP_PROTOCOL' \
'INNER_DST_IP' \
'INNER_SRC_IP' \
'INNER_L4_DST_PORT' \
'INNER_L4_SRC_PORT'
```

#### Show
The following command shows switch hash global configuration:
```
show
|--- switch-hash
     |--- global
```
     
Example:
```
root@sonic:/home/admin# show switch-hash global
ECMP HASH          LAG HASH
-----------------  -----------------
DST_MAC            DST_MAC
SRC_MAC            SRC_MAC
ETHERTYPE          ETHERTYPE
IP_PROTOCOL        IP_PROTOCOL
DST_IP             DST_IP
SRC_IP             SRC_IP
L4_DST_PORT        L4_DST_PORT
L4_SRC_PORT        L4_SRC_PORT
INNER_DST_MAC      INNER_DST_MAC
INNER_SRC_MAC      INNER_SRC_MAC
INNER_ETHERTYPE    INNER_ETHERTYPE
INNER_IP_PROTOCOL  INNER_IP_PROTOCOL
INNER_DST_IP       INNER_DST_IP
INNER_SRC_IP       INNER_SRC_IP
INNER_L4_DST_PORT  INNER_L4_DST_PORT
INNER_L4_SRC_PORT  INNER_L4_SRC_PORT
```
### Related DUT configuration files

```
{
    "SWITCH_HASH": {
        "GLOBAL": {
            "ecmp_hash": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT"
            ],
            "lag_hash": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT"
            ]
        }
    }
}
```
### Supported topology
The test will be supported on any topology


## Test cases

### Test cases #1 - Verify the default hash fields are ip_proto, src_ip, dst_ip, src_l4_port, dst_l4_port, inner_src_ip, inner_dst_ip.
1. Get the default hash fields configration via cli "show switch-hash global"
2. Check the default ecmp and lag hash fields are ip_proto, src_ip, dst_ip, src_l4_port, dst_l4_port, inner_src_ip, inner_dst_ip.

### Test cases #2 - Verify when generic ecmp hash is configured, the traffic can be balanced accordingly.
1. The test is using the default links and routes in a community setup.
2. Randomly select a hash field and configure it to the ecmp hash list via cli "config switch-hash global ecmp-hash".
3. Configure the lag hash list to exclude the selected field in case the egress links are portchannels.
4. Send traffic with changing selected field from a downlink ptf to uplink destination via multiple nexthops.
5. Check the traffic is balanced between the nexthops.
6. If the uplinks are portchannels with multiple members, check the traffic is not balanced between the members.
7. Recover the hash configs to the default.

### Test cases #3 - Verify when generic lag hash is configured, the traffic can be balanced accordingly.
1. The test is using the default links and routes in a community setup and only runs on setups which have multi-member portchannel uplinks.
2. Randomly select a hash field and configure it to the lag hash list via cli "config switch-hash global lag-hash".
3. Configure the ecmp hash list to exclude the selected field.
4. Send traffic with changing selected field from a downlink ptf to uplink destination via the portchannels.
5. Check only one portchannel receives the traffic and the traffic is balanced between the members.
6. Recover the hash configs to the default.

### Test cases #4 - Verify when both generic ecmp/lag hash are configured with all the valid fields, the traffic can be balanced accordingly.
1. The test is using the default links and routes in a community setup.
2. Configure all the valid hash fields for the ecmp and lag hash.
3. Randomly select one hash field for the test.
4. Send traffic with changing selected field from a downlink ptf to uplink destination.
5. Check the traffc is balanced between all the egress physical ports.
6. Recover the hash configs to the default.

### Test cases #5 - Verify the generic hash cannot be configured seccessfully with invalid arguments.
1. Configure the ecmp/lag hash with invalid fields list arguments.
2. Check there is a cli error notify the user the the argument is invalid.
3. Check the running config is not changed.
4. The invalid arguments includes:
  a. empty argument
  b. single invalid field
  c. invalid field(s) combined with valid field(s)
5. Recover the hash configs to the default.

### Test cases #6 - Verify generic hash running configuration persists after fast/warm reboot.
1. The test is using the default links and routes in a community setup.
2. Configure all the valid hash fields for the ecmp and lag hash.
3. Randomly select one hash field for the test.
4. Send traffic with changing selected field from a downlink ptf to uplink destination.
5. Randomly do fast/warm reboot while sending the traffic.
6. After the reboot finished, check the traffc is balanced between all the egress physical ports.
7. Recover the hash configs to the default.
