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
  Invalid parameter value
2. Backend
  1. Missing parameters
  2. Invalid parameter value
  3. Parameter removal
  4. Configuration removal

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
show ip interfaces loopback-action 
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

### Test cases #1 - Verify when generic ecmp hash is configured, the traffic can be balanced accordingly.

### Test cases #2 - Verify when generic lag hash is configured, the traffic can be balanced accordingly.

### Test cases #3 - Verify when both generic ecmp/lag hash are configured, the traffic can be balanced accordingly.

### Test cases #4 - Verify the generic hash cannot be configured seccessfully with invalid arguments .

### Test cases #5 - Verify generic hash configuration persists after reboot(config reload, reboot, fast-reboot, warm-reboot).

