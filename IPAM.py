import os, sys
import csv
import ipaddress
import operator
import pprint
import collections
import logging

import rv.misc

class IPRangeUtil:
    def _subnet_check(self, sn):
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
                    'IP_END': n.network_address + n.num_addresses}

        raise Exception("Invalid sn: {}".format(sn))

    def __init__(self, f):
        logging.info("Loading IPData from {}".format(f))
        # dict for ipv4 and ipv6 data
        ip_data_dict = collections.defaultdict(list)
        with rv.misc.Timer() as t:
            with open(f, encoding='latin-1') as fd:
                csv_reader = csv.DictReader(fd)
                for r in csv_reader:
                    sn_info = self._subnet_check(r['Range'])
                    if sn_info:
                        r.update(sn_info)
                        version = sn_info['IP_START'].version
                        ip_data_dict[version].append(r)
        logging.info("Took {:.1f} secs to load".format(t()))

        for version, ip_data in ip_data_dict.items():
            # sort by most restricted range (LOW NUM) and IP_START
            logging.info("Sorting V{}".format(version))
            ip_data_dict[version] = sorted(ip_data, key=operator.itemgetter('NUM', 'IP_START'))

        self.ip_blocks_dict = {}
        for version, ip_data in ip_data_dict.items():
            # split ip_data into blocks of IP Ranges per NUM
            ip_blocks = collections.defaultdict(list)
            for ip in ip_data:
                ip_blocks[ip['NUM']].append(ip)
            self.ip_blocks_dict[version] = {'IP_BLOCKS': ip_blocks, 'IP_NUMS': sorted(ip_blocks.keys())}
        logging.info("IPDATA init done.")

    def lookup_ip(self, ip):
        ipa = ipaddress.ip_address(ip)
        d = self.ip_blocks_dict[ipa.version]
        ip_blocks = d['IP_BLOCKS']
        for num in d['IP_NUMS']:
            # see if ipa in the range of this blocks for this num
            if ipa < ip_blocks[num][0]['IP_START'] or ipa > ip_blocks[num][-1]['IP_END']:
                # logging.info("IP {} outside ranges of NUM {}".format(ip, num))
                continue
            # check if it exists in the block
            for ip_block in ip_blocks[num]:
                if ip_block['IP_START'] <= ipa <= ip_block['IP_END']:
                    return ip_block
        return None


#-----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    rv.misc.set_logging()
    f = r'TestData.csv'
    ipru = IPRangeUtil(f)
    for ip in ('10.12.86.10', '10.12.104.67', '10.13.17.12', '143.183.250.10', '198.175.120.40'):
        res = ipru.lookup_ip(ip)
        logging.info("{} = {}".format(ip, pprint.pformat(res) if res else 'NOT_FOUND'))
