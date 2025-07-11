import datetime
import logging
import os
import pytest
import random
import time
import traceback

from tests.common.broadcom_data import is_broadcom_device
from tests.common.fixtures.conn_graph_facts import enum_fanout_graph_facts      # noqa: F401
from tests.common.helpers.assertions import pytest_require
from tests.common.helpers.pfc_storm import PFCStorm
from tests.common.plugins.loganalyzer.loganalyzer import LogAnalyzer
from tests.common.reboot import reboot
from tests.common.reboot import DUT_ACTIVE
from tests.common.utilities import InterruptableThread
from tests.common.utilities import join_all
from tests.ptf_runner import ptf_runner
from tests.common import constants
from tests.common.helpers.pfcwd_helper import EXPECT_PFC_WD_DETECT_RE, EXPECT_PFC_WD_RESTORE_RE, pfcwd_show_status
from tests.common.helpers.pfcwd_helper import send_background_traffic
from tests.common.helpers.pfcwd_helper import has_neighbor_device
from tests.common.utilities import wait_until
from tests.common import config_reload

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")
TESTCASE_INFO = {'no_storm': {'test_sequence': ["detect", "restore", "warm-reboot", "detect", "restore"],
                              'desc': "Test PFC storm detect/restore before and after warm boot"},
                 'storm': {'test_sequence': ["detect", "warm-reboot", "detect", "restore"],
                           'desc': "Test PFC storm detect with on going storm after warm boot followed by restore"},
                 'async_storm': {'test_sequence': ["storm_defer", "warm-reboot", "detect", "restore"],
                                 'desc': "Test PFC async storm start/end with warm boot followed by detect/restore"}
                 }
ACTIONS = {'detect': 0,
           'restore': 1,
           'storm_defer': 2
           }

pytestmark = [pytest.mark.disable_loganalyzer,
              pytest.mark.topology('t0')
              ]

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def skip_pfcwd_wb_tests(duthosts, enum_rand_one_per_hwsku_frontend_hostname):
    """
    Skip Pfcwd warm reboot tests on certain asics

    Args:
        duthosts (pytest fixture): list of Duts
        enum_rand_one_per_hwsku_frontend_hostname (str): hostname of DUT

    Returns:
        None
    """
    duthost = duthosts[enum_rand_one_per_hwsku_frontend_hostname]
    SKIP_LIST = ["td2"]
    asic_type = duthost.get_asic_name()
    pytest_require(not (is_broadcom_device(duthost) and asic_type in SKIP_LIST),
                   "Warm reboot is not supported on {}".format(asic_type))


@pytest.fixture(autouse=True)
def setup_pfcwd(duthosts, enum_rand_one_per_hwsku_frontend_hostname):
    """
    Setup PFCwd before the test run

    Args:
        duthost(AnsibleHost) : dut instance
    """
    duthost = duthosts[enum_rand_one_per_hwsku_frontend_hostname]
    logger.info("Setup the default pfcwd config for warm-reboot test")
    duthost.command("redis-cli -n 4 hset \"DEVICE_METADATA|localhost\" "
                    "default_pfcwd_status enable")
    duthost.command("pfcwd stop")
    time.sleep(5)
    duthost.command("pfcwd start_default")


class PfcCmd(object):
    @staticmethod
    def set_storm_status(dut, queue_oid, storm_status):
        """
        Sets the PFC storm status on the queue

        Args:
            dut(AnsibleHost) : dut instance
            queue_oid(string) : queue oid for which the storm status needs to be set
            storm_status(string) : debug storm status (enabled/disabled)
        """
        logger.info("Setting DEBUG storm status {} on queue oid {}".format(storm_status, queue_oid))
        cmd = "redis-cli -n 2 HSET COUNTERS:{} DEBUG_STORM {}"
        dut.command(cmd.format(queue_oid, storm_status))

    @staticmethod
    def get_queue_oid(dut, port, queue_num):
        """
        Retreive queue oid

        Args:
            dut(AnsibleHost) : dut instance
            port(string) : port name
            queue_num(int) : queue number

        Returns:
            queue oid(string)
        """
        cmd = "redis-cli -n 2 HGET COUNTERS_QUEUE_NAME_MAP {}:{}".format(port, queue_num)
        return dut.command(cmd)['stdout']


class SetupPfcwdFunc(object):
    """ Test setup per port """
    def setup_test_params(self, port, vlan, idx, ip_version="IPv4"):
        """
        Sets up test parameters associated with a DUT port

        Args:
            port(string) : DUT port
            vlan(dict) : DUT vlan info
        """
        logger.info("--- Setting up test params for port {} ---".format(port))
        self.setup_port_params(port, idx)
        self.resolve_arp(vlan, ip_version=ip_version)

    def setup_port_params(self, port, idx):
        """
        Gather all the parameters needed for storm generation and ptf test based off the DUT port

        Args:
            port(string) : DUT port
        """
        self.pfc_wd = dict()
        self.pfc_wd['queue_indices'] = [4]
        if self.two_queues and (self.seed % 2) != 0:
            # Will send traffic for (queues 4 and 3) per each port
            self.pfc_wd['queue_indices'].append(3)
        self.pfc_wd['test_pkt_count'] = 100
        self.pfc_wd['frames_number'] = 1000000000
        self.peer_device = self.ports[port]['peer_device']
        self.pfc_wd['test_port'] = port
        self.pfc_wd['rx_port'] = self.ports[port]['rx_port']
        self.pfc_wd['test_neighbor_addr'] = self.ports[port]['test_neighbor_addr']
        self.pfc_wd['rx_neighbor_addr'] = self.ports[port]['rx_neighbor_addr']
        self.pfc_wd['test_port_id'] = self.ports[port]['test_port_id']
        self.pfc_wd['rx_port_id'] = self.ports[port]['rx_port_id']
        self.pfc_wd['port_type'] = self.ports[port]['test_port_type']
        self.pfc_wd['test_port_ids'] = list()
        if self.pfc_wd['port_type'] == "portchannel":
            self.pfc_wd['test_port_ids'] = self.ports[port]['test_portchannel_members']
        elif self.pfc_wd['port_type'] in ["vlan", "interface"]:
            self.pfc_wd['test_port_ids'] = [self.pfc_wd['test_port_id']]
        self.pfc_wd['test_port_vlan_id'] = self.ports[port].get('test_port_vlan_id')
        self.pfc_wd['rx_port_vlan_id'] = self.ports[port].get('rx_port_vlan_id')
        self.pfc_wd['fake_storm'] = self.fake_storm

    def resolve_arp(self, vlan, ip_version="IPv4"):
        """
        Populate ARP info for the DUT vlan port

        Args:
            vlan(dict) : DUT vlan info
        """
        if self.pfc_wd['port_type'] == "vlan":
            self.ptf.script("./scripts/remove_ip.sh")
            ptf_port = 'eth%s' % self.pfc_wd['test_port_id']
            if self.pfc_wd['test_port_vlan_id'] is not None:
                ptf_port += (constants.VLAN_SUB_INTERFACE_SEPARATOR + self.pfc_wd['test_port_vlan_id'])
            self.ptf.command("ip neigh flush all")
            self.ptf.command("ip -6 neigh flush all")
            self.dut.command("ip neigh flush all")
            self.dut.command("ip -6 neigh flush all")
            if ip_version == "IPv4":
                self.ptf.command("ifconfig {} {}".format(ptf_port, self.pfc_wd['test_neighbor_addr']))
                self.ptf.command("ping {} -c 10".format(vlan['addr']))
                self.dut.command(
                    "docker exec -i swss arping {} -c 5".format(self.pfc_wd['test_neighbor_addr']))  # noqa: E501
            else:
                self.ptf.command(
                    "ip -6 addr add {}/{} dev {}".format(self.pfc_wd['test_neighbor_addr'], vlan['prefix'], ptf_port))
                self.ptf.command("ping {} -6 -c 10".format(vlan['addr']))
                self.dut.command("docker exec -i swss ping -6 -c 5 {}".format(self.pfc_wd['test_neighbor_addr']))

    def storm_defer_setup(self):
        """
        Set the defer start and stop values and calculate the max wait time

        Max wait time will be used after warm boot to wait for all the storms to end prior
        to starting the next detect
        """
        self.pfc_wd['storm_start_defer'] = random.randrange(120)
        self.pfc_wd['storm_stop_defer'] = random.randrange(self.pfc_wd['storm_start_defer'] + 5, 125)
        # Added 10 sec to max_wait as sometimes it's not enough and test fail due to runtime error
        self.max_wait = max(self.max_wait, self.pfc_wd['storm_stop_defer']) + 10

    def storm_setup(self, port, queue, send_pfc_frame_interval, storm_defer=False):
        """
        Prepare fanout for the storm generation

        Args:
            port(string) : DUT port
            queue(int): The queue on the DUT port which will get stormed
            storm_defer(bool): if the storm needs to be deferred, default: False
        """
        if self.dut.facts['asic_type'] == 'vs':
            peer_info = {}
        else:
            peer_info = {'peerdevice': self.peer_device,
                         'hwsku': self.fanout_info[self.peer_device]['device_info']['HwSku'],
                         'pfc_fanout_interface': self.neighbors[port]['peerport']
                         }

        if storm_defer:
            self.storm_handle[port][queue] = PFCStorm(self.dut, self.fanout_info, self.fanout,
                                                      pfc_queue_idx=queue,
                                                      pfc_frames_number=self.pfc_wd['frames_number'],
                                                      peer_info=peer_info,
                                                      pfc_storm_defer_time=self.pfc_wd['storm_start_defer'],
                                                      pfc_storm_stop_defer_time=self.pfc_wd['storm_stop_defer'],
                                                      send_pfc_frame_interval=send_pfc_frame_interval)
        else:
            self.storm_handle[port][queue] = PFCStorm(self.dut, self.fanout_info, self.fanout,
                                                      pfc_queue_idx=queue,
                                                      pfc_frames_number=self.pfc_wd['frames_number'],
                                                      peer_info=peer_info,
                                                      send_pfc_frame_interval=send_pfc_frame_interval)
        # new peer device
        if not self.peer_dev_list or self.peer_device not in self.peer_dev_list:
            self.peer_dev_list[self.peer_device] = peer_info['hwsku']
            self.storm_handle[port][queue].deploy_pfc_gen()


class SendVerifyTraffic(object):
    """ PTF test """
    def __init__(self, ptf, router_mac, pfc_params, queue, ip_version='IPv4'):
        """
        Args:
            ptf(AnsibleHost) : ptf instance
            router_mac(string) : router mac address
            ptf_params(dict) : all PFC test params specific to the DUT port
            queue(int): queue to check the wd action
        """
        self.ptf = ptf
        self.router_mac = router_mac
        self.pfc_wd_test_pkt_count = pfc_params['test_pkt_count']
        self.pfc_wd_rx_port_id = pfc_params['rx_port_id']
        self.pfc_wd_test_port = pfc_params['test_port']
        self.pfc_wd_test_port_id = pfc_params['test_port_id']
        self.pfc_wd_test_port_ids = pfc_params['test_port_ids']
        self.pfc_wd_test_neighbor_addr = pfc_params['test_neighbor_addr']
        self.pfc_wd_rx_neighbor_addr = pfc_params['rx_neighbor_addr']
        self.port_type = pfc_params['port_type']
        self.queue = queue
        self.ip_version = ip_version

    def verify_tx_egress(self, wd_action):
        """
        Send traffic with test port as the egress and verify if the packets get forwarded
        or dropped based on the action

        Args:
            wd_action(string): pfcwd action expected on that port and queue (valid values: drop, forward)
        """
        logger.info("Check for egress {} on Tx port {}".format(wd_action, self.pfc_wd_test_port))
        dst_port = "[" + str(self.pfc_wd_test_port_id) + "]"
        if wd_action == "forward" and type(self.pfc_wd_test_port_ids) == list:
            dst_port = "".join(str(self.pfc_wd_test_port_ids)).replace(',', '')
        ptf_params = {'router_mac': self.router_mac,
                      'queue_index': self.queue,
                      'pkt_count': self.pfc_wd_test_pkt_count,
                      'port_src': self.pfc_wd_rx_port_id[0],
                      'port_dst': dst_port,
                      'ip_dst': self.pfc_wd_test_neighbor_addr,
                      'port_type': self.port_type,
                      'wd_action': wd_action,
                      'ip_version': self.ip_version}
        log_format = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        log_file = "/tmp/pfc_wd.PfcWdTest.{}.log".format(log_format)
        ptf_runner(self.ptf, "ptftests", "pfc_wd.PfcWdTest", "ptftests", params=ptf_params,
                   log_file=log_file, is_python3=True)

    def verify_rx_ingress(self, wd_action):
        """
        Send traffic with test port as the ingress and verify if the packets get forwarded
        or dropped based on the action

        Args:
            wd_action(string): pfcwd action expected on that port and queue (valid values: drop, forward)
        """
        logger.info("Check for ingress {} on Rx port {}".format(wd_action, self.pfc_wd_test_port))
        if type(self.pfc_wd_rx_port_id) == list:
            dst_port = "".join(str(self.pfc_wd_rx_port_id)).replace(',', '')
        else:
            dst_port = "[ " + str(self.pfc_wd_rx_port_id) + " ]"
        ptf_params = {'router_mac': self.router_mac,
                      'queue_index': self.queue,
                      'pkt_count': self.pfc_wd_test_pkt_count,
                      'port_src': self.pfc_wd_test_port_id,
                      'port_dst': dst_port,
                      'ip_dst': self.pfc_wd_rx_neighbor_addr,
                      'port_type': self.port_type,
                      'wd_action': wd_action,
                      'ip_version': self.ip_version}
        log_format = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        log_file = "/tmp/pfc_wd.PfcWdTest.{}.log".format(log_format)
        ptf_runner(self.ptf, "ptftests", "pfc_wd.PfcWdTest", "ptftests", params=ptf_params,
                   log_file=log_file, is_python3=True)

    def verify_wd_func(self, dut, detect=True):
        """
        PTF traffic send and verify

        Args:
            detect(bool) : if the current iteration is a storm detect or not (default: True)
        """
        if detect:
            rx_action = "drop"
            tx_action = "drop"
            wd_action = "drop"
        else:
            rx_action = "forward"
            tx_action = "forward"
            wd_action = "forward"

        if dut.facts['asic_type'] in ['mellanox', 'cisco-8000', 'marvell-teralynx']:
            rx_action = "forward"

        logger.info("--- Verify PFCwd function for pfcwd action {}, Tx traffic {}, Rx traffic {} ---"
                    .format(wd_action, tx_action, rx_action))
        self.verify_tx_egress(tx_action)
        self.verify_rx_ingress(rx_action)


class TestPfcwdWb(SetupPfcwdFunc):
    """ Test PFCwd warm-reboot function and supporting methods """
    def storm_detect_path(self, port, queue, first_detect_after_wb=False):
        """
        Storm detection action and associated verifications

        Args:
            port(string) : DUT port
            queue(int): queue on the port that will be stormed
            first_detect_after_wb(bool): first detect iteration after warm reboot (default: False)
        """
        # for the first iteration after wb, do not write a marker to the log but specify the start msg from
        # where to search the logs
        start_marker = None
        if first_detect_after_wb:
            start_marker = ("NOTICE swss#orchagent: :- setWarmStartState: "
                            "orchagent warm start state changed to initialized")
        self.loganalyzer = LogAnalyzer(ansible_host=self.dut,
                                       marker_prefix="pfcwd_wb_storm_detect_port_{}_queue_{}".format(port, queue),
                                       start_marker=start_marker)
        marker = self.loganalyzer.init()
        time.sleep(5)
        ignore_file = os.path.join(TEMPLATES_DIR, "ignore_pfc_wd_messages")
        reg_exp = self.loganalyzer.parse_regexp_file(src=ignore_file)
        self.loganalyzer.ignore_regex.extend(reg_exp)
        self.loganalyzer.expect_regex = []
        self.loganalyzer.expect_regex.extend([EXPECT_PFC_WD_DETECT_RE])
        self.loganalyzer.match_regex = []

        selected_test_ports = [self.pfc_wd['rx_port'][0]]
        test_ports_info = {self.pfc_wd['rx_port'][0]: self.pfc_wd}

        with send_background_traffic(self.dut, self.ptf, [queue], selected_test_ports, test_ports_info):
            # ongoing storm. no need to start a new one
            if not first_detect_after_wb:
                if not self.pfc_wd['fake_storm']:
                    self.storm_handle[port][queue].start_storm()
                    time.sleep(60 * len(self.pfc_wd['queue_indices']))
                else:
                    logger.info("Enable DEBUG fake storm on port {} queue {}".format(port, queue))
                    PfcCmd.set_storm_status(self.dut, self.oid_map[(port, queue)], "enabled")
                    time.sleep(5)
            else:
                # for the first iteration after wb, check the log for detect msgs for the ongoing storms
                self.loganalyzer.expected_matches_target = len(self.ports) * len(self.pfc_wd['queue_indices'])
                time.sleep(20)

        # storm detect check
        logger.info("Verify if PFC storm is detected on port {} queue {}".format(port, queue))
        self.loganalyzer.analyze(marker)

    def storm_restore_path(self, port, queue):
        """
        Storm restoration action and associated verifications

        Args:
            port(string) : DUT port
            queue(int): queue on the port where storm would be restored
        """
        marker = self.loganalyzer.update_marker_prefix("pfcwd_wb_storm_restore_port_{}_queue_{}".format(port, queue))
        time.sleep(5)
        ignore_file = os.path.join(TEMPLATES_DIR, "ignore_pfc_wd_messages")
        reg_exp = self.loganalyzer.parse_regexp_file(src=ignore_file)
        self.loganalyzer.ignore_regex.extend(reg_exp)
        self.loganalyzer.expect_regex = []
        self.loganalyzer.expect_regex.extend([EXPECT_PFC_WD_RESTORE_RE])
        self.loganalyzer.match_regex = []
        self.loganalyzer.expected_matches_target = 0

        if not self.pfc_wd['fake_storm']:
            self.storm_handle[port][queue].stop_storm()
            time.sleep(15)
        else:
            logger.info("Disable DEBUG fake storm on port {} queue {}".format(port, queue))
            PfcCmd.set_storm_status(self.dut, self.oid_map[(port, queue)], "disabled")
            time.sleep(5)

        # storm restore check
        logger.info("Verify if PFC storm is restored on port {}".format(port))
        self.loganalyzer.analyze(marker)

    def defer_fake_storm(self, port, queue, start_defer, stop_defer):
        time.sleep(start_defer)
        DUT_ACTIVE.wait()
        logger.info("Enable DEBUG fake storm on port {} queue {}".format(port, queue))
        PfcCmd.set_storm_status(self.dut, self.oid_map[(port, queue)], "enabled")
        time.sleep(stop_defer)
        DUT_ACTIVE.wait()
        logger.info("Disable DEBUG fake storm on port {} queue {}".format(port, queue))
        PfcCmd.set_storm_status(self.dut, self.oid_map[(port, queue)], "disabled")

    def run_test(self, port, queue, detect=True, storm_start=True, first_detect_after_wb=False,
                 storm_defer=False):
        """
        Test method that invokes the storm detection and restoration path which includes the traffic
        test

        Args:
            port(string) : DUT port
            queue(int): queue on the port which would be stormed/restored
            detect(bool): if the detect logic needs to be called (default: True)
            storm_start(bool): used to decide certain actions in the detect logic (default: True)
            first_detect_after_wb(bool): used to decide certain actions in the detect logic (default: False)
            storm_defer(bool): use the storm defer logic or not (default: False)
        """

        logger.info(
            "pfcwd wr: run_test port: {}, queue: {}, detect: {}, storm_start: {}, "
            "first_detect_after_wb: {}, storm_defer: {}".format(
                port, queue, detect, storm_start, first_detect_after_wb, storm_defer
            )
        )

        # for deferred storm, return to main loop for next action which is warm boot
        if storm_defer:
            if not self.pfc_wd['fake_storm']:
                self.storm_handle[port][queue].start_storm()
                self.storm_handle[port][queue].stop_storm()
            else:
                thread = InterruptableThread(
                    target=self.defer_fake_storm,
                    args=(port, queue, self.pfc_wd['storm_start_defer'],
                          self.pfc_wd['storm_stop_defer']))
                thread.daemon = True
                thread.start()
                self.storm_threads.append(thread)
            return

        if detect:
            if storm_start or first_detect_after_wb:
                logger.info("--- Storm detection path for port {} queue {} ---".format(port, queue))
                self.storm_detect_path(port, queue, first_detect_after_wb=first_detect_after_wb)
        else:
            logger.info("--- Storm restoration path for port {} queue {} ---".format(port, queue))
            self.storm_restore_path(port, queue)
        # test pfcwd functionality on a storm/restore
        self.traffic_inst.verify_wd_func(self.dut, detect=detect)

    @pytest.fixture(autouse=True)
    def pfcwd_wb_test_cleanup(self, setup_pfc_test):
        """
        Cleanup method

        Args:
            setup_pfc_test(fixture): module scoped autouse fixture
        """
        yield

        # stop all threads that might stuck in wait
        DUT_ACTIVE.set()
        # if there are no neighbor devices detected, exit the cleanup function early
        if not has_neighbor_device(setup_pfc_test):
            return

        for thread in self.storm_threads:
            thread_exception = thread.join(timeout=0.1,
                                           suppress_exception=True)
            if thread_exception:
                logger.debug("Exception in thread %r:", thread)
                logger.debug(
                    "".join(traceback.format_exception(*thread_exception))
                    )
        self.stop_all_storm()
        time.sleep(5)
        logger.info("--- Stop PFC WD ---")
        self.dut.command("pfcwd stop")
        config_reload(self.dut, safe_reload=True, check_intf_up_ports=True, wait_for_bgp=True)

    def stop_all_storm(self):
        """
        Stop all the storms after each test run
        """
        if self.storm_handle:
            logger.info("--- Stopping storm on all ports ---")
            for port in self.storm_handle:
                for queue in self.storm_handle[port]:
                    if self.storm_handle[port][queue]:
                        logger.info("--- Stop pfc storm on port {} queue {}".format(port, queue))
                        self.storm_handle[port][queue].stop_storm()
                    else:
                        logger.info("--- Disabling fake storm on port {} queue {}".format(port, queue))
                        PfcCmd.set_storm_status(self.dut, self.oid_map[(port, queue)], "disabled")

    def pfcwd_wb_helper(self, fake_storm, testcase_actions, setup_pfc_test, enum_fanout_graph_facts,    # noqa: F811
                        ptfhost, duthost, localhost, fanouthosts, two_queues):
        """
        Helper method that initializes the vars and starts the test execution

        Args:
            fake_storm(bool): if fake storm is enabled or disabled
            testcase_actions(list): list of actions that the test will go through
            setup_pfc_test(fixture): module scoped autouse fixture
            enum_fanout_graph_facts(fixture): fanout info
            ptfhost(AnsibleHost): PTF instance
            duthost(AnsibleHost): DUT instance
            localhost(AnsibleHost): local instance
            fanouthosts(AnsibleHost): fanout instance
        """
        setup_info = setup_pfc_test
        ip_version = setup_info["ip_version"]
        self.fanout_info = enum_fanout_graph_facts
        self.ptf = ptfhost
        self.dut = duthost
        self.asic_type = duthost.facts['asic_type']
        self.fanout = fanouthosts
        self.timers = setup_info['pfc_timers']
        self.ports = setup_info['selected_test_ports']
        self.neighbors = setup_info['neighbors']
        dut_facts = self.dut.facts
        self.peer_dev_list = dict()
        self.seed = int(datetime.datetime.today().day)
        self.two_queues = two_queues
        self.storm_handle = dict()
        bitmask = 0
        storm_deferred = 0
        storm_restored = 0
        self.max_wait = 0
        self.fake_storm = fake_storm
        self.oid_map = dict()
        self.storm_threads = []

        logger.debug("pfcwd wr: fake_storm: {} two_queues: {}".format(self.fake_storm, self.two_queues))

        for t_idx, test_action in enumerate(testcase_actions):
            logger.info("pfcwd wr: Index {} test_action {}".format(t_idx, test_action))
            if 'warm-reboot' in test_action:
                reboot(self.dut, localhost, reboot_type="warm", wait_warmboot_finalizer=True)

                assert wait_until(300, 20, 20, self.dut.critical_services_fully_started), \
                    "All critical services should fully started!"

                continue

            # Need to wait some time after warm-reboot for the counters to be created
            # if create_only_config_db_buffers is not enabled
            if t_idx > 0 and test_action == 'detect' and testcase_actions[t_idx - 1] == "warm-reboot":
                config_facts = duthost.get_running_config_facts()
                if config_facts["DEVICE_METADATA"]['localhost'].get("create_only_config_db_buffers") != 'true':
                    time.sleep(20)
                    logger.info("Wait 20s before the first detect after the warm-reboot "
                                "for the counters to be created")
            # one of the factors to decide if the storm needs to be started
            storm_restored = bitmask and (bitmask & 2)
            # if the action prior to the warm-reboot was a 'storm_defer', ensure that all the storms are
            # stopped
            storm_deferred = bitmask and (bitmask & 4)
            if storm_deferred:
                logger.info("Wait for all the deferred storms to start and stop ...")
                join_all(self.storm_threads, self.max_wait)
                self.storm_threads = []
                self.storm_handle = dict()

            bitmask = (1 << ACTIONS[test_action])
            for p_idx, port in enumerate(self.ports):
                logger.info("")
                logger.info("pfcwd wr: --- Testing on port {} ---".format(port))
                if self.asic_type != 'vs' and self.fanout[self.ports[port]['peer_device']].os == 'onyx':
                    send_pfc_frame_interval = calculate_send_pfc_frame_interval(duthost, port)
                else:
                    send_pfc_frame_interval = 0
                self.setup_test_params(port, setup_info['vlan'], p_idx, ip_version=ip_version)
                for q_idx, queue in enumerate(self.pfc_wd['queue_indices']):
                    logger.info("pfcwd wr: --- Testing on queue {} ---".format(queue))
                    if not t_idx or storm_deferred:
                        if not q_idx:
                            self.storm_handle[port] = dict()
                        self.storm_handle[port][queue] = None

                        # setup the defer parameters if the storm is deferred currently
                        if (bitmask & 4):
                            self.storm_defer_setup()

                        if not self.pfc_wd['fake_storm']:
                            self.storm_setup(port, queue,
                                             send_pfc_frame_interval=send_pfc_frame_interval,
                                             storm_defer=(bitmask & 4))
                        else:
                            self.oid_map[(port, queue)] = PfcCmd.get_queue_oid(self.dut, port, queue)

                    self.traffic_inst = SendVerifyTraffic(
                        self.ptf, dut_facts['router_mac'], self.pfc_wd, queue, ip_version
                    )
                    try:
                        pfcwd_show_status(
                            self.dut,
                            "pfcwd wr: run_test start t_idx: {}, test_action: {}, p_idx: {}-{}, q_idx: {}-{}, "
                            "bitmask: {}, storm_deferred: {}, storm_restored: {}".format(
                                t_idx, test_action, p_idx, port, q_idx, queue, bitmask, storm_deferred, storm_restored
                            )
                        )
                        self.run_test(port, queue, detect=(bitmask & 1),
                                      storm_start=not t_idx or storm_deferred or storm_restored,
                                      first_detect_after_wb=(t_idx == 2 and not p_idx and not q_idx and not storm_deferred),  # noqa: E501
                                      storm_defer=(bitmask & 4))
                        pfcwd_show_status(self.dut, "pfcwd wr: run_test end")
                    except Exception as e:
                        pfcwd_show_status(self.dut, "pfcwd wr: run_test exception")
                        pytest.fail(str(e))

    @pytest.fixture(params=['no_storm', 'storm', 'async_storm'])
    def testcase_action(self, request):
        """
        Parameters to invoke the pfcwd warm boot test

        Args:
            request(pytest) : pytest request object

        Yields:
            testcase_action(string) : testcase to execute
        """
        yield request.param

    def test_pfcwd_wb(self, fake_storm, testcase_action, setup_pfc_test, enum_fanout_graph_facts,   # noqa: F811
                      ptfhost, duthosts, enum_rand_one_per_hwsku_frontend_hostname,
                      localhost, fanouthosts, two_queues):
        """
        Tests PFCwd warm reboot with various testcase actions

        Args:
            fake_storm(fixture): fake storm status
            testcase_action(fixture): testcase to execute (values: 'no_storm', 'storm', 'async_storm')

                'no_storm' : PFCwd storm detection/restore before and after warm reboot
                'storm' : PFC storm started and detected before warm-reboot.
                          Storm is ongoing during warm boot and lasts past the warm boot finish.
                          Verifies if the storm is detected after warm-reboot.
                          PFC storm is stopped and 465 restored after warm boot
                'async_storm': PFC storm asynchronously starts at a random time and lasts a random period at fanout.
                               Warm reboot is done. Wait for all the storms to finish
                               and then verify the storm detect/restore logic

            setup_pfc_test(fixture) : Module scoped autouse fixture for PFCwd
            enum_fanout_graph_facts(fixture) : fanout graph info
            ptfhost(AnsibleHost) : ptf host instance
            duthost(AnsibleHost) : DUT instance
            localhost(AnsibleHost) : localhost instance
            fanouthosts(AnsibleHost): fanout instance
        """
        # skip the pytest when the device does not have neighbors
        # 'rx_port_id' being None indicates there are no ports available to receive frames for the fake storm
        if not has_neighbor_device(setup_pfc_test):
            pytest.skip("Test skipped: No neighbors detected as 'rx_port_id' is None for selected test ports,"
                        " which is necessary for PFCwd test setup.")

        duthost = duthosts[enum_rand_one_per_hwsku_frontend_hostname]
        logger.info("--- {} ---".format(TESTCASE_INFO[testcase_action]['desc']))
        self.pfcwd_wb_helper(fake_storm, TESTCASE_INFO[testcase_action]['test_sequence'], setup_pfc_test,
                             enum_fanout_graph_facts, ptfhost, duthost, localhost, fanouthosts, two_queues)


def calculate_send_pfc_frame_interval(duthost, port):
    speed = float(duthost.get_speed(port))/1000*1024*1024*1024
    pfc_frame_len = 512.0
    quatta_number = 65535
    sleep_proportion = 0.7
    send_pfc_frame_interval = sleep_proportion*quatta_number*pfc_frame_len/speed
    logger.info("send pfc frame interval of {} is: {}".format(port, send_pfc_frame_interval))
    return send_pfc_frame_interval
