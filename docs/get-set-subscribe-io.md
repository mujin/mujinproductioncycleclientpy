# Mujin Controller I/O Subscription and I/O Setting

I/O variables can be used to manage various Mujin controller functionality, such as production cycle & orders, as well as the locations within the robot cell.

Users can get the current I/O values, set the I/O values, and subscribe to changes in the I/O values. Example GraphQL queries for each operation, and example results are shown below.

## Setting I/O

```graphql
mutation SetControllerIOVariables($parameters: Any!) {
  CommandRobotBridges(command: "SetControllerIOVariables", parameters: $parameters)
}
```

Variables:

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

Result:

```json
{
  "data": {
    "CommandRobotBridges": {
      "commandid": 13915838,
      "custom": 3,
      "elapsedTimeInPause": 0,
      "elapsedtime": 0,
      "finishedTimeStamp": 0
    }
  }
}
```

## Getting I/O

Getting I/O is slow and repeatedly getting I/O should be avoided whenever possible. Use I/O subscription instead.

```graphql
mutation GetControllerIOVariables($parameters: Any!) {
  CommandRobotBridges(command: "GetControllerIOVariables", parameters: $parameters)
}
```

Variables:

```json
{
  "parameters": {
    "parameternames": [
      "location1ContainerId",
      "location1HasContainer"
    ]
  }
}
```

Result:

```json
{
  "data": {
    "CommandRobotBridges": {
      "commandid": 13916246,
      "elapsedTimeInPause": 0,
      "elapsedtime": 0,
      "finishedTimeStamp": 0,
      "parametervalue": [
        "abc",
        false
      ]
    }
  }
}
```

## Subscribing to I/O

```graphql
subscription {
  SubscribeRobotBridgesState {
    sentiovalues 
    receivediovalues
  }
}
```

```json
{
  "data": {
    "SubscribeRobotBridgesState": {
      "receivediovalues": [
        [
          "startProductionCycle",
          false
        ],
        [
          "stopProductionCycle",
          false
        ],
        [
          "location1OrderReadPointer",
          1
        ],
        [
          "location1OrderWritePointer",
          1
        ],
        [
          "location1OrderResultReadPointer",
          1
        ],
        [
          "location1OrderResultWritePointer",
          1
        ]
      ],
      "sentiovalues": [
        [
          "startProductionCycle",
          false
        ],
        [
          "isRunningProductionCycle",
          false
        ],
        [
          "isPausingProductionCycle",
          false
        ],
        [
          "isProcessingProductionCycle",
          false
        ]
      ]
    }
  }
}
```
