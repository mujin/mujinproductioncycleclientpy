#!/usr/bin/env python
import time
from graphql import GraphQLClient, ProductionCycleOrderManager

def _Main():

    controllerUrl = 'http://localhost' # URL of Mujin controller
    graphQLClient = GraphQLClient(controllerUrl=controllerUrl)
    orderManager = ProductionCycleOrderManager(graphQLClient)

    # start production cycle
    while not graphQLClient.GetControllerIOVariable('isRunningProductionCycle'):
        graphQLClient.SetControllerIOVariables([
            ('startProductionCycle', True)
        ])
        time.sleep(0.1)
    graphQLClient.SetControllerIOVariables([
        ('startProductionCycle', False)
    ])

    # queue an order
    orderEntry = {
        'orderUniqueId': 'order0001',
        'orderPickContainerId': 'source0001',
        'orderNumber': 1,
        'orderPickLocationName': 'sc1',
        'orderPlaceLocationName': 'dc1',
    }
    orderManager.QueueOrder(orderEntry)
    print('Queued order: %r' % orderEntry)

    # handle move in for source and destination locations
    handledMoveInForSource = False
    handledMoveInForDest = False
    while not handledMoveInForSource or not handledMoveInForDest:
        ioNameValues = []

        # handle move in for source location
        if not handledMoveInForSource and graphQLClient.GetControllerIOVariable('moveInLocation1Container'):
            ioNameValues += [
                ('location1HasContainer', True),
                ('location1ContainerId', 'source0001')
            ]
            handledMoveInForSource = True

        # handle move in for destination location
        if not handledMoveInForDest and graphQLClient.GetControllerIOVariable('moveInLocation2Container'):
            ioNameValues += [
                ('location2HasContainer', True),
                ('location2ContainerId', 'dest0001')
            ]
            handledMoveInForDest = True

        # send move in ios
        if len(ioNameValues) > 0:
            graphQLClient.SetControllerIOVariables(ioNameValues)
        time.sleep(0.1)

    # handle move out
    handledMoveOutForSource = False
    handledMoveOutForDest = False
    while not handledMoveOutForSource or not handledMoveOutForDest:
        ioNameValues = []

        # handle move in for source location
        if not handledMoveOutForSource and graphQLClient.GetControllerIOVariable('moveOutLocation1Container'):
            ioNameValues += [
                ('location1HasContainer', False),
                ('location1ContainerId', '')
            ]
            handledMoveOutForSource = True

        # handle move in for destination location
        if not handledMoveOutForDest and graphQLClient.GetControllerIOVariable('moveOutLocation2Container'):
            ioNameValues += [
                ('location2HasContainer', False),
                ('location2ContainerId', '')
            ]
            handledMoveOutForDest = True

        # send move in ios
        if len(ioNameValues) > 0:
            graphQLClient.SetControllerIOVariables(ioNameValues)
        time.sleep(0.1)

    # check the order result
    resultEntry = None
    while resultEntry is None:
        resultEntry = orderManager.ReadNextOrderResult()
    print('Queued order: %r' % orderEntry)

if __name__ == "__main__":
    _Main()