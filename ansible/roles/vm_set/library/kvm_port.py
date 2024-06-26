#!/usr/bin/python

import re
import subprocess
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
module: kvm_port
version_added: "0.1"
author: Guohan Lu (gulv@microsoft.com)
short_description: Gather management and front panel ports from KVM-based DUT
'''

EXAMPLES = '''
- name: Get front panel and mgmt port for kvm vm
  kvm_port:
    vmname: "{{ dut_name }}"
'''


def main():

    module = AnsibleModule(argument_spec=dict(
        vmname=dict(required=True),
    ))

    vmname = module.params['vmname']

    try:
        output = subprocess.check_output(
            "virsh domiflist %s" % vmname,
            env={"LIBVIRT_DEFAULT_URI": "qemu:///system"},
            shell=True).decode('utf-8')
    except subprocess.CalledProcessError:
        module.fail_json(msg="failed to iflist dom %s" % vmname)

    mgmt_port = None
    fp_ports = {}
    cur_fp_idx = 0

    for msg in output.split('\n'):
        fds = re.split(r'\s+', msg.lstrip())
        if len(fds) != 5:
            continue
        if fds[1] == "ethernet":
            if mgmt_port is None:
                mgmt_port = fds[0]
            else:
                fp_ports[cur_fp_idx] = fds[0]
                cur_fp_idx = cur_fp_idx + 1

    if mgmt_port is None:
        module.fail_json(msg="failed to find mgmt port")

    module.exit_json(changed=False, ansible_facts={
                     'dut_mgmt_port': mgmt_port, 'dut_fp_ports': fp_ports})


if __name__ == "__main__":
    main()
