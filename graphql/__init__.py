import asyncio
import base64
import json
import requests
import time
import websockets

class MujinGraphqlClient(object):
    _websocketUrl = None # URL to websocket GraphQL endpoint on Mujin controller
    _httpUrl = None      # URL to http GraphQL endpoint on Mujin controller
    _headers = None      # request headers information
    _cookies = None      # request cookies information

    _websocket = None # WebSocketClientProtocol, used to subscribe to IO changes on Mujin controller
    robotBridgeState = None # dict storing last received RobotBridgesState from subscription

    def __init__(self, host='localhost', username='mujin', password='mujin'):
        self._httpUrl = 'http://%s/api/v2/graphql' % host
        self._websocketUrl = 'ws://%s/api/v2/graphql' % host
        self.robotBridgeState = {}

        token = '%s:%s' % (username, password)
        encodedToken = base64.b64encode(token.encode('utf-8')).decode('ascii')
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': 'token',
            'Authorization': 'Basic %s' % encodedToken
        }
        self._cookies = {
            'csrftoken': 'token'
        }

    @property
    def receivedIoMap(self):
        return dict(self.robotBridgeState.get('receivediovalues', {}))

    @property
    def sentIoMap(self):
        return dict(self.robotBridgeState.get('sentiovalues', {}))

    async def SubscribeRobotBridgesState(self):
        """ Subscribes to IO changes on Mujin controller.
        """
        query = """
            subscription {
                SubscribeRobotBridgesState {
                    sentiovalues
                    receivediovalues
                }
            }
        """
        # create the client for executing the subscription
        async def _Subscribe(callbackFunction):
            async with websockets.connect(
                uri=self._websocketUrl,
                subprotocols=['graphql-ws'],
                extra_headers=self._headers,
            ) as websocket:
                self.websocket = websocket
                # send the WebSocket connection initialization request
                await websocket.send(json.dumps({'type': 'connection_init', 'payload': {}}))

                # start a new subscription on the WebSocket connection
                await websocket.send(json.dumps({'type': 'start', 'payload': {'query': query}}))

                # read incoming messages
                async for response in websocket:
                    data = json.loads(response)
                    if data['type'] == 'connection_ack':
                        print('received connection-acknowledge ("connection_ack") message')
                    elif data['type'] == 'ka':
                        # received keep-alive "ka" message
                        pass
                    else:
                        # call the calback function to process the payload
                        callbackFunction(data['payload'])

                # stop the subscription on the WebSocket connection
                await websocket.send(json.dumps({"type": "stop", "payload": {}}))

        def _Callback(response):
            # update with response robotBridgeState
            robotBridgeState = response.get('data', {}).get('SubscribeRobotBridgesState') or {}
            self.robotBridgeState.update(robotBridgeState)

        await _Subscribe(_Callback)

    def SetControllerIOVariables(self, ioNameValues):
        """ Sends GraphQL query to set IO variables to Mujin controller.

        Args:
            ioNameValues (list(tuple(ioName, ioValue))): List of tuple(ioName, ioValue) for IO variables to set
        """
        query = """
            mutation SetControllerIOVariables($parameters: Any!) {
                CommandRobotBridges(command: "SetControllerIOVariables", parameters: $parameters)
            }
        """
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'ioNameValues': ioNameValues
                }
            }
        })
        response = requests.post(
            url=self._httpUrl,
            headers=self._headers,
            cookies=self._cookies,
            data=data,
        )
        responseJson = response.json()
        if 'errors' in responseJson:
            # command failed
            raise Exception('Failed to set io variables for %r. response: %s' % (ioNameValues, responseJson))

    def GetControllerIOVariable(self, ioName):
        """ Sends GraphQL query to get single IO variable from Mujin controller.

        Args:
            ioName (str): Name of IO variable to get.

        Returns:
            Value of IO variable.
        """
        query = """
            mutation GetControllerIOVariable($parameters: Any!) {
                CommandRobotBridges(command: "GetControllerIOVariable", parameters: $parameters)
            }
        """
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'parametername': ioName
                }
            }
        })
        response = requests.post(
            url=self._httpUrl,
            headers=self._headers,
            cookies=self._cookies,
            data=data,
        )
        responseJson = response.json()
        if 'errors' in responseJson:
            # command failed
            raise Exception('Failed to get io variables for IO name %r. response: %s' % (ioName, responseJson))
        parameterValue = responseJson.get('data', {}).get('CommandRobotBridges', {}).get('parametervalue')
        if parameterValue is None:
            # failed to fetch parameter values
            raise Exception('Failed to get io variables for IO name %r. response: %r' % (ioName, responseJson))
        return parameterValue

    def GetControllerIOVariables(self, ioNames):
        """ Sends GraphQL query to get multiple IO variables from Mujin controller.

        Args:
            ioNames (list(str)): List of IO names for IO variables to get.

        Returns:
            dict: Mapping of IO name to IO value for queried IO variables.
        """
        query = """
            mutation GetControllerIOVariables($parameters: Any!) {
                CommandRobotBridges(command: "GetControllerIOVariables", parameters: $parameters)
            }
        """
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'parameternames': ioNames
                }
            }
        })
        response = requests.post(
            url=self._httpUrl,
            headers=self._headers,
            cookies=self._cookies,
            data=data,
        )
        responseJson = response.json()
        if 'errors' in responseJson:
            # command failed
            raise Exception('Failed to get io variables for IO names %r. response: %s' % (ioNames, responseJson))
        parameterValues = responseJson.get('data', {}).get('CommandRobotBridges', {}).get('parametervalue')
        if parameterValues is None or len(ioNames) != len(parameterValues):
            # failed to fetch parameter values
            raise Exception('Failed to get io variables for IO names %r. response: %r' % (ioNames, responseJson))
        return dict(zip(ioNames, parameterValues))

class ProductionCycleOrderManager(object):
    orderQueueIOName = 'productionQueue1Order'                    # io name of order request queue
    resultQueueIOName = 'productionQueue1Result'                  # io name of order result queue

    orderReadPointerIOName = 'location1OrderReadPointer'          # io name of order request read pointer
    orderWritePointerIOName = 'location1OrderWritePointer'        # io name of order request write pointer
    resultReadPointerIOName = 'location1OrderResultReadPointer'   # io name of order result read pointer
    resultWritePointerIOName = 'location1OrderResultWritePointer' # io name of order result write pointer

    orderWritePointer = 0 # value of current order request write pointer
    resultReadPointer = 0 # value of current order result write pointer
    queueLength = 0       # length of order request queue

    _graphQLClient = None # instance of GraphQLClient

    def __init__(self, graphQLClient):
        self._graphQLClient = graphQLClient

    def _IncrementPointer(self, pointerValue):
        """ Increments value for an order queue pointer. Wraps around length of order queue.

        Args:
            pointerValue (int): Value of order queue pointer to be incremented.

        Returns:
            int: Incremented pointerValue.
        """
        pointerValue += 1
        if pointerValue > self.queueLength:
            pointerValue = 1
        return pointerValue

    async def InitializeOrderPointers(self, timeout=5):
        """ Sends GraphQL query to get order queue pointers and order queue length
        """
        starttime = time.time()

        # initialize order queue length from order queue
        orderQueue = self._graphQLClient.GetControllerIOVariable(self.orderQueueIOName)
        self.queueLength = len(orderQueue)

        # initalize order pointers
        initializedOrderPointers = False
        while not initializedOrderPointers:
            self.orderWritePointer = self._graphQLClient.receivedIoMap.get(self.orderWritePointerIOName) or 0
            self.resultReadPointer = self._graphQLClient.receivedIoMap.get(self.resultReadPointerIOName) or 0
            orderReadPointer = self._graphQLClient.receivedIoMap.get(self.orderReadPointerIOName) or 0
            resultWritePointer = self._graphQLClient.receivedIoMap.get(self.resultWritePointerIOName) or 0

            # verify order queue pointer values are valid
            initializedOrderPointers = True
            for pointerValue, orderPointerIOName in [
                (self.orderWritePointer, self.orderWritePointerIOName),
                (self.resultReadPointer,  self.resultReadPointerIOName),
                (orderReadPointer, self.orderReadPointerIOName),
                (resultWritePointer, self.resultWritePointerIOName),
            ]:
                if pointerValue < 1 or pointerValue > self.queueLength:
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
        orderReadPointer = self._graphQLClient.receivedIoMap.get(self.orderReadPointerIOName) or 0

        # check if order queue is full
        if self._IncrementPointer(self.orderWritePointer) == orderReadPointer:
            raise Exception('Failed to queue new order entry because order queue is full (length=%d).' % self.queueLength)

        # queue order entry and increment order write pointer
        orderQueueEntryIOName = '%s[%d]' % (self.orderQueueIOName, self.orderWritePointer-1)
        self.orderWritePointer = self._IncrementPointer(self.orderWritePointer)
        self._graphQLClient.SetControllerIOVariables([
            (orderQueueEntryIOName, orderEntry),
            (self.orderWritePointerIOName, self.orderWritePointer)
        ])

    def DequeueOrderResult(self):
        """ Dequeues next result entry in order result queue.

        returns:
            dict: Order result information. None if there is no result entry to be read.
        """
        # reads next order result from order result queue and increment the order result read pointer
        resultEntry = None
        resultWritePointer = self._graphQLClient.receivedIoMap.get(self.resultWritePointerIOName) or 0
        if self.resultReadPointer != resultWritePointer:
            orderResultQueueEntryIOName = '%s[%d]' % (self.resultQueueIOName, self.resultReadPointer - 1)
            resultEntry = self._graphQLClient.GetControllerIOVariable(orderResultQueueEntryIOName)
            self.resultReadPointer = self._IncrementPointer(self.resultReadPointer)
            self._graphQLClient.SetControllerIOVariables([
                (self.resultReadPointerIOName, self.resultReadPointer)
            ])
        return resultEntry
