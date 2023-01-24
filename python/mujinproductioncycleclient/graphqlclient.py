# -*- coding: utf-8 -*-

import base64
import json
import requests
import websockets

import logging
log = logging.getLogger(__name__)


class MujinGraphClient(object):

    _url = None # passed in url of mujin controller
    _graphEndpoint = None # URL to http GraphQL endpoint on Mujin controller

    _headers = None # request headers information
    _cookies = None # request cookies information

    _websocket = None # WebSocketClientProtocol, used to subscribe to IO changes on Mujin controller
    _robotBridgeState = None # dict storing last received RobotBridgesState from subscription

    def __init__(self, url='http://127.0.0.1', username='mujin', password='mujin'):
        assert url.startswith('http://') or url.startswith('https://'), 'URL "%s" is invalid, should start with "http(s)://"' % url
        assert not url.endswith('/'), 'URL "%s" is invalid, should not end with "/"' % url
        self._url = url
        self._graphEndpoint = '%s/api/v2/graphql' % url
        self._robotBridgeState = {}

        usernamePassword = '%s:%s' % (username, password)
        encodedUsernamePassword = base64.b64encode(usernamePassword.encode('utf-8')).decode('ascii')
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': 'token',
            'Authorization': 'Basic %s' % encodedUsernamePassword,
        }
        self._cookies = {
            'csrftoken': 'token',
        }

    @property
    def receivedIoMap(self):
        return dict(self._robotBridgeState.get('receivediovalues', {}))

    @property
    def sentIoMap(self):
        return dict(self._robotBridgeState.get('sentiovalues', {}))

    async def SubscribeRobotBridgesState(self):
        """ Subscribes to IO changes on Mujin controller.
        """
        query = '''
            subscription {
                SubscribeRobotBridgesState {
                    sentiovalues
                    receivediovalues
                }
            }
        '''
        # create the client for executing the subscription

        async def _Subscribe(callbackFunction):
            async with websockets.connect(
                uri='ws%s' % self._graphEndpoint[len('http'):], # replace http:// with ws://, https:// with wss://
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
                        log.debug('received connection_ack')
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
            self._robotBridgeState = response.get('data', {}).get('SubscribeRobotBridgesState') or {}

        await _Subscribe(_Callback)

    def SetControllerIOVariables(self, ioNameValues):
        """ Sends GraphQL query to set IO variables to Mujin controller.

        Args:
            ioNameValues (list(tuple(ioName, ioValue))): List of tuple(ioName, ioValue) for IO variables to set
        """
        query = '''
            mutation SetControllerIOVariables($parameters: Any!) {
                CommandRobotBridges(command: "SetControllerIOVariables", parameters: $parameters)
            }
        '''
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'ioNameValues': ioNameValues,
                },
            },
        })
        response = requests.post(
            url=self._graphEndpoint,
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
        query = '''
            mutation GetControllerIOVariable($parameters: Any!) {
                CommandRobotBridges(command: "GetControllerIOVariable", parameters: $parameters)
            }
        '''
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'parametername': ioName,
                },
            },
        })
        response = requests.post(
            url=self._graphEndpoint,
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
        query = '''
            mutation GetControllerIOVariables($parameters: Any!) {
                CommandRobotBridges(command: "GetControllerIOVariables", parameters: $parameters)
            }
        '''
        data = json.dumps({
            'query': query,
            'variables': {
                'parameters': {
                    'parameternames': ioNames,
                },
            },
        })
        response = requests.post(
            url=self._graphEndpoint,
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
