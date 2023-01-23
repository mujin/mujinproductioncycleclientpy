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
        return requests.post(
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
        parameterValues = self._GetControllerIOVariables([parameterName])
        return parameterValues[0]

    def GetControllerIOVariables(self, parameterNames):
        parameterValues = self._GetControllerIOVariables(parameterNames)
        return dict(zip(parameterNames, parameterValues))

class ProductionCycleOrderManager(object):
    orderQueueIOName = 'productionQueue1Order'
    resultQueueIOName = 'productionQueue1Result'

    orderReadPointerIOName = 'location1OrderReadPointer'
    orderWritePointerIOName = 'location1OrderWritePointer'
    resultReadPointerIOName = 'location1OrderResultReadPointer'
    resultWritePointerIOName = 'location1OrderResultWritePointer'

    orderWritePointer = 0
    resultReadPointer = 0
    queueLength = 0

    _graphQLClient = None

    def __init__(self, graphQLClient):
        self._graphQLClient = graphQLClient
        self.InitializeOrderPointers()

    def _IncrementPointer(self, pointerValue):
        pointerValue += 1
        if pointerValue > self.queueLength:
            pointerValue = 1
        return pointerValue

    def InitializeOrderPointers(self):
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
        
        for pointerValue, orderPointerIOName in [
            (self.orderWritePointer, self.orderWritePointerIOName),
            (self.resultReadPointer,  self.resultReadPointerIOName),
            (orderReadPointer, self.orderReadPointerIOName),
            (resultWritePointer, self.resultWritePointerIOName),
        ]:
            if pointerValue < 1 or pointerValue > self.queueLength:
                raise Exception('Production cycle queue pointers are invalid, "%s" signal has value %r' % (orderPointerIOName, pointerValue))

    def QueueOrder(self, orderEntry):
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
