import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum
import sys
import os

student_id = "6310301020"


# State 
S_OFF       = 'OFF'
S_READY     = 'READY'
S_FAULT     = 'FAULT'
S_FILLWATER = 'FILLWATER'
S_HEATWATER = 'HEATWATER'
S_WASH      = 'WASH'
S_RINSE     = 'RINSE'
S_SPIN      = 'SPIN'
S_STOP      = 'STOP'

# Function
S_DOORCLOSED            = 'DOORCLOSE'
S_FULLLEVELDETECTED     = 'FULLLEVELDETECTED'
S_TEMPERATUREREACHED    = 'TEMPERATUREREACHED'
S_FUNCTIONCOMPLETED     = 'FUNCTIONCOMPLETED'
S_TIMEOUT               = 'TIMEOUT'
S_MOTORFAILURE          = 'MOTORFAILURE'
S_FAULTCLEARED          = 'FAULTCLEARED'

async def publish_message(serial, client, app, action, name, value):
    print(f"{time.ctime()} - PUBLISH [{serial}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : serial,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{serial}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{serial}"
                        , payload=json.dumps(payload))

async def monitor(client):
    while True:
        await asyncio.sleep(10)
        payload = {
                    "action"    : "get",
                    "project"   : student_id,
                    "model"     : "model-01",
                }
        print(f"{time.ctime()} - PUBLISH - GET ALL MACHINE STATUS")
        await client.publish(f"v1cdti/app/get/{student_id}/model-01/"
                            , payload=json.dumps(payload))

async def listen(client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/app/get/{student_id}/model-01/+")
        print(f"{time.ctime()} SUB topic: v1cdti/app/get/{student_id}/model-01/+")

        async for message in messages:
            m_decode = json.loads(message.payload)

            if message.topic.matches(f"v1cdti/app/get/{student_id}/model-01/+"):
                #print(f"{time.ctime()} - MQTT - [{m_decode['project']}] {m_decode['serial']} : {m_decode['name']} => {m_decode['value']}")

            
                if (m_decode['name']=="STATUS" and m_decode['value']=="OFF"):
                    await publish_message( m_decode['serial'], client, "hw", "set", "STATUS", "READY")
                    await asyncio.sleep(2)

                elif (m_decode['name']=="STATUS" and m_decode['value']=="FILLWATER"):
                    await publish_message( m_decode['serial'], client, "hw", "set", "STATUS",S_FULLLEVELDETECTED)
                    await asyncio.sleep(2)

                elif (m_decode['name']=="STATUS" and m_decode['value']=="HEATWATER"):
                    await publish_message( m_decode['serial'], client, "hw", "set", "STATUS",S_TEMPERATUREREACHED)
                    await asyncio.sleep(2)

                      
           
async def main():
    async with aiomqtt.Client("broker.hivemq.com") as client:
        await asyncio.gather(listen(client), monitor(client))

asyncio.run(main())