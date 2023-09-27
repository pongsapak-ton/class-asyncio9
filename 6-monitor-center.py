import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum

student_id = "6310301020"


async def listen(client):
    async with client.messages() as messages:
        print(f'{time.ctime()} - Subscribe for topic v1cdti/app/monitor/{student_id}/model-01/+')
        await client.subscribe(f"v1cdti/app/monitor/{student_id}/model-01/+")
        async for message in messages:
            mgs_decode = json.loads(message.payload)
            # print(mgs_decode)
            if message.topic.matches(f"v1cdti/app/monitor/{student_id}/model-01/+"):
                print(f"{time.ctime()} FROM MQTT: [{mgs_decode['serial']}] {mgs_decode['name']} - {mgs_decode['value']}]")
                
async def main():
    async with aiomqtt.Client("broker.hivemq.com") as client:
       await asyncio.gather(listen(client))

asyncio.run(main())