#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# This is a simple example of starting production cycle on mujin controller and simultaneously:
#
# - queuing one order request
# - waiting for one order result
# - managing pick location container move in and move out
# - managing place location container move in and move out
#

import time
import argparse
import asyncio

from mujinproductioncycleclient.graphqlclient import MujinGraphClient
from mujinproductioncycleclient.ordermanager import ProductionCycleOrderManager

import logging
log = logging.getLogger(__name__)


async def _RunMain(url, username, password):
    # GraphQLClient to set and get controller io variables
    graphClient = MujinGraphClient(url, username, password)

    await asyncio.gather(
        graphClient.SubscribeRobotBridgesState(),
        _ManageProductionCycle(graphClient),
    )

async def _ManageProductionCycle(graphClient):
    """ Starts production cycle and queues a single order. Manages the location states for the order to be processed and dequeue the order result.

    Args:
        graphClient (MujinGraphClient): For checking Mujin IO state and setting IO.
    """
    # ProductionCycleOrderManager to manage order pointers, queue orders, and read order results
    orderManager = ProductionCycleOrderManager(graphClient)

    # initialize internal order queue pointers
    await orderManager.InitializeOrderPointers()

    # start production cycle
    await StartProductionCycle(graphClient)

    # queue an order
    pickLocationName = 'sc1' # name of the pick location set up in mujin controller
    placeLocationName = 'dc1' # name of the place location set up in mujin controller
    pickContainerId = 'source0001' # unique id of the source container, usually barcode of the box, or agv id, must not be constant when pick container changes
    placeContainerId = 'dest0001' # unique id of the destination pallet, usually barcode of the pallet, must not be constant when place contianer changes

    orderEntry = {
        'orderUniqueId': 'order%X' % int(time.time()), # unique id for this order
        'orderGroupId': 'group1', # group multiple orders to same place container
        'orderNumber': 1, # number of parts to pick
        'orderPartSizeX': 300,
        'orderPartSizeY': 450,
        'orderPartSizeZ': 250,
        'orderPackFormationName': 'packFormation1', # name of the pack formation
        'orderInputPartIndex': 1, # 1-based index into the pack formation, 1 meaning the first box in the pack
        'orderPickContainerId': pickContainerId,
        'orderPlaceContainerId': placeContainerId,
        'orderPickLocationName': pickLocationName,
        'orderPlaceLocationName': placeLocationName,
        # NOTE: additional parameters may be required depending on the configurations on mujin controller
    }
    orderManager.QueueOrder(orderEntry)
    log.info('Queued order: %r', orderEntry)

    await asyncio.gather(
        # handle location move in and out for source location
        HandleLocationMove(
            graphClient=graphClient,
            locationName=pickLocationName,
            containerId=pickContainerId, # use containerId matching the queued order request
            containerIdIOName='location1ContainerId', # location1 here is example, depend on mujin controller configuration
            hasContainerIOName='location1HasContainer', # location1 here is example, depend on mujin controller configuration
            moveInIOName='moveInLocation1Container', # location1 here is example, depend on mujin controller configuration
            moveOutIOName='moveOutLocation1Container', # location1 here is example, depend on mujin controller configuration
        ),
        # handle location move in and out for destination location
        HandleLocationMove(
            graphClient,
            locationName=placeLocationName,
            containerId=placeContainerId, # use containerId matching the queued order request
            containerIdIOName='location2ContainerId', # location2 here is example, depend on mujin controller configuration
            hasContainerIOName='location2HasContainer', # location2 here is example, depend on mujin controller configuration
            moveInIOName='moveInLocation2Container', # location2 here is example, depend on mujin controller configuration
            moveOutIOName='moveOutLocation2Container', # location2 here is example, depend on mujin controller configuration
        ),
        # dequeue order results
        DequeueOrderResults(orderManager),
    )

async def StartProductionCycle(graphClient):
    """ Starts production cycle.

    Args:
        graphClient (MujinGraphClient): For checking Mujin IO state and setting IO.
    """
    # start production cycle
    if not graphClient.sentIoMap.get('isRunningProductionCycle'):
        graphClient.SetControllerIOVariables([
            ('startProductionCycle', True)
        ])

    # wait for production cycle to start running
    while not graphClient.sentIoMap.get('isRunningProductionCycle'):
        await asyncio.sleep(0) # non-blocking sleep, allow next scheduled coroutine to run

    # set trigger off
    graphClient.SetControllerIOVariables([
        ('startProductionCycle', False)
    ])

async def DequeueOrderResults(orderManager):
    """ Dequeues order results in the order result queue.

    Args:
        orderManager (ProductionCycleOrderManager): For dequeuing order results and managing order pointers.
    """
    while True:
        # read the order result
        resultEntry = orderManager.DequeueOrderResult()
        if resultEntry is not None:
            log.info('Read order result: %r', resultEntry)

        await asyncio.sleep(0) # non-blocking sleep, allow next scheduled coroutine to run

async def HandleLocationMove(graphClient, locationName, containerId, containerIdIOName, hasContainerIOName, moveInIOName, moveOutIOName):
    """ Handles state management of a location upon move-in and move-out request sent from Mujin.

    Args:
        graphClient (MujinGraphClient): For checking Mujin IO state and setting location state IO.
        locationName (str): Name of this location for printing.
        containerId (str): ID of the container to move in to this location. Should be consistent with the queued order information.
        containerIdIOName (str): IO name used to set this location's container ID value.
        hasContainerIOName (str): IO name used to set this location's hasContainer .
        moveInIOName (str): IO name used to get and check for move-in request for this location.
        moveOutIOName (str): IO name used to get and check for move-out request for this location.
    """
    hasContainer = graphClient.sentIoMap.get(hasContainerIOName)
    while True:
        ioNameValues = []
        isMoveIn = graphClient.sentIoMap.get(moveInIOName)
        isMoveOut = graphClient.sentIoMap.get(moveOutIOName)

        # handle move in
        if isMoveIn and not hasContainer:
            ioNameValues += [
                (containerIdIOName, containerId), # set container ID
                (hasContainerIOName, True),       # hasContainer set True
            ]
            hasContainer = True
            log.info('Moved in container "%s" to location "%s"', containerId, locationName)

        # handle move out
        elif isMoveOut and hasContainer:
            ioNameValues += [
                (containerIdIOName, ''),     # reset container ID
                (hasContainerIOName, False), # hasContainer set False
            ]
            hasContainer = False
            log.info('Moved out container "%s" of location "%s"', containerId, locationName)

        # set ioNameValues
        if len(ioNameValues) > 0:
            graphClient.SetControllerIOVariables(ioNameValues)

        await asyncio.sleep(0) # non-blocking sleep, allow next scheduled coroutine to run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example code to run one order on production cycle')
    parser.add_argument('--logLevel', type=str, default='DEBUG', help='The python log level, e.g. DEBUG, VERBOSE, ERROR, INFO, WARNING, CRITICAL (default: %(default)s)')
    parser.add_argument('--url', type=str, default='http://127.0.0.1', help='URL of the controller (default: %(default)s)')
    parser.add_argument('--username', type=str, default='mujin', help='Username to login with (default: %(default)s)')
    parser.add_argument('--password', type=str, default='mujin', help='Password to login with (default: %(default)s)')
    options = parser.parse_args()

    logging.basicConfig(level=options.logLevel)
    asyncio.run(_RunMain(options.url, options.username, options.password))
