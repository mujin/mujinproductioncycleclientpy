import json
import requests

class GraphQLClient(object):
    _url = None     # URL to graphQL endpoint on Mujin controller
    _headers = None # request headers information
    _cookies = None # request cookies information
    _auth = None    # request auth information

    def __init__(self, controllerUrl='http://localhost', username='mujin', password='mujin'):
        self._url = '%s/api/v2/graphql' % controllerUrl
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': 'token',
        }
        self._cookies = {
            'csrftoken': 'token'
        }
        self._auth = requests.auth.HTTPBasicAuth(username, password)

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
        requests.post(
            url=self._url,
            headers=self._headers,
            cookies=self._cookies,
            auth=self._auth,
            data=data,
        )

    def _GetControllerIOVariables(self, parameterNames):
        query = """
            mutation GetControllerIOVariables($parameters: Any!) {
                CommandRobotBridges(command: "GetControllerIOVariables", parameters: $parameters)
            }
        """
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'parameternames': parameterNames
                }
            }
        })
        response = requests.post(
            url=self._url,
            headers=self._headers,
            cookies=self._cookies,
            auth=self._auth,
            data=data,
        )
        responseJson = response.json()
        if 'errors' in responseJson:
            # command failed
            raise Exception('Failed to get io variables for parameterNames %r. response: %s' % (parameterNames, responseJson))
        parameterValues = responseJson.get('data', {}).get('CommandRobotBridges', {}).get('parametervalue')
        if parameterValues is None or len(parameterNames) != len(parameterValues):
            # failed to fetch parameter values
            raise Exception('Failed to get io variables for parameterNames %r. response: %r' % (parameterNames, responseJson))
        return parameterValues

    def GetControllerIOVariable(self, parameterName):
        """ Sends GraphQL query to get single IO variable from Mujin controller.

        Args:
            parameterName (str): Name of IO variable to get.

        Returns:
            Value of IO variable.
        """
        parameterValues = self._GetControllerIOVariables([parameterName])
        return parameterValues[0]

    def GetControllerIOVariables(self, parameterNames):
        """ Sends GraphQL query to get multiple IO variables from Mujin controller.

        Args:
            parameterNames (list(str)): List of names for IO variables to get.

        Returns:
            dict: Mapping of IO name to IO value for queried IO variables.
        """
        parameterValues = self._GetControllerIOVariables(parameterNames)
        return dict(zip(parameterNames, parameterValues))

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
        self.InitializeOrderPointers()

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

    def InitializeOrderPointers(self):
        """ Sends GraphQL query to get order queue pointers and order queue length
        """
        # send graphQL query
        ioNameValues = self._graphQLClient.GetControllerIOVariables([
            self.orderReadPointerIOName,
            self.orderWritePointerIOName,
            self.resultReadPointerIOName,
            self.resultWritePointerIOName,
            self.orderQueueIOName,
        ])
        self.queueLength = len(ioNameValues[self.orderQueueIOName])
        self.orderWritePointer = ioNameValues[self.orderWritePointerIOName]
        self.resultReadPointer = ioNameValues[self.resultReadPointerIOName]
        orderReadPointer = ioNameValues[self.orderReadPointerIOName]
        resultWritePointer = ioNameValues[self.resultWritePointerIOName]

        # verify order queue pointer values are valid
        for pointerValue, orderPointerIOName in [
            (self.orderWritePointer, self.orderWritePointerIOName),
            (self.resultReadPointer,  self.resultReadPointerIOName),
            (orderReadPointer, self.orderReadPointerIOName),
            (resultWritePointer, self.resultWritePointerIOName),
        ]:
            if pointerValue < 1 or pointerValue > self.queueLength:
                raise Exception('Production cycle order queue pointers are invalid, "%s" signal has value %r' % (orderPointerIOName, pointerValue))

    def QueueOrder(self, orderEntry):
        """ Queues an order entry to the order queue.

        Args:
            orderEntry (dict): Order information to queue to the system.
        """
        # queue order to next entry in order queue and increment the order write pointer
        orderReadPointer = self._graphQLClient.GetControllerIOVariable(self.orderReadPointerIOName)

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

    def ReadNextOrderResult(self):
        """ Reads next result entry in order result queue.

        returns:
            dict: Order result information. None if there is no result entry to be read.
        """
        # reads next order result from order result queue and increment the order result read pointer
        resultEntry = None
        resultWritePointer = self._graphQLClient.GetControllerIOVariable(self.resultWritePointerIOName)
        if self.resultReadPointer != resultWritePointer:
            orderResultQueueEntryIOName = '%s[%d]' % (self.resultQueueIOName, self.resultReadPointer - 1)
            resultEntry = self._graphQLClient.GetControllerIOVariable(orderResultQueueEntryIOName)
            self.resultReadPointer = self._IncrementPointer(self.resultReadPointer)
            self._graphQLClient.SetControllerIOVariables([
                (self.resultReadPointerIOName, self.resultReadPointer)
            ])
        return resultEntry
