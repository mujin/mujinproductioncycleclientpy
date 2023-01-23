#!/usr/bin/env python
import time
from graphql import GraphQLClient, ProductionCycleOrderManager

def _Main():

    controllerUrl = 'http://localhost' # URL of Mujin controller
    # GraphQLClient to set and get controller io variables
    graphQLClient = GraphQLClient(controllerUrl=controllerUrl)
    # ProductionCycleOrderManager to manage order pointers, queue orders, and read order results
    orderManager = ProductionCycleOrderManager(graphQLClient)

    # start production cycle
    while not graphQLClient.GetControllerIOVariable('isRunningProductionCycle'):
        graphQLClient.SetControllerIOVariables([
            ('startProductionCycle', True)
        ])
        time.sleep(0.1)

    # after production cycle is running, set trigger off
    graphQLClient.SetControllerIOVariables([
        ('startProductionCycle', False)
    ])

    # queue an order
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

    # set source location and destination location container IDs matching the sent orderEntry
    graphQLClient.SetControllerIOVariables([
        ('location1ContainerId', sourceContainerId),
        ('location2ContainerId', destContainerId),
    ])

    # handle move in for source and destination locations
    handledMoveInForSource = False
    handledMoveInForDest = False
    while not handledMoveInForSource or not handledMoveInForDest:
        ioNameValues = []

        # handle move in for source location
        if not handledMoveInForSource and graphQLClient.GetControllerIOVariable('moveInLocation1Container'):
            ioNameValues += [
                ('location1HasContainer', True), # hasContainer set True
            ]
            handledMoveInForSource = True
            print('Moved in "%s" to source location.' % sourceContainerId)

        # handle move in for destination location
        if not handledMoveInForDest and graphQLClient.GetControllerIOVariable('moveInLocation2Container'):
            ioNameValues += [
                ('location2HasContainer', True), # hasContainer set True
            ]
            handledMoveInForDest = True
            print('Moved in "%s" to destination location.' % destContainerId)

        # set ioNameValues over graphQL
        if len(ioNameValues) > 0:
            graphQLClient.SetControllerIOVariables(ioNameValues)
        time.sleep(0.1)

    # handle move out for source and destination locations
    handledMoveOutForSource = False
    handledMoveOutForDest = False
    while not handledMoveOutForSource or not handledMoveOutForDest:
        ioNameValues = []

        # handle move out for source location
        if not handledMoveOutForSource and graphQLClient.GetControllerIOVariable('moveOutLocation1Container'):
            ioNameValues += [
                ('location1ContainerId', ''),     # reset container ID
                ('location1HasContainer', False), # hasContainer set False
            ]
            handledMoveOutForSource = True
            print('Moved out source location.')

        # handle move in for destination location
        if not handledMoveOutForDest and graphQLClient.GetControllerIOVariable('moveOutLocation2Container'):
            ioNameValues += [
                ('location2ContainerId', '')      # reset container ID
                ('location2HasContainer', False), # hasContainer set False
            ]
            handledMoveOutForDest = True
            print('Moved out destination location.')

        # set ioNameValues over graphQL
        if len(ioNameValues) > 0:
            graphQLClient.SetControllerIOVariables(ioNameValues)
        time.sleep(0.1)

    # read the order result
    resultEntry = None
    while resultEntry is None:
        resultEntry = orderManager.ReadNextOrderResult()
    print('Queued order: %r' % orderEntry)

if __name__ == "__main__":
    _Main()
