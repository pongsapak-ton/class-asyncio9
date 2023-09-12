import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum

student_id = "6310301020"

class MachineStatus():
    pressure = round(random.uniform(2000,3000), 2)
    temperature = round(random.uniform(25.0,40.0), 2)
    def __init__(self):
        self.fulldetect = 0
        self.heatreach = 1

class MachineMaintStatus(Enum):
    filter = random.choice(["clear", "clogged"])
    noise = random.choice(["quiet", "noisy"])

class WashingMachine:
    def __init__(self, serial):
        self.MACHINE_STATUS = 'OFF'
        self.FAULT_TYPE = 'Timeout'
        self.SERIAL = serial
       
    async def waiting(self):
        try:
            print(f'{time.ctime()} - Start Waiting')
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            print(f'{time.ctime()} - Waiting function is canceled!')
            raise

        print(f'{time.ctime()} - Waiting 10 second already! -> TIMEOUT!')
        self.MACHINE_STATUS = 'FAULT'
        self.FAULT_TYPE = 'TIMEOUT'

       
        print(f'{time.ctime()} - [{self.SERIAL}] STATUS: {self.MACHINE_STATUS}')


    async def waiting_task(self):
        self.task = asyncio.create_task(self.waiting())
        return self.task

    async def cancel_waiting(self):
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            print(f'{time.ctime()} - Cancel-Waiting')
        
    

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))

async def CoroWashingMachine(w,sensor, client):
    while True:
        wait_next = round(10*random.random(),2)
        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... {wait_next} seconds.")
        await asyncio.sleep(wait_next)
        if w.MACHINE_STATUS == 'OFF':
            continue
        if w.MACHINE_STATUS == 'READY':
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
            await publish_message(w, client, "app", "get", "STATUS", "READY")
            # door close
            
            w.MACHINE_STATUS = 'FillWater'
            await publish_message(w, client, "app", "get", "STATUS",  "FillWater") 
            wait = w.waiting_task()
            await wait

        if w.MACHINE_STATUS == 'WaterHeat':
                wait = w.waiting_task()
                await wait
                while w.MACHINE_STATUS == 'WaterHeat':
                    await asyncio.sleep(2)
        
        if w.MACHINE_STATUS == 'FAULT':
            await publish_message(w, client, 'app', 'get', 'FAULT', w.FAULT_TYPE)
            while w.MACHINE_STATUS == 'FAULT':
                print(f"{time.ctime()} - [{w.SERIAL}] Waiting to clear fault...")
                await asyncio.sleep(1)

        if w.MACHINE_STATUS == 'WASHING':
            continue
                

           
            # fill water untill full level detected within 10 seconds if not full then timeout 
          
            # heat water until temperature reach 30 celcius within 10 seconds if not reach 30 celcius then timeout

            # wash 10 seconds, if out of balance detected then fault

            # rinse 10 seconds, if motor failure detect then fault

            # spin 10 seconds, if motor failure detect then fault

            # ready state set 

            # When washing is in FAULT state, wait until get FAULTCLEARED

            #w.MACHINE_STATUS = 'OFF'
            #await publish_message(w, client, "app", "get", "STATUS", w.MACHINE_STATUS)
            #continue
            

async def listen(w,sensor, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")
                if m_decode['name'] == "STATUS":
                    w.MACHINE_STATUS = m_decode['value']

                if w.MACHINE_STATUS == "FillWater":
                    if m_decode['name'] == "WaterLevel":
                        sensor.fulldetected = m_decode['value']
                        if sensor.fulldetected == "WaterFull":
                            w.MACHINE_STATUS = 'WaterHeat'
                            print(f'{time.ctime()} - [{w.SERIAL}] STATUS: {w.MACHINE_STATUS}')
                            await publish_message(w, client, 'app', 'get', 'STATUS', w.MACHINE_STATUS)
                        await w.cancel_waiting()

                if w.MACHINE_STATUS == 'WaterHeat':
                    if m_decode['name'] == "Temperature":
                        sensor.heatreach = m_decode['value']
                        if sensor.heatreach == 'REACHED':
                            w.MACHINE_STATUS = 'WASH'
                            print(f'{time.ctime()} - [{w.SERIAL}] STATUS: {w.MACHINE_STATUS}')
                            await publish_message(w, client, 'app', 'get', 'STATUS', w.MACHINE_STATUS)

                        await w.cancel_waiting()

                if m_decode['name'] == "Fault":
                    if m_decode['value'] == 'Clear':
                        w.MACHINE_STATUS = 'OFF'
                        await publish_message(w, client, 'app', 'get', 'STATUS', w.MACHINE_STATUS)




                   
async def main():
    w = WashingMachine(serial='SN-001')
    sensor = MachineStatus()
    async with aiomqtt.Client("broker.hivemq.com") as client:
        await asyncio.gather(listen(w,sensor,client) , CoroWashingMachine(w,sensor, client))

asyncio.run(main())