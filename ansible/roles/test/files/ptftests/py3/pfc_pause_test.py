import datetime
import glob
import os
import random
import sys
import time

import ptf
import ptf.packet as scapy
import scapy as sc

from ptf.base_tests import BaseTest
from ptf.mask import Mask
from ptf.testutils import add_filter, reset_filters, dp_poll, simple_udp_packet, send_packet, test_params_get
import macsec  # noqa F401


def udp_filter(pkt_str):
    try:
        pkt = scapy.Ether(pkt_str)
        return scapy.UDP in pkt

    except Exception:
        return False


def capture_matched_packets(test, exp_packet, port, device_number=0, timeout=1):
    """
    Receive all packets on the port and return all the received packets.
    As soon as the packets stop arriving, the function waits for the timeout value and returns the received packets.
    Therefore, this function requires a positive timeout value.
    """
    if timeout <= 0:
        raise Exception("%s() requires positive timeout value." %
                        sys._getframe().f_code.co_name)

    pkts = list()
    while True:
        result = dp_poll(test, device_number=device_number,
                         port_number=port, timeout=timeout)
        if isinstance(result, test.dataplane.PollSuccess):
            if ptf.dataplane.match_exp_pkt(exp_packet, result.packet):
                pkts.append(result.packet)
        else:
            break

    return pkts


class PfcPauseTest(BaseTest):
    def __init__(self):
        BaseTest.__init__(self)
        self.test_params = test_params_get()

    def setUp(self):
        add_filter(udp_filter)
        self.dataplane = ptf.dataplane_instance
        self.pkt_count = int(self.test_params['pkt_count'])
        self.pkt_intvl = float(self.test_params['pkt_intvl'])
        self.port_src = int(self.test_params['port_src'])
        self.port_dst = self.test_params['port_dst']
        self.mac_src = self.dataplane.get_mac(0, self.port_src)
        self.mac_dst = self.dataplane.get_mac(0, self.port_dst)
        self.ip_src = self.test_params['ip_src']
        self.ip_dst = self.test_params['ip_dst']
        self.dscp = self.test_params['dscp']
        """ DSCP for background traffic """
        self.dscp_bg = self.test_params['dscp_bg']
        self.queue_paused = self.test_params['queue_paused']
        """ if DUT has MAC information """
        self.dut_has_mac = self.test_params['dut_has_mac']
        self.debug = self.test_params.get('debug', False)
        self.vlan_id = self.test_params.get('vlan_id', None)
        self.testbed_type = self.test_params.get('testbed_type', None)

    def construct_pkt(self, sport, dport):
        tos = self.dscp << 2
        tos_bg = self.dscp_bg << 2

        pkt_args = {
            'eth_dst': self.mac_dst,
            'eth_src': self.mac_src,
            'ip_src': self.ip_src,
            'ip_dst': self.ip_dst,
            'ip_tos': tos,
            'udp_sport': sport,
            'udp_dport': dport,
            'ip_ttl': 64
        }
        if self.vlan_id is not None:
            pkt_args['dl_vlan_enable'] = True
            pkt_args['vlan_vid'] = int(self.vlan_id)
            pkt_args['vlan_pcp'] = self.dscp
        pkt = simple_udp_packet(**pkt_args)

        pkt_bg_args = {
            'eth_dst': self.mac_dst,
            'eth_src': self.mac_src,
            'ip_src': self.ip_src,
            'ip_dst': self.ip_dst,
            'ip_tos': tos_bg,
            'udp_sport': sport,
            'udp_dport': dport,
            'ip_ttl': 64
        }
        if self.vlan_id is not None:
            pkt_bg_args['dl_vlan_enable'] = True
            pkt_bg_args['vlan_vid'] = int(self.vlan_id)
            pkt_bg_args['vlan_pcp'] = self.dscp_bg
        pkt_bg = simple_udp_packet(**pkt_bg_args)

        exp_pkt_args = {
            'ip_src': self.ip_src,
            'ip_dst': self.ip_dst,
            'ip_tos': tos_bg,
            'udp_sport': sport,
            'udp_dport': dport,
            'ip_ttl': 63
        }
        if self.vlan_id is not None:
            exp_pkt_args['dl_vlan_enable'] = True
            exp_pkt_args['vlan_vid'] = int(self.vlan_id)
            exp_pkt_args['vlan_pcp'] = self.dscp_bg
        exp_pkt = simple_udp_packet(**exp_pkt_args)

        masked_exp_pkt = Mask(exp_pkt)
        masked_exp_pkt.set_do_not_care_scapy(scapy.Ether, "src")
        masked_exp_pkt.set_do_not_care_scapy(scapy.Ether, "dst")
        masked_exp_pkt.set_do_not_care_scapy(scapy.IP, "ttl")
        masked_exp_pkt.set_do_not_care_scapy(scapy.IP, "chksum")
        masked_exp_pkt.set_do_not_care_scapy(scapy.IP, "tos")
        if 'backend' in self.testbed_type:
            masked_exp_pkt.set_do_not_care_scapy(scapy.Dot1Q, "prio")

        return pkt, pkt_bg, masked_exp_pkt

    def populate_fdb(self):
        pkt_args = {
            'eth_dst': self.mac_dst,
            'eth_src': self.mac_src,
            'ip_src': self.ip_src,
            'ip_dst': self.ip_dst
        }
        if self.vlan_id is not None:
            pkt_args['dl_vlan_enable'] = True
            pkt_args['vlan_vid'] = int(self.vlan_id)
            pkt_args['vlan_pcp'] = 0

        pkt = simple_udp_packet(**pkt_args)

        send_packet(self, self.port_src, pkt, 5)

        pkt_args['eth_dst'] = self.mac_src
        pkt_args['eth_src'] = self.mac_dst
        pkt_args['ip_src'] = self.ip_dst
        pkt_args['ip_dst'] = self.ip_src

        pkt = simple_udp_packet(**pkt_args)

        send_packet(self, self.port_dst, pkt, 5)

    def runTest(self):
        tos_bg = self.dscp_bg << 2
        pass_cnt = 0
        if self.debug:
            # remove previous debug files
            files = glob.glob("/tmp/pfc_pause_{}*".format(self.dscp))
            for file in files:
                os.remove(file)
            current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            log_file = open(
                "/tmp/pfc_pause_{}_{}".format(self.dscp, current_time), "w")
        """ If DUT needs to learn MAC addresses """
        if not self.dut_has_mac:
            self.populate_fdb()

        for x in range(self.pkt_count):
            sport = random.randint(0, 65535)
            dport = random.randint(0, 65535)

            pkt, pkt_bg, masked_exp_pkt = self.construct_pkt(sport, dport)
            send_packet(self, self.port_src, pkt, 1)
            send_packet(self, self.port_src, pkt_bg, 1)

            pkts = capture_matched_packets(self, masked_exp_pkt, self.port_dst)

            if self.debug:
                for i, pkt in enumerate(pkts):
                    dump_msg = "Iteration {}:\n Pkt num {}:\n Hex dump: {}\n\n".format(
                        x, i, sc.utils.hexstr(pkt))
                    log_file.write(dump_msg)

            time.sleep(self.pkt_intvl)

            """ If the queue is paused, we should only receive the background packet """
            if self.queue_paused:
                if 'backend' in self.testbed_type:
                    filter_expr = (hex(scapy.Ether(pkts[0]).type) == '0x8100' and
                                   int(scapy.Ether(pkts[0])[scapy.Dot1Q].prio) == self.dscp_bg and
                                   int(scapy.Ether(pkts[0])[scapy.Dot1Q].vlan) == self.vlan_id)
                else:
                    filter_expr = (scapy.Ether(pkts[0])[
                                   scapy.IP].tos == tos_bg)
                pass_cnt += int(len(pkts) == 1 and filter_expr)

            else:
                pass_cnt += int(len(pkts) == 2)

        if self.debug:
            log_file.close()
        print(("Passes: %d / %d" % (pass_cnt, self.pkt_count)))

    def tearDown(self):
        reset_filters()
        BaseTest.tearDown(self)
