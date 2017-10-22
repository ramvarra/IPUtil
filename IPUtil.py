import os, sys
import csv
import ipaddress
import operator
import pprint
import collections
import logging
from AVLTree import AVLTree, RangeKey

import rv.misc

# wrappe for AVL
class Key:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return self.v['IP_START'] == other.v['IP_START']

    def __lt__(self, other):
        return self.v['IP_START'] < other.v['IP_START']

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return str(self.v)

class IPRangeUtil:
    USE_AVL = True

    def _subnet_info(self, sn):
        '''
        Calculates START, END and NUMBBER addresses for IP Range.  Processes ranges expressed as
        ADDR1-ADDR2 (e.g. 10.24.164.0-10.24.171.255).
        :param sn: Range string from Subnet info CSV file.
        :return: dictionary containing START, END and NUM of addresses in the range
        '''
        if '-' in sn:
            # 10.24.164.0-10.24.171.255
            start, end = sn.split('-')
            ns, ne = ipaddress.IPv4Address(start), ipaddress.IPv4Address(end)
            return {'IP_START': ns, 'IP_END': ne, 'NUM': int(ne) - int(ns) + 1}
        if '/' in sn:
            ip_sn, ip_r = sn.split('/')
            if ip_r == '0' or ip_sn == '::' or ip_sn == '0.0.0.0':
                return None
            n = ipaddress.ip_network(sn)
            return {'IP_START': n.network_address, 'NUM': n.num_addresses,
                    'IP_END': n.network_address + n.num_addresses - 1}

        raise Exception("Invalid sn: {}".format(sn))


    def _read_subnet_entry(self, f, encoding='latin-1'):
        '''
        Generator that produces a IP SUBNET record from a CSV file.  The CSV file should have following required fields:
          Range: IPV4 or V6 Range (e.g. "2.2.2.0/24" or "262A:0:2D0:200::7/32")

        :param f: CSV File name.
        :param encoding: Encoding.
        :return: CSV Record
        '''
        with open(f, encoding=encoding) as fd:
            csv_reader = csv.DictReader(fd)
            yield from csv_reader


    def __init__(self, f, tree_type='AVL'):

        logging.info("Loading IPData from {}".format(f))
        # Create a dictionary for IPV4 and IPV6 Range lists.
        ip_data_dict = collections.defaultdict(list)
        with rv.misc.Timer() as t:
            for r in self._read_subnet_entry(f):
                sn_info = self._subnet_info(r['Range'])
                if sn_info:
                    r.update(sn_info)
                    version = sn_info['IP_START'].version
                    ip_data_dict[version].append(r)

        logging.info("Took {:.1f} secs to load IPRanges".format(t()))

        with rv.misc.Timer() as t:
            if self.USE_AVL:
                self._build_avl_tree(ip_data_dict)
                self.lookup_ip = self._lookup_avl_ip
            else:
                self._build_normal_tree(ip_data_dict)
                self.lookup_ip = self._lookup_normal_ip
        logging.info("IP Search Tree build: {:.1f} secs".format(t()))

    def _build_normal_tree(self, ip_data_dict):
        # create sorted IP block lists for each version
        self.ip_blocks_dict = {}
        for version, sn_list in ip_data_dict.items():
            logging.info("Sorting V{} list".format(version))
            # sort each list by most restricted range - i.e. ascending order of (NUM, IP_START)
            sn_list = sorted(sn_list, key=operator.itemgetter('NUM', 'IP_START'))
            # create a dict with list Subnets for each NUM
            ip_num_blocks = collections.defaultdict(list)
            for ip in sn_list:
                ip_num_blocks[ip['NUM']].append(ip)
            # store it
            self.ip_blocks_dict[version] = {'IP_BLOCKS': ip_num_blocks, 'IP_NUMS': sorted(ip_num_blocks.keys())}
            ip_block_list_lens = sorted((len(l), n) for n,l in ip_num_blocks.items())
            logging.info("Top 10 V{} Lengths = {}".format(version, ip_block_list_lens[-10:]))
            '''
            # print a few from 256 range
            block_256 = ip_num_blocks.get(256)
            if block_256:
                logging.info("256 block size: {}".format(len(block_256)))
                logging.info("last 5: {}".format(','.join(r['Range'] for r in block_256[-5:])))
                #last 5: 198.175.121.0/24,198.175.122.0/24,198.175.123.0/24,198.175.195.0/24,204.128.183.0/24
            '''
        logging.info("NORMAL IPDATA init done.")

    def _build_avl_tree(self, ip_data_dict):
        self.ip_avl_blocks_dict = {}
        for version, sn_list in ip_data_dict.items():
            # sort each list by most restricted range - i.e. ascending order of (NUM, IP_START)
            sn_list = sorted(sn_list, key=operator.itemgetter('NUM', 'IP_START'))
            # create a dict with list Subnets for each NUM
            ip_num_blocks = {}
            for ip in sn_list:
                num = ip['NUM']
                rk = RangeKey(ip['IP_START'], ip['IP_END'], ip)
                if num not in ip_num_blocks:
                    d = {'AVL': AVLTree()}
                    d['AVL'].insert(rk)
                    d['START_MIN'] = ip['IP_START']
                    d['END_MAX']  = ip['IP_END']
                    ip_num_blocks[num] = d
                    d['FIRST'] = ip
                    d['LAST'] = ip
                else:
                    d = ip_num_blocks[num]
                    d['AVL'].insert(rk)
                    if ip['IP_START'] < d['START_MIN']:
                        d['START_MIN'] = ip['START_MIN']
                    if ip['IP_END'] > d['END_MAX']:
                        d['END_MAX'] = ip['IP_END']
                    d['LAST'] = ip
            # store it
            self.ip_avl_blocks_dict[version] = {'IP_BLOCKS': ip_num_blocks, 'IP_NUMS': sorted(ip_num_blocks.keys())}
        logging.info("AVL IPDATA init done.")



    def _lookup_normal_ip(self, ip):
        '''
        Look up IP address in the range list.
        :param ip: ip address string (V4 or V6)
        :return: Subnet info
        '''
        ipa = ipaddress.ip_address(ip)
        d = self.ip_blocks_dict[ipa.version]
        ip_blocks, num_list = d['IP_BLOCKS'], d['IP_NUMS']
        # search from smallest block NUM to largest block
        for num in num_list:
            ip_range_start = ip_blocks[num][0]['IP_START']
            ip_range_end = ip_blocks[num][-1]['IP_END']

            # see if ipa in the range of this blocks for this num
            if ipa < ip_blocks[num][0]['IP_START'] or ipa > ip_blocks[num][-1]['IP_END']:
                # logging.info("IP {} outside ranges of NUM {}".format(ip, num))
                continue
            # search this block to see if the IP Address exists in the ranges.
            #logging.info("Checking Range: {} - {} NUM: {}".format(ip_range_start, ip_range_end, num))
            for ip_range in ip_blocks[num]:
                if ip_range['IP_START'] <= ipa <= ip_range['IP_END']:
                    return ip_range
        return None

    def _lookup_avl_ip(self, ip):
        '''
        Look up IP address in the range list.
        :param ip: ip address string (V4 or V6)
        :return: Subnet info
        '''
        ipa = ipaddress.ip_address(ip)
        avl_d = self.ip_avl_blocks_dict[ipa.version]
        ip_blocks, num_list = avl_d['IP_BLOCKS'], avl_d['IP_NUMS']
        # search from smallest block NUM to largest block
        for num in num_list:
            # see if ipa in the range of this blocks for this num
            d = ip_blocks[num]
            ip_range_start = d['FIRST']['IP_START']
            ip_range_end = d['LAST']['IP_END']

            if ipa < ip_range_start or ipa > ip_range_end:
                # logging.info("IP {} outside ranges of NUM {}".format(ip, num))
                continue
            # search this block to see if the IP Address exists in the ranges.
            #logging.info("Looking in {}-{} NUM: {}".format(ip_range_start, ip_range_end, num))

            node = d['AVL'].lookup(RangeKey(ipa))
            if node:
                return node.info
        return None


#-----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    rv.misc.set_logging()
    f = r'TestData.csv'
    ipru = IPRangeUtil(f)


    for ip in ('10.12.86.10', '10.12.104.67', '10.13.17.12', '143.183.250.10', '198.175.120.40', '172.217.4.132', '157.240.17.35'):
        res = ipru.lookup_ip(ip)
        logging.info("{} = {}".format(ip, res['Range'] if res else 'NOT_FOUND'))


    # bennch mark
    test_ranges = "198.175.121.0/24,198.175.122.0/24,198.175.123.0/24,198.175.195.0/24,204.128.183.0/24,172.217.4.0/24"
    logging.info("Generating Benchmark addresses")
    num_per_range = 100
    address_list = []
    for tr in test_ranges.split(','):
        sn = ipru._subnet_info(tr)
        for i in range(max(num_per_range, sn['NUM'])):
            address_list.append(str(sn['IP_START'] + i))

    logging.info("Benchmark with {} addresses".format(len(address_list)))
    with rv.misc.Timer() as t:
        for ipa in address_list:
            res = ipru.lookup_ip(ipa)
            if not ipa.startswith('172.'):
                assert res, "IP {} not found ".format(ipa)
    logging.info("Lookup time {:.1f}".format(t()))

    logging.info("Verification")
    for ipa in address_list:
        res = ipru.lookup_ip(ipa)
        if not ipa.startswith('172.'):
            assert res['IP_START'] <= ipaddress.IPv4Address(ipa) <= res['IP_END'], \
                "IP {} = Bad Range {} - {} to {}".format(ipa, res['Range'], res['IP_START'], res['IP_END'])
        else:
            assert res is None, "Bad match for IP {}  - should be None instead {}".format(ipa, res)

    logging.info("Verification successful")
