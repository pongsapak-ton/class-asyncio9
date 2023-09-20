import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum

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

# Function
S_DOORCLOSED            = 'DOORCLOSE'
S_FULLLEVELDETECTED     = 'FULLLEVELDETECTED'
S_TEMPERATUREREACHED    = 'TEMPERATUREREACHED'
S_FUNCTIONCOMPLETED     = 'FUNCTIONCOMPLETED'
S_TIMEOUT               = 'TIMEOUT'
S_MOTORFAILURE          = 'MOTORFAILURE'
S_FAULTCLEARED          = 'FAULTCLEARED'

async def publish_message(w, client, app, action, name, value):
    await asyncio.sleep(1)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUB topic: v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL} payload: {name}:{value}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))

async def fillwater(w, filltime=10):
    print(f"{time.ctime()} - [{w.SERIAL}] Waiting for fill water maxinum {filltime} seconds")
    await asyncio.sleep(filltime)

async def door(w, doortime=10):
    print(f"{time.ctime()} - [{w.SERIAL}] Waiting for door close")
    await asyncio.sleep(doortime)


async def fillwater(w, filltime=10):
    print(f"{time.ctime()} - [{w.SERIAL}] Waiting for fill water maxinum {filltime} seconds")
    await asyncio.sleep(filltime)

async def waterheater(w, heatertime=10):
    print(f"{time.ctime()}- [{w.SERIAL}] Water Heater detect {heatertime} seconds")
    await asyncio.sleep(heatertime)

async def wash_rinse_spine(w, washtime=10):
    print(f"{time.ctime()}- [{w.SERIAL}] Failure detect {washtime} seconds")
    await asyncio.sleep(washtime)  
   
class MachineStatus(Enum):
    pressure = round(random.uniform(2000,3000), 2)
    temperature = round(random.uniform(25.0,40.0), 2)

class MachineMaintStatus(Enum):
    filter = random.choice(["clear", "clogged"])
    noise = random.choice(["quiet", "noisy"])

class WashingMachine:
    def __init__(self, serial):
        self.SERIAL = serial
        self.STATE = 'OFF'
        self.Task = None

    async def waiting_task(self,w):
        self.Task = asyncio.create_task(fillwater(w))
        return self.Task
    async def Cancel_Task(self):
        self.Task.cancel()

async def CoroWashingMachine(w, client,event):

    while True:
        #wait_next = round(10*random.random(),2)
        
        if w.STATE == S_OFF:
            # print(f"{time.ctime()} - [{w.SERIAL}-{w.STATE}]... {wait_next} seconds.")
            print(f"{time.ctime()} - [{w.SERIAL}-{w.STATE}] Waiting to start...")
            # await asyncio.sleep(wait_next)
            # continue
            await event.wait()
            event.clear()
            continue


        if w.STATE == S_FAULT:
            print(f"{time.ctime()} - [{w.SERIAL}-{w.STATE}] Waiting to start... {wait_next} seconds.")
            await event.wait()
            event.clear()
            continue


        if w.STATE == S_READY:
            print(f"{time.ctime()} - [{w.SERIAL}-{w.STATE}]")

            await publish_message(w, client, "app", "get", "STATUS", "READY")
            await publish_message(w, client, "app", "get", "LID", "CLOSE")
            w.STATE = 'FILLWATER'
            await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")
            # door close
            
            # fill water untill full level detected within 10 seconds if not full then timeout 
            try:
                async with asyncio.timeout(10):
                    await fillwater(w)
     
            except TimeoutError:
                if w.STATE == 'FULLLEVELDETECTED' :
                    print(f"{time.ctime()} - Water level full")
                    await publish_message(w, client, "app", "get", "STATUS", "WATERHEATER")

                else:
                    print(f"{time.ctime()} - Water level fault")
                    await publish_message(w, client, "app", "get", "STATUS", "FAULT")
                    w.STATE = 'FAULT'
                    continue
            
            await publish_message(w, client, "app", "get", "STATUS", "HEATWATER")
            try:
                async with asyncio.timeout(10):
                    await waterheater(w)
            except TimeoutError:
                if w.STATE == 'TEMPERATUREREACHED' : 
                    print(f"{time.ctime()} - Water heater reached ")
                    await publish_message(w, client, "app", "get", "STATUS", "WASH")
                    
                else:
                    print(f"{time.ctime()} - Water heater fault")
                    await publish_message(w, client, "app", "get", "STATUS", "FAULT")
                    w.STATE = 'FAULT'
                    continue
            
         
            
            try:
                async with asyncio.timeout(10):
                    await wash_rinse_spine(w)
            except TimeoutError:
                if w.STATE == 'OUTOFBALANCE':
                    await publish_message(w, client, "app", "get", "STATUS", "OUTOFBALANCE")
                    w.STATE = 'FAULT'
                    continue
                else:
                    await publish_message(w, client, "app", "get", "STATUS", "RINSE")



        # rinse 10 seconds, if motor failure detect then fault
            try:
                async with asyncio.timeout(10):
                    await wash_rinse_spine(w)
            except TimeoutError:
                if w.STATE == 'MOTORFAILURE':
                    await publish_message(w, client, "app", "get", "STATUS", "MOTORFAILURE")
                    w.STATE = 'FAULT'
                    continue
                else:
                    await publish_message(w, client, "app", "get", "STATUS", "SPIN")
                    


        # spin 10 seconds, if motor failure detect then fault
            try:
                async with asyncio.timeout(10):
                    await wash_rinse_spine(w)
            except TimeoutError:
                if w.STATE == 'MOTORFAILURE':
                    await publish_message(w, client, "app", "get", "STATUS", "MOTORFAILURE")
                    w.STATE = 'FAULT'
                    continue
                else:
                    await publish_message(w, client, "app", "get", "STATUS", "OFF")
                    
                    
        # When washing is in FAULT state, wait until get FAULTCLEARED

        # wash 10 seconds, if out of balance detected then fault

        # rinse 10 seconds, if motor failure detect then fault

        # spin 10 seconds, if motor failure detect then fault

        # When washing is in FAULT state, wait until get FAULTCLEARED

        # wait_next = round(5*random.random(),2)
        # print(f"sleep {wait_next} seconds")
        # await asyncio.sleep(wait_next)
     
         # Wait until the waiter task is finished.
     

async def listen(w, client,event):
    async with client.messages() as messages:
        print(f"{time.ctime()} - SUB topic: v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")
                if (m_decode['name']=="STATUS" and m_decode['value']==S_READY):
                    w.STATE = S_READY
                    event.set()
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_FULLLEVELDETECTED):
                    # w.Cancel_Task
                    w.STATE = S_HEATWATER 
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_TEMPERATUREREACHED):
                    w.STATE = S_TEMPERATUREREACHED
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_MOTORFAILURE):
                    w.STATE = S_MOTORFAILURE
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_OUTOFBALANCE):
                    w.STATE = S_OUTOFBALANCE   
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_FAULT):
                    w.STATE = S_FAULT
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_FAULTCLEARED):
                    w.STATE = S_FAULTCLEARED
                elif (m_decode['name']=="STATUS" and m_decode['value']==S_OFF):
                    w.STATE = "OFF"
                else:
                    print(f"{time.ctime()} - ERROR MQTT [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")

async def main():
    w = WashingMachine(serial='SN-001')
    Events = asyncio.Event()
    async with aiomqtt.Client("broker.hivemq.com") as client:
        await asyncio.gather(listen(w, client,Events) , CoroWashingMachine(w, client,Events)
                             )

asyncio.run(main())