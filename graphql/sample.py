#!/usr/bin/env python

import asyncio
from graphql import MujinGraphqlClient, ProductionCycleOrderManager

async def _Main():
    host = 'localhost' # IP of Mujin controller

    # GraphQLClient to set and get controller io variables
    graphqlClient = MujinGraphqlClient(host=host)

    await asyncio.gather(
        graphqlClient.SubscribeRobotBridgesState(),
        _ManageProductionCycle(graphqlClient),
    )

async def _ManageProductionCycle(graphqlClient):
    """ Starts production cycle and queues a single order. Manages the location states for the order to be processed and dequeue the order result.

    Args:
        graphqlClient (MujinGraphqlClient): For checking Mujin IO state and setting IO.
    """
    # ProductionCycleOrderManager to manage order pointers, queue orders, and read order results
    orderManager = ProductionCycleOrderManager(graphqlClient)

    # initialize internal order queue pointers
    await orderManager.InitializeOrderPointers()

    # start production cycle
    await StartProductionCycle(graphqlClient)

    # queue an order
    orderEntry = QueueOrder(orderManager)

    await asyncio.gather(
        # handle location move in and out for source location
        HandleLocationMove(
            graphqlClient=graphqlClient,
            locationName='source',
            containerId=orderEntry['orderPickContainerId'], # use containerId from the queued order request
            containerIdIOName='location1ContainerId',
            hasContainerIOName='location1HasContainer',
            moveInIOName='moveInLocation1Container',
            moveOutIOName='moveOutLocation1Container',
        ),
        # handle location move in and out for destination location
        HandleLocationMove(
            graphqlClient,
            locationName='destination',
            containerId=orderEntry['orderPlaceContainerId'], # use containerId from the queued order request
            containerIdIOName='location2ContainerId',
            hasContainerIOName='location2HasContainer',
            moveInIOName='moveInLocation2Container',
            moveOutIOName='moveOutLocation2Container',
        ),
        # dequeue order results
        DequeueOrderResults(orderManager),
    )

async def StartProductionCycle(graphqlClient):
    """ Starts production cycle.

    Args:
        graphqlClient (MujinGraphqlClient): For checking Mujin IO state and setting IO.
    """
    # start production cycle
    if not graphqlClient.sentIoMap.get('isRunningProductionCycle'):
        graphqlClient.SetControllerIOVariables([
            ('startProductionCycle', True)
        ])

    # wait for production cycle to start running
    while not graphqlClient.sentIoMap.get('isRunningProductionCycle'):
        await asyncio.sleep(0.01) # sleep this coroutine to allow other coroutines to run

    # set trigger off
    graphqlClient.SetControllerIOVariables([
        ('startProductionCycle', False)
    ])

def QueueOrder(orderManager):
    """ Queues an order to order request queue.

    Args:
        orderManager (ProductionCycleOrderManager): For queuing order requests and managing order pointers.

    Returns:
        dict: Order information that was queued.
    """
    sourceContainerId = 'source0001'
    destContainerId = 'dest0001'
    orderEntry = {
        'orderUniqueId': 'order0001',
        'orderPickContainerId': sourceContainerId,
        'orderPlaceContainerId': destContainerId,
        'orderNumber': 1,
        'orderPickLocationName': 'sc1',
        'orderPlaceLocationName': 'dc1',
    }
    orderManager.QueueOrder(orderEntry)
    print('Queued order: %r' % orderEntry)
    return orderEntry

async def DequeueOrderResults(orderManager):
    """ Dequeues order results in the order result queue.

    Args:
        orderManager (ProductionCycleOrderManager): For dequeuing order results and managing order pointers.
    """
    while True:
        # read the order result
        if (resultEntry := orderManager.DequeueOrderResult()) is not None:
            print('Read order result: %r' % resultEntry)

        await asyncio.sleep(0.01) # sleep this coroutine to allow other coroutines to run

async def HandleLocationMove(graphqlClient, locationName, containerId, containerIdIOName, hasContainerIOName, moveInIOName, moveOutIOName):
    """ Handles state management of a location upon move-in and move-out request sent from Mujin.

    Args:
        graphqlClient (MujinGraphqlClient): For checking Mujin IO state and setting location state IO.
        locationName (str): Name of this location for printing.
        containerId (str): ID of the container to move in to this location. Should be consistent with the queued order information.
        containerIdIOName (str): IO name used to set this location's container ID value.
        hasContainerIOName (str): IO name used to set this location's hasContainer .
        moveInIOName (str): IO name used to get and check for move-in request for this location.
        moveOutIOName (str): IO name used to get and check for move-out request for this location.
    """
    hasContainer = graphqlClient.sentIoMap.get(hasContainerIOName)
    while True:
        ioNameValues = []
        isMoveIn = graphqlClient.sentIoMap.get(moveInIOName)
        isMoveOut = graphqlClient.sentIoMap.get(moveOutIOName)

        # handle move in
        if isMoveIn and not hasContainer:
            ioNameValues += [
                (containerIdIOName, containerId), # set container ID
                (hasContainerIOName, True),       # hasContainer set True
            ]
            hasContainer = True
            print('Moved in "%s" to %s location.' % (containerId, locationName))

        # handle move out
        elif isMoveOut and hasContainer:
            ioNameValues += [
                (containerIdIOName, ''),     # reset container ID
                (hasContainerIOName, False), # hasContainer set False
            ]
            hasContainer = False
            print('Moved out %s of %s location.' % (containerId, locationName))

        # set ioNameValues over graphQL
        if len(ioNameValues) > 0:
            graphqlClient.SetControllerIOVariables(ioNameValues)

        await asyncio.sleep(0.01) # sleep this coroutine to allow other coroutines to run

if __name__ == "__main__":
    asyncio.run(_Main())
