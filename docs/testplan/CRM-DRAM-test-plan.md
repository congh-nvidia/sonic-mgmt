# CRM DRAM test plan

* [Overview](#Overview)
   * [Scope](#Scope)
   * [Testbed](#Testbed)
* [Setup configuration](#Setup)
* [Test](#Test)
* [Test cases](#Test)
* [TODO](#TODO)

## Overview
The purpose is to test functionality of CRM for DRAM on the SONiC switch or standalone DPU DUTs.

### Scope
The test is targeting on the DRAM resource in CRM.

### Testbed
The test is able to run on a SONiC switch testbed or a standalone DPU testbed.

## Setup configuration
No setup pre-configuration is required, test will configure and clean-up all the configuration.

## Test

## Test cases

### Test case # 1 – CRM DRAM counters
#### Test objective
Verify "DRAM" CRM resource counters.
#### Test steps
* Set polling interval to 1 second.
* Record the DRAM used/available CRM counters.
* Allocate memory by creating a file in the size of 50% of the free memory(not more than 1GB) in /dev/shm.
* Check the used counter is increased by the file size.
* Check the available counter is decreased by the file size.
* Free the memory by removing the file.
* Check the available counter is increased by the file size.
* Check the used counter is decreased by by the file size.
* Since we have background processes may be allocating/freeing memory during the test, set a 10% tolerance for all the counter checks.
* Restore the polling interval to default.

### Test case # 2 – CRM DRAM thresholds
#### Test objective
Verify "DRAM" CRM resource thresholds.
#### Test steps
* Set polling interval to 1 second.
* Check the default threshold is low 70%, high 85%.
* Get the current the DRAM used/available CRM counters.
* Perform the following steps for all threshold types ("percentage", "used", "free"):
  * Set low and high thresholds according to current usage and type.
  * Verify that "EXCEEDED" message is logged (using log analyzer).
  * Set low and high thresholds to default values.
  * Verify that "CLEAR" message is logged (using log analyzer).
* Restore the polling interval to default.

## TODO
Need to support smartswith DPU duts when the test infra is ready.
