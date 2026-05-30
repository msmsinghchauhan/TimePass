"""
IPC Method 3: SHARED MEMORY - Direct memory sharing between processes
Best for: High-performance numerical operations, counters, arrays
"""
from multiprocessing import Process, Value, Array, Lock
import time

def increment_counter(counter, lock, process_id):
    """Increment shared counter safely"""
    for i in range(5):
        with lock:  # Lock to prevent race condition
            counter.value += 1
            print(f"Process {process_id}: Counter = {counter.value}")
        time.sleep(0.1)

def modify_array(shared_array, process_id):
    """Modify shared array"""
    print(f"Process {process_id} modifying array...")
    for i in range(len(shared_array)):
        shared_array[i] += process_id
    print(f"Process {process_id} done!")

def calculate_sum(numbers, result, start, end):
    """Calculate sum of array slice"""
    partial_sum = sum(numbers[start:end])
    result.value += partial_sum
    print(f"Process calculated sum {start}-{end}: {partial_sum}")

if __name__ == "__main__":
    print("="*60)
    print("SHARED MEMORY Demo 1: Shared Counter")
    print("="*60)
    
    # Shared integer value with lock
    counter = Value('i', 0)  # 'i' = integer
    lock = Lock()
    
    # Create 3 processes incrementing same counter
    processes = []
    for i in range(3):
        p = Process(target=increment_counter, args=(counter, lock, i+1))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    print(f"\nFinal counter value: {counter.value}")
    print("✓ Shared counter demo completed!\n")
    
    # Example 2: Shared Array
    print("="*60)
    print("SHARED MEMORY Demo 2: Shared Array")
    print("="*60)
    
    # Create shared array
    shared_arr = Array('i', [0, 0, 0, 0, 0])  # 'i' = integer array
    print(f"Initial array: {list(shared_arr)}")
    
    # Two processes modify the same array
    p1 = Process(target=modify_array, args=(shared_arr, 1))
    p2 = Process(target=modify_array, args=(shared_arr, 10))
    
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    
    print(f"Final array: {list(shared_arr)}")
    print("✓ Shared array demo completed!\n")
    
    # Example 3: Parallel sum calculation
    print("="*60)
    print("SHARED MEMORY Demo 3: Parallel Sum Calculation")
    print("="*60)
    
    # Large array to sum
    numbers = Array('i', range(1, 101))  # 1 to 100
    result = Value('i', 0)
    
    # Divide work among 4 processes
    chunk_size = 25
    processes = []
    
    for i in range(4):
        start = i * chunk_size
        end = start + chunk_size
        p = Process(target=calculate_sum, args=(numbers, result, start, end))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    print(f"\nTotal sum (1-100): {result.value}")
    print(f"Expected: {sum(range(1, 101))}")
    print("✓ Parallel calculation completed!")
    
    print("\n" + "="*60)
    print("Data Types for Value/Array:")
    print("="*60)
    print("""
    'i' = signed integer
    'd' = double (float)
    'f' = float
    'c' = char
    'b' = signed byte
    """)
