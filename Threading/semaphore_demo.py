"""
SEMAPHORE Example - Parking Lot Management
Demonstrates controlling access to limited resources
"""
import threading
import time
import random

# Semaphore with 3 parking spots
parking_lot = threading.Semaphore(3)

def park_car(car_number):
    """Simulate car parking in limited parking lot"""
    
    print(f"🚗 Car #{car_number} arrived, looking for parking...")
    
    # Try to acquire a parking spot
    parking_lot.acquire()  # Decrements counter (3→2→1→0, then blocks)
    
    print(f"   ✓ Car #{car_number} PARKED successfully!")
    
    # Simulate random parking duration (1-3 seconds)
    park_duration = random.randint(1, 3)
    time.sleep(park_duration)
    
    print(f"   🚗 Car #{car_number} leaving after {park_duration}s")
    
    # Release the parking spot
    parking_lot.release()  # Increments counter (0→1→2→3)
    print(f"   ✓ Spot freed by Car #{car_number}")

if __name__ == "__main__":
    print("="*60)
    print("SEMAPHORE DEMO: Parking Lot (3 spots for 7 cars)")
    print("="*60)
    print("Note: Only 3 cars can park at the same time\n")
    
    cars = []
    
    # Create 7 cars trying to park (only 3 spots available)
    for i in range(1, 8):
        car_thread = threading.Thread(target=park_car, args=(i,))
        cars.append(car_thread)
        car_thread.start()
        time.sleep(0.3)  # Cars arrive every 0.3 seconds
    
    # Wait for all cars to finish parking and leaving
    for car in cars:
        car.join()
    
    print("\n" + "="*60)
    print("✓ All cars have completed parking!")
    print("="*60)
