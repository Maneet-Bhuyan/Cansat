import asyncio
import websockets
import time
import random

# Ensure this matches your backend's exact WebSocket route
WS_URL = "ws://127.0.0.1:8000/ws/serial" 

async def stress_test():
    try:
        # Connect to the FastAPI WebSocket bridge
        async with websockets.connect(WS_URL) as websocket:
            print(f"Successfully connected to {WS_URL}")
            print("Sending 500 rapid telemetry packets...")
            
            start_time = time.time()
            
            # Send 500 packets in rapid succession
            for i in range(500):
                temp = round(random.uniform(20.0, 35.0), 2)
                pressure = round(random.uniform(900.0, 1013.25), 2)
                altitude = round(random.uniform(0.0, 500.0), 2)
                
                # Simulating raw CanSat serial format (e.g., "25.5,1013.25,150.0")
                telemetry_string = f"{temp},{pressure},{altitude}"
                
                await websocket.send(telemetry_string)
                
                # Wait just 10 milliseconds between sends to stress the server
                await asyncio.sleep(0.01) 
            
            end_time = time.time()
            print("Stress Test Complete!")
            print(f"Total time taken: {end_time - start_time:.2f} seconds")
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(stress_test())