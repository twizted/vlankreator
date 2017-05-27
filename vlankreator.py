#!/usr/bin/env python

#  VLANKreator - create VLAN interfaces to test network equipment setup
#  Copyright (C) 2017 Armando Vega
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import logging
import sys
import subprocess
import os
import netifaces


def weAreRoot():
    if os.getuid() == 0:
        return 1
    else:
        return 0


def getNextVLANAddress(lastOctet):
    if getNextVLANAddress.octetC == 255:
        if getNextVLANAddress.octetB == 255:
            return '10.%d.%d.%d' % (getNextVLANAddress.octetB, getNextVLANAddress.octetC, lastOctet)
        getNextVLANAddress.octetB += 1
        getNextVLANAddress.octetC = 0
    else:
        getNextVLANAddress.octetC += 1

    return '10.%d.%d.%d' % (getNextVLANAddress.octetB, getNextVLANAddress.octetC, lastOctet)


getNextVLANAddress.octetB = 1
getNextVLANAddress.octetC = 0


def addVLANInterface(hwInterface, vlanId, ipAddress):
    cmd = 'ip link add link ' + hwInterface + ' name ' + hwInterface + '.' + vlanId + ' type vlan id ' + vlanId
    if subprocess.call(cmd.split()) != 0:
        return 1
    cmd = 'ip address add ' + ipAddress + '/24 dev ' + hwInterface + '.' + vlanId
    if subprocess.call(cmd.split()) != 0:
        return 1
    cmd = 'ip link set ' + hwInterface + '.' + vlanId + ' up'
    if subprocess.call(cmd.split()) != 0:
        return 1
    return 0


def removeVLANInterface(hwInterface, vlanId):
    cmd = 'ip link del ' + hwInterface + '.' + vlanId
    return subprocess.call(cmd.split())


def interfaceRollback(hwInterface, vlanInterfaces):
    logger = logging.getLogger('kreator')
    for vlanId in sorted(vlanInterfaces):
        if removeVLANInterface(hwInterface, str(vlanId)) != 0:
            logger.error('!!! Unable to remove VLAN interface ' + hwInterface + '.' + str(vlanId))
        else:
            logger.info('Removed VLAN interface ' + hwInterface + '.' + str(vlanId))


def pingAllVLANs(vlanInterfaces):
    logger = logging.getLogger('kreator')
    DEVNULL = open(os.devnull, 'wb')
    for vlanId in sorted(vlanInterfaces):
        msg = 'Pinging peer on ' + vlanInterfaces[vlanId]['peer_addr'] + ' [VID: ' + str(vlanId) + ']'
        sys.stdout.flush()
        cmd = 'ping -W 1 -c 3 -i 0.3 ' + vlanInterfaces[vlanId]['peer_addr']
        retval = subprocess.call(cmd.split(), stdout=DEVNULL, stderr=subprocess.STDOUT, close_fds=True)
        if retval != 0:
            logger.error(msg + ' - FAILURE!')
        else:
            logger.info(msg + ' - SUCCESS!')


if __name__ == '__main__':
    ifaces = [nif for nif in netifaces.interfaces() if nif != 'lo']
    parser = argparse.ArgumentParser(description='Utility that tests VLANs')
    parser.add_argument('-r', '--role', choices=['primary', 'secondary'], help='Machine role', required=True)
    parser.add_argument('-i', '--interface', choices=ifaces,
                        help='Parent interface to use for VLANs', required=True)
    parser.add_argument('-n', '--nth-vlan', help='Check every n-th VLAN', type=int, required=True)
    args = vars(parser.parse_args())

    if not weAreRoot():
        print 'You *MUST* run the tool as \'root\' user!'
        sys.exit(1)

    if args['nth_vlan'] not in xrange(1, 4094):
        print 'Invalid VLAN increment, valid range is 1-4093!'
        parser.print_help()
        sys.exit(1)

    if args['role'] == 'primary':
        lastOctet = 1
    else:
        lastOctet = 2

    logger = logging.getLogger('kreator')
    logger.setLevel(logging.DEBUG)
    conformat = logging.Formatter('%(message)s')
    conlog = logging.StreamHandler()
    conlog.setLevel(logging.INFO)
    conlog.setFormatter(conformat)
    logger.addHandler(conlog)
    fileformat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    try:
        filelog = logging.FileHandler('testvlans.log')
        filelog.setLevel(logging.INFO)
        filelog.setFormatter(fileformat)
        logger.addHandler(filelog)
    except IOError:
        logger.warn('WARNING: Unable to open the log file, LOGGING DISABLED!')

    logger.info('Creating VLAN interfaces..')
    vlanInterfaces = dict()
    for vlanId in range(1, 4095, args['nth_vlan']):
        addr = getNextVLANAddress(lastOctet)
        if addVLANInterface(args['interface'], str(vlanId), addr) > 0:
            logger.error('ERROR: Unable to add a VLAN interface!')
            logger.info('Rolling back changes..')
            interfaceRollback(args['interface'], vlanInterfaces)
            logger.info('Exiting')
            sys.exit(1)
        else:
            changes = list(addr)
            changes[-1] = '2' if lastOctet == 1 else '1'
            peer_addr = ''.join(changes)
            vlanInterfaces[vlanId] = {'addr': addr, 'peer_addr': peer_addr}
            logger.info('Added VLAN interface ' + args['interface'] + '.' + str(vlanId))

    logger.info('VLAN interfaces created!')

    while str(raw_input('Continue with the ping test? [Y/n]: ')) in ['', 'y', 'Y']:
        pingAllVLANs(vlanInterfaces)

    logger.info('Removing VLAN interfaces..')
    interfaceRollback(args['interface'], vlanInterfaces)
    logger.info('Done!')
