#!/usr/bin/env python

import asyncio
from graphql import MujinGraphqlClient, ProductionCycleOrderManager

async def _Main():
    host = 'localhost:1234' # TODO: IP of Mujin controller

    # GraphQLClient to set and get controller io variables
    graphqlClient = MujinGraphqlClient(host=host)

    await asyncio.gather(
        graphqlClient.SubscribeRobotBridgesState(),
        _ManageProductionCycle(graphqlClient),
    )

async def _ManageProductionCycle(graphqlClient):
    # ProductionCycleOrderManager to manage order pointers, queue orders, and read order results
    orderManager = ProductionCycleOrderManager(graphqlClient)

    # start production cycle
    StartProductionCycle(graphqlClient)

    # queue an order
    orderEntry = QueueOrder(orderManager)

    await asyncio.gather(
        # handle location move in and out for source location
        HandleLocationMove(
            graphqlClient=graphqlClient,
            locationName='source',
            containerId=orderEntry['orderPickContainerId'],
            containerIdIOName='location1ContainerId',
            hasContainerIOName='location1HasContainer',
            moveInIOName='moveInLocation1Container',
            moveOutIOName='moveOutLocation1Container',
        ),
        # handle location move in and out for destination location
        HandleLocationMove(
            graphqlClient,
            locationName='destination',
            containerId=orderEntry['orderPlaceContainerId'],
            containerIdIOName='location2ContainerId',
            hasContainerIOName='location2HasContainer',
            moveInIOName='moveInLocation2Container',
            moveOutIOName='moveOutLocation2Container',
        ),
        DequeueOrderResults(orderManager),
    )

def StartProductionCycle(graphqlClient):
    # start production cycle
    if not graphqlClient.sentIoMap.get('isRunningProductionCycle'):
        graphqlClient.SetControllerIOVariables([
            ('startProductionCycle', True)
        ])
    # wait for production cycle to start running
    while not graphqlClient.sentIoMap.get('isRunningProductionCycle'):
        pass
    # set trigger off
    graphqlClient.SetControllerIOVariables([
        ('startProductionCycle', False)
    ])

def QueueOrder(orderManager):
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
    while True:
        # read the order result
        if (resultEntry := orderManager.DequeueOrderResult()) is not None:
            print('Read order result: %r' % resultEntry)

        await asyncio.sleep(0.01) # sleep this coroutine to allow other coroutines to run

async def HandleLocationMove(graphqlClient, locationName, containerId, containerIdIOName, hasContainerIOName, moveInIOName, moveOutIOName):
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
