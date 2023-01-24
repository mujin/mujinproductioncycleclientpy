# How To Access The Mujin GraphQL APIs

Writing and reading I/O signals can be performed by HTTP requests that contain specific GraphQL queries. These HTTP requests can be performed in multiple ways, including but not limited to the command line using cURL, Python's requests library, any web browser (such as Google Chrome), etc., as long the required credentials are provided. These methods are explained below.

## GraphQL Playground

The GraphQL playground can be used to experiment with different queries interactively. Please visit `http://controller1234/api/v2/graphql/playground` on a web browser that has a network connection to the Mujin controller to use the playground. Make sure to replace controller1234  in the URL with the correct IP address pointing to the Mujin controller. The username and password for the playground is mujin

The playground is also helpful for debugging possible syntax errors in your queries and checking the detailed API documentation through the DOCS button available on the right side of the screen. Users can type the GraphQL mutation into the top left box, and the parameters into the bottom left box. Later, the users can press the play button (▶), and the results will be available on the right side.

Here is a sample GraphQL query to set location states:

```graphql
mutation SetControllerIOVariables($parameters: Any!) {
  CommandRobotBridges(command: "SetControllerIOVariables", parameters: $parameters)
}
```

Using the following variables to the query:

```json
{
  "parameters": {
    "ioNameValues": [
      ["location1HasContainer", 0],
      ["location1ContainerId", "abc"]
    ]
  }
}
```

## cURL

cURL can be used to perform the queries and get a JSON response in return.

Users can execute the sample GraphQL mentioned above using the following cURL command.

Note that the query needs to be wrapped by another JSON dictionary: `{"query": {"your JSON escaped query string"}}`.

Further note that the parameters need to be wrapped by another JSON dictionary: `{"variables": {"parameters": {"key": "value"}}}`.

```bash
curl \
  --request POST 'http://controller1234/api/v2/graphql' \
  --user 'mujin:mujin' \
  --header 'X-CSRFToken: token' \
  --header 'Cookie: csrftoken=token' \
  --header 'Content-Type: application/json' \
  --data \
   '{
       "query": "mutation SetControllerIOVariables($parameters: Any!) { CommandRobotBridges(command: \"SetControllerIOVariables\", parameters: $parameters) }", 
       "variables": {"parameters":{"ioNameValues":[["location1HasContainer",0],["location1ContainerId","abc"]]}}
   }'
```

Executing the cURL command above produces the following output.

```bash
$ curl -v \
  --request POST 'http://controller1234/api/v2/graphql' \
  --user 'mujin:mujin' \
  --header 'X-CSRFToken: token' \
  --header 'Cookie: csrftoken=token' \
  --header 'Content-Type: application/json' \
  --data \
   '{
       "query": "mutation SetControllerIOVariables($parameters: Any!) { CommandRobotBridges(command: \"SetControllerIOVariables\", parameters: $parameters) }",
       "variables": {"parameters":{"ioNameValues":[["location1HasContainer",0],["location1ContainerId","abc"]]}}
   }'
*   Trying 10.2.12.65:80...
* Connected to controller1234 (10.2.12.65) port 80 (#0)
* Server auth using Basic with user 'mujin'
> POST /api/v2/graphql HTTP/1.1
> Host: controller1234
> Authorization: Basic bXVqaW46bXVqaW4=
> User-Agent: curl/7.74.0
> Accept: */*
> X-CSRFToken: token
> Cookie: csrftoken=token
> Content-Type: application/json
> Content-Length: 279
> 
* upload completely sent off: 279 out of 279 bytes
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< Server: mujinwebstack/2.2.21.b4eb5a8cd2619adbc4fa4c79b403e655cc6694c7 (controller1234)
< Set-Cookie: jwttoken=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYmYiOjE2NzQ0NDU0MTcsInVzZXJuYW1lIjoibXVqaW4ifQ.n-k7kENWTOkl93_82V38CtIAyrcc255umk7iUSHvQlo; Path=/; Max-Age=1209600; HttpOnly
< Vary: Accept-Encoding
< X-Content-Type-Options: nosniff
< Date: Mon, 10 Jan 2023 09:43:37 GMT
< Content-Length: 133
< 
{"data":{"CommandRobotBridges":{"commandid":130093343,"custom":0,"elapsedTimeInPause":0.0,"elapsedtime":0.0,"finishedTimeStamp":0}}}
```

## Python

Using Python is another option to perform the queries/subscriptions and get JSON responses in return.

### Query

Users can execute the sample GraphQL mentioned above using the following Python code. The username and password used for authentication is mujin The value of the CSRF token can be anything as long as the value of the csrftoken cookie and the X-CSRFToken header matches.

```python
import json
import requests


# GraphQL query we want to execute
query = '''
    mutation SetControllerIOVariables($parameters: Any!) {         
         CommandRobotBridges(command: "SetControllerIOVariables", parameters: $parameters)
    }
'''

# GraphQL query variables
variables = {
    "parameters": {
        "ioNameValues": [["location1HasContainer", 0], ["location1ContainerId", "abc"]]
    }
}

# replace controller1234 with the Mujin controller's IP address
controllerGraphQLEndpoint = "http://controller1234/api/v2/graphql"

# execute the query
response = requests.post(
    url=controllerGraphQLEndpoint,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": "token",
    },
    cookies={"csrftoken": "token"},
    auth=requests.auth.HTTPBasicAuth("mujin", "mujin"),
    data=json.dumps({"query": query, "variables": variables}),
)

# print the result
print(response.json())
```

```bash
$ python example.py 
{u'data': {u'CommandRobotBridges': {u'elapsedtime': 0.0, u'finishedTimeStamp': 0, u'commandid': 130091921, u'elapsedTimeInPause': 0.0, u'custom': 0}}
```

### Subscription

The subscriptions are handled through persistent WebSocket connections between the user and the Mujin controller. Using WebSocket allows the Mujin controller to deliver I/O state changes to the users with low latency and no re-initialization overhead. Users do not need to repeatedly make new HTTP requests to check the status of I/O values. Instead, subscriptions efficiently deliver the latest I/O values to the users. The communication channel between the user and the Mujin controller stays open as long as one side decides to close the channel.

#### Upgrading An Existing HTTP Connection To Use WebSocket

A WebSocket connection can be created by upgrading an existing HTTP connection. In order to upgrade an HTTP connection to a WebSocket, `Connection: Upgrade`, `Upgrade: websocket`, `Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==`, and `Sec-WebSocket-Version: 13` headers need to be supplied.

If the upgrade request is successful, the Mujin controller is going to reply with HTTP/1.1 101 Switching Protocols. After this point, the communication will be based on the WebSocket protocol.

```bash
$ curl -v \
    http://controller1234/api/v2/graphql \
    --user 'mujin:mujin' \
    --header "Connection: Upgrade" \
    --header "Upgrade: websocket" \
    --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
    --header "Sec-WebSocket-Version: 13" 
* Connected to controller1234 (10.2.12.65) port 80 (#0)
* Server auth using Basic with user 'mujin'
> GET /api/v2/graphql HTTP/1.1
> Host: controller1234
> Authorization: Basic bXVqaW46bXVqaW4=
> User-Agent: curl/7.74.0
> Accept: */*
> Connection: Upgrade
> Upgrade: websocket
> Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==
> Sec-WebSocket-Version: 13
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 101 Switching Protocols
< Upgrade: websocket
< Connection: Upgrade
< Sec-WebSocket-Accept: qGEgH3En71di5rrssAZTmtRTyFk=
< 
```

#### How To Start A GraphQL Subscription On A WebSocket Connection

Mujin controller supports `graphql-ws` and `graphql-transport-ws` transport protocols to serve GraphQL subscriptions. Here are messages that need to be exchanged between the User and Mujin controller to start a GraphQL subscription:

1. The user sends connection_init message to initialize the currently established WebSocket connection.
1. Mujin controller replies with connection_ack message to indicate that the connection initialization request is acknowledged.
1. The user sends a start message and a subscription query inside the message's payload key.
1. Mujin controller replies with ka message to indicate that the subscription request is received and the connection will be kept alive in order to send the changes to the user.
1. Mujin controller pushes the I/O state changes to the user with subsequent messages.
1. Mujin controller sends ka messages periodically to keep the current connection alive.
1. The communication channel is left open until either side closes the channel with a stop message.

#### GraphQL Subscription Python Example

A WebSocket client library (such as `websockets`) can be utilized to subscribe to I/O changes.

In the example below, a WebSocket client is used to subscribe to the Mujin controller sent & received I/O state. The values received through a callback function (see the example below) can be used to determine changes in the I/O values. By using a subscription, the program will always have access to the latest I/O values without issuing new HTTP requests each time I/O values need to be checked.

```bash
$ python -m pip install websockets
Collecting websockets
  Downloading websockets-10.4-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (106 kB)
     |████████████████████████████████| 106 kB 20.2 MB/s 
Installing collected packages: websockets
Successfully installed websockets-10.4
```

```python
import json
import asyncio
import base64
import websockets
 
 
# GraphQL subscription we want to execute
subscription = '''
    subscription {
        SubscribeRobotBridgesState {
            sentiovalues
            receivediovalues
        }
    }
'''
 
# produce a basic authentication header
def _EncodeBasicAuthorization(username, password):
    usernamePassword = '%s:%s' % (username, password)
    encodedUsernamePassword = base64.b64encode(usernamePassword.encode("utf-8")).decode("ascii")
    return 'Basic %s' % encodedUsernamePassword
 
# replace controller1234 with the Mujin controller's IP address
controllerGraphQLEndpoint = "ws://controller1234/api/v2/graphql"
 
# create the client for executing the subscription
async def Subscribe(callbackFunction):
    async with websockets.connect(
        uri=controllerGraphQLEndpoint,
        subprotocols=["graphql-ws"],
        extra_headers={"Authorization": _EncodeBasicAuthorization("mujin", "mujin")},
    ) as websocket:
        # print the initial HTTP request headers
        print("Initial request headers:\n%s" % websocket.request_headers)
        # print the response to the HTTP upgrade request
        print("Initial response headers:\n%s" % websocket.response_headers)

        # send the WebSocket connection initialization request
        await websocket.send(json.dumps({"type": "connection_init", "payload": {}}))
 
        # start a new subscription on the WebSocket connection
        await websocket.send(json.dumps({"type": "start", "payload": {"query": subscription}}))
 
        # read incoming messages
        async for response in websocket:
            data = json.loads(response)
            if data["type"] == "connection_ack":
                print("Received connection-acknowledge ('connection_ack') message")
            elif data["type"] == "ka":
                print("Received keep-alive ('ka') message")
            else:
                # call the callback function to process the payload
                callbackFunction(data["payload"])
 
def Callback(response):
    # we could further process the changes here
    # just print the changes for now
    print("State:\n%s" % json.dumps(response))
 
# execute the subscription in an async way
# the callback function will keep receiving the state values each time a new state value is received.
asyncio.run(Subscribe(Callback))
```

As seen in the program output, it first upgrades the HTTP connection and then uses the WebSocket protocol.

```bash
$ python example.py 
Initial request headers:
Host: controller1234
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: Vc+Y5ATsG8Q9BonyfnPkUA==
Sec-WebSocket-Version: 13
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
Sec-WebSocket-Protocol: graphql-ws
Authorization: Basic bXVqaW46bXVqaW4=
User-Agent: Python/3.9 websockets/10.4


Initial response headers:
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: ksY7bqRjkvDrTbMWfX43kBqlRvs=
Sec-WebSocket-Protocol: graphql-ws


Received connection-acknowledge ('connection_ack') message
State:
{"data": {"SubscribeRobotBridgesState": {"receivediovalues": [["startOrderCycle", false], ["orderIsPlaceContainerEmptyOnArrival", false], ["pause", false], ["stopImmediately", false], ["startMoveToHome", false], ["clearState", false], ["resume", false], ["preparationIsPlaceContainerEmptyOnArrival", false], ["startDetection", false], ["stopGripper", false], ["stopDetection", false], ["stopOrderCycle", false], ["startPreparation", false], ["resetError", false], ["airejector/1/isAirSavingEnabled", false], ["airejector/1/isPartPresent", false], ["airejector/2/isAirSavingEnabled", false], ["airejector/2/isPartPresent", false], ["airejector/3/isAirSavingEnabled", false], ["airejector/3/isPartPresent", false], ["airejector/4/isAirSavingEnabled", false], ["airejector/4/isPartPresent", false], ["MUJININ1", false], ["MUJININ2", false], ["MUJININ3", false], ["MUJININ4", false], ["MUJININ5", false], ["MUJININ6", false], ["MUJININ7", false], ["MUJININ8", false], ["orderNumber", 0], ["plcCommCounter", 51518], ["preparationOrderNumber", 0], ["airejector/1/ejectorCondition", 0], ["airejector/2/ejectorCondition", 0], ["airejector/3/ejectorCondition", 0], ["airejector/4/ejectorCondition", 0], ["airejector/1/pressureValue", -200], ["airejector/2/pressureValue", -100], ["airejector/3/pressureValue", -300], ["airejector/4/pressureValue", -200], ["orderPickContainerType", ""], ["orderPlaceLocation", ""], ["preparationPlaceContainerId", ""], ["orderPartType", ""], ["preparationPickLocation", ""], ["preparationPlaceContainerType", ""], ["orderPlaceContainerId", ""], ["orderPickLocation", ""], ["preparationPartType", ""], ["orderPlaceContainerType", ""], ["orderPickContainerId", ""], ["preparationPickContainerId", ""], ["preparationPickContainerType", ""], ["preparationPlaceLocation", ""]], "sentiovalues": [["isCycleReady", false], ["location1NotEmpty", false], ["isRunningOrderCycle", false], ["startPreparationReceived", false], ["location2NotEmpty", false], ["isRunningPreparation", false], ["location4NotEmpty", false], ["isPausing", false], ["location3DetectionRunning", false], ["isMoveToHomeRunning", false], ["clearStatePerformed", false], ["location4DetectionRunning", false], ["location1DetectionRunning", false], ["isAtHome", true], ["isGrabbingTarget", false], ["isError", false], ["location3NotEmpty", false], ["location2DetectionRunning", false], ["isModeAuto", false], ["isSystemReady", true], ["isRobotMoving", false], ["moveInLocationContainer", false], ["moveOutLocationContainer", false], ["airejector/1/suction", false], ["airejector/1/blow", false], ["airejector/2/suction", false], ["airejector/2/blow", false], ["airejector/3/suction", false], ["airejector/3/blow", false], ["airejector/4/suction", false], ["airejector/4/blow", false], ["MUJINOUT1", false], ["MUJINOUT2", false], ["MUJINOUT3", false], ["MUJINOUT4", false], ["MUJINOUT5", false], ["MUJINOUT6", false], ["MUJINOUT7", false], ["MUJINOUT8", false], ["returnOrderNumber", 0], ["numLeftInOrder", 0], ["errorcode", 0], ["commCounter", 13311], ["orderCycleFinishCode", 65535], ["numPutInDestination", 0], ["returnPreparationOrderNumber", 0], ["returnPickContainerType", ""], ["detailcode", ""], ["returnPartType", ""], ["returnPreparationPickLocation", ""], ["returnPreparationPlaceContainerId", ""], ["returnPlaceContainerId", ""], ["returnPlaceContainerType", ""], ["returnPreparationPickContainerId", ""], ["returnPreparationPlaceContainerType", ""], ["returnPreparationPickContainerType", ""], ["returnPreparationPlaceLocation", ""], ["returnPreparationPartType", ""], ["returnPlaceLocation", ""], ["returnPickLocation", ""], ["returnPickContainerId", ""]]}}}
State:
{"data": {"SubscribeRobotBridgesState": {"receivediovalues": [["startOrderCycle", false], ["orderIsPlaceContainerEmptyOnArrival", false], ["pause", false], ["stopImmediately", false], ["startMoveToHome", false], ["clearState", false], ["resume", false], ["preparationIsPlaceContainerEmptyOnArrival", false], ["startDetection", false], ["stopGripper", false], ["stopDetection", false], ["stopOrderCycle", false], ["startPreparation", false], ["resetError", false], ["airejector/1/isAirSavingEnabled", false], ["airejector/1/isPartPresent", false], ["airejector/2/isAirSavingEnabled", false], ["airejector/2/isPartPresent", false], ["airejector/3/isAirSavingEnabled", false], ["airejector/3/isPartPresent", false], ["airejector/4/isAirSavingEnabled", false], ["airejector/4/isPartPresent", false], ["MUJININ1", false], ["MUJININ2", false], ["MUJININ3", false], ["MUJININ4", false], ["MUJININ5", false], ["MUJININ6", false], ["MUJININ7", false], ["MUJININ8", false], ["orderNumber", 0], ["plcCommCounter", 51518], ["preparationOrderNumber", 0], ["airejector/1/ejectorCondition", 0], ["airejector/2/ejectorCondition", 0], ["airejector/3/ejectorCondition", 0], ["airejector/4/ejectorCondition", 0], ["airejector/1/pressureValue", -200], ["airejector/2/pressureValue", -100], ["airejector/3/pressureValue", -300], ["airejector/4/pressureValue", -200], ["orderPickContainerType", ""], ["orderPlaceLocation", ""], ["preparationPlaceContainerId", ""], ["orderPartType", ""], ["preparationPickLocation", ""], ["preparationPlaceContainerType", ""], ["orderPlaceContainerId", ""], ["orderPickLocation", ""], ["preparationPartType", ""], ["orderPlaceContainerType", ""], ["orderPickContainerId", ""], ["preparationPickContainerId", ""], ["preparationPickContainerType", ""], ["preparationPlaceLocation", ""]], "sentiovalues": [["isCycleReady", false], ["location1NotEmpty", false], ["isRunningOrderCycle", false], ["startPreparationReceived", false], ["location2NotEmpty", false], ["isRunningPreparation", false], ["location4NotEmpty", false], ["isPausing", false], ["location3DetectionRunning", false], ["isMoveToHomeRunning", false], ["clearStatePerformed", false], ["location4DetectionRunning", false], ["location1DetectionRunning", false], ["isAtHome", true], ["isGrabbingTarget", false], ["isError", false], ["location3NotEmpty", false], ["location2DetectionRunning", false], ["isModeAuto", false], ["isSystemReady", true], ["isRobotMoving", false], ["moveInLocationContainer", false], ["moveOutLocationContainer", false], ["airejector/1/suction", false], ["airejector/1/blow", false], ["airejector/2/suction", false], ["airejector/2/blow", false], ["airejector/3/suction", false], ["airejector/3/blow", false], ["airejector/4/suction", false], ["airejector/4/blow", false], ["MUJINOUT1", false], ["MUJINOUT2", false], ["MUJINOUT3", false], ["MUJINOUT4", false], ["MUJINOUT5", false], ["MUJINOUT6", false], ["MUJINOUT7", false], ["MUJINOUT8", false], ["returnOrderNumber", 0], ["numLeftInOrder", 0], ["errorcode", 0], ["commCounter", 13313], ["orderCycleFinishCode", 65535], ["numPutInDestination", 0], ["returnPreparationOrderNumber", 0], ["returnPickContainerType", ""], ["detailcode", ""], ["returnPartType", ""], ["returnPreparationPickLocation", ""], ["returnPreparationPlaceContainerId", ""], ["returnPlaceContainerId", ""], ["returnPlaceContainerType", ""], ["returnPreparationPickContainerId", ""], ["returnPreparationPlaceContainerType", ""], ["returnPreparationPickContainerType", ""], ["returnPreparationPlaceLocation", ""], ["returnPreparationPartType", ""], ["returnPlaceLocation", ""], ["returnPickLocation", ""], ["returnPickContainerId", ""]]}}}

... the rest of the output is truncated
```

In the given WebSocket subscription example, the program reads an unlimited number of state changes from the subscription. However, it is possible to limit the number of messages read by adding a limit condition to the Subscribe() function, as shown below.

```python
# create the client for executing the subscription
async def Subscribe(callbackFunction):
    async with websockets.connect(
        uri=controllerGraphQLEndpoint,
        subprotocols=["graphql-ws"],
        extra_headers={"Authorization": GetBasicAuthToken("mujin", "mujin")},
    ) as websocket:
        # send the WebSocket connection initialization request
        await websocket.send(json.dumps({"type": "connection_init", "payload": {}}))

        # start a new subscription on the WebSocket connection
        await websocket.send(json.dumps({"type": "start", "payload": {"query": subscription}}))

        # read incoming messages
        numberOfMessagesRead = 0
        async for response in websocket:
            if numberOfMessagesRead > 2:
                # read up to 3 messages
                break

            data = json.loads(response)
            if data["type"] == "connection_ack":
                print("received connection-acknowledge ('connection_ack') message")
            elif data["type"] == "ka":
                print("received keep-alive ('ka') message")
            else:
                # call the callback function to process the payload
                callbackFunction(data["payload"])

            # call the callback function to process the payload
            numberOfMessagesRead += 1
            callbackFunction(data["payload"])

        # stop the subscription on the WebSocket connection
        await websocket.send(json.dumps({"type": "stop", "payload": {}}))
```
