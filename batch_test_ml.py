import requests
import time
import random

API_URL = "http://127.0.0.1:8000/api/predict"

# 1. Generate a batch of mock CanSat data
batch_data = []
for i in range(100): 
    batch_data.append({
        "temp": random.uniform(20.0, 35.0),
        "pressure": random.uniform(900.0, 1013.25),
        "altitude": random.uniform(0.0, 500.0)
    })

print(f"Starting batch test with {len(batch_data)} records...")
start_time = time.time()

# 2. Send the batch to your API
success_count = 0
for data in batch_data:
    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 200:
            success_count += 1
        else:
            print(f"Server rejected the data!")
            print(f"Status Code: {response.status_code}")
            print(f"Reason: {response.text}")
            break 
    except Exception as e:
        print(f"Request failed: {e}")
        break

end_time = time.time()

# 3. Output the results
if success_count > 0 or response.status_code == 200:
    print(f"Batch Test Complete!")
    print(f"Successful predictions: {success_count}/{len(batch_data)}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")