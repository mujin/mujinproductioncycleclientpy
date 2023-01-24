# -*- coding: utf-8 -*-

import asyncio
import time

import logging
log = logging.getLogger(__name__)


class ProductionCycleOrderManager(object):
    _orderQueueIOName = None  # io name of order request queue
    _resultQueueIOName = None # io name of order result queue

    _orderReadPointerIOName = None   # io name of order request read pointer
    _orderWritePointerIOName = None  # io name of order request write pointer
    _resultReadPointerIOName = None  # io name of order result read pointer
    _resultWritePointerIOName = None # io name of order result write pointer

    _orderWritePointer = 0 # value of current order request write pointer
    _resultReadPointer = 0 # value of current order result write pointer
    _queueLength = 0       # length of order request queue

    _graphClient = None # instance of graphqlclient.GraphClient

    def __init__(self, graphClient, queueIndex=1):
        self._graphClient = graphClient
        self._orderQueueIOName = 'productionQueue%dOrder' % queueIndex
        self._resultQueueIOName = 'productionQueue%dResult' % queueIndex
        self._orderReadPointerIOName = 'location%dOrderReadPointer' % queueIndex
        self._orderWritePointerIOName = 'location%dOrderWritePointer' % queueIndex
        self._resultReadPointerIOName = 'location%dOrderResultReadPointer' % queueIndex
        self._resultWritePointerIOName = 'location%dOrderResultWritePointer' % queueIndex

    def _IncrementPointer(self, pointerValue):
        """ Increments value for an order queue pointer. Wraps around length of order queue.

        Args:
            pointerValue (int): Value of order queue pointer to be incremented.

        Returns:
            int: Incremented pointerValue.
        """
        pointerValue += 1
        if pointerValue > self._queueLength:
            pointerValue = 1
        return pointerValue

    async def InitializeOrderPointers(self, timeout=5):
        """ Sends GraphQL query to get order queue pointers and order queue length
        """
        starttime = time.time()

        # initialize order queue length from order queue
        orderQueue = self._graphClient.GetControllerIOVariable(self._orderQueueIOName)
        self._queueLength = len(orderQueue)

        # initalize order pointers
        initializedOrderPointers = False
        while not initializedOrderPointers:
            self._orderWritePointer = self._graphClient.receivedIoMap.get(self._orderWritePointerIOName) or 0
            self._resultReadPointer = self._graphClient.receivedIoMap.get(self._resultReadPointerIOName) or 0
            orderReadPointer = self._graphClient.receivedIoMap.get(self._orderReadPointerIOName) or 0
            resultWritePointer = self._graphClient.receivedIoMap.get(self._resultWritePointerIOName) or 0

            # verify order queue pointer values are valid
            initializedOrderPointers = True
            for pointerValue, orderPointerIOName in [
                (self._orderWritePointer, self._orderWritePointerIOName),
                (self._resultReadPointer, self._resultReadPointerIOName),
                (orderReadPointer, self._orderReadPointerIOName),
                (resultWritePointer, self._resultWritePointerIOName),
            ]:
                if pointerValue < 1 or pointerValue > self._queueLength:
                    initializedOrderPointers = False
                    if time.time() - starttime > timeout:
                        raise Exception('Production cycle order queue pointers are invalid, "%s" signal has value %r' % (orderPointerIOName, pointerValue))
                await asyncio.sleep(0) # non-blocking sleep, allow next scheduled coroutine to run

    def QueueOrder(self, orderEntry):
        """ Queues an order entry to the order queue.

        Args:
            orderEntry (dict): Order information to queue to the system.
        """
        # queue order to next entry in order queue and increment the order write pointer
        orderReadPointer = self._graphClient.receivedIoMap.get(self._orderReadPointerIOName) or 0

        # check if order queue is full
        if self._IncrementPointer(self._orderWritePointer) == orderReadPointer:
            raise Exception('Failed to queue new order entry because order queue is full (length=%d).' % self._queueLength)

        # queue order entry and increment order write pointer
        orderQueueEntryIOName = '%s[%d]' % (self._orderQueueIOName, self._orderWritePointer-1)
        self._orderWritePointer = self._IncrementPointer(self._orderWritePointer)
        self._graphClient.SetControllerIOVariables([
            (orderQueueEntryIOName, orderEntry),
            (self._orderWritePointerIOName, self._orderWritePointer)
        ])

    def DequeueOrderResult(self):
        """ Dequeues next result entry in order result queue.

        returns:
            dict: Order result information. None if there is no result entry to be read.
        """
        # reads next order result from order result queue and increment the order result read pointer
        resultEntry = None
        resultWritePointer = self._graphClient.receivedIoMap.get(self._resultWritePointerIOName) or 0
        if self._resultReadPointer != resultWritePointer:
            orderResultQueueEntryIOName = '%s[%d]' % (self._resultQueueIOName, self._resultReadPointer - 1)
            resultEntry = self._graphClient.GetControllerIOVariable(orderResultQueueEntryIOName)
            self._resultReadPointer = self._IncrementPointer(self._resultReadPointer)
            self._graphClient.SetControllerIOVariables([
                (self._resultReadPointerIOName, self._resultReadPointer)
            ])
        return resultEntry
