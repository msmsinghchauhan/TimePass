"""
IPC Method 2: QUEUE - Thread-safe FIFO queue for multiple processes
Best for: Producer-consumer pattern, multiple workers processing tasks
"""
from multiprocessing import Process, Queue
import time
import random

def producer(queue, producer_id):
    """Producer process puts items into queue"""
    print(f"[Producer {producer_id}] Starting...")
    
    for i in range(3):
        item = f"Item-{producer_id}-{i}"
        queue.put(item)
        print(f"[Producer {producer_id}] Produced: {item}")
        time.sleep(random.uniform(0.1, 0.5))
    
    print(f"[Producer {producer_id}] Finished")

def consumer(queue, consumer_id):
    """Consumer process takes items from queue"""
    print(f"[Consumer {consumer_id}] Starting...")
    
    while True:
        try:
            # Wait for 2 seconds for an item
            item = queue.get(timeout=2)
            print(f"[Consumer {consumer_id}] Consumed: {item}")
            time.sleep(0.3)  # Simulate processing
        except:
            # Queue is empty and timeout reached
            print(f"[Consumer {consumer_id}] No more items, stopping")
            break

def worker(task_queue, result_queue, worker_id):
    """Worker takes tasks and puts results"""
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task == "STOP":
                break
            
            # Process task
            result = task ** 2
            result_queue.put(f"Worker {worker_id}: {task}² = {result}")
            time.sleep(0.2)
        except:
            break

if __name__ == "__main__":
    print("="*60)
    print("QUEUE Demo 1: Producer-Consumer Pattern")
    print("="*60)
    
    queue = Queue()
    
    # Create 2 producers and 2 consumers
    producers = [
        Process(target=producer, args=(queue, 1)),
        Process(target=producer, args=(queue, 2))
    ]
    
    consumers = [
        Process(target=consumer, args=(queue, 1)),
        Process(target=consumer, args=(queue, 2))
    ]
    
    # Start all processes
    for p in producers + consumers:
        p.start()
    
    # Wait for completion
    for p in producers + consumers:
        p.join()
    
    print("\n✓ Producer-Consumer demo completed!")
    
    # Example 2: Task distribution
    print("\n" + "="*60)
    print("QUEUE Demo 2: Task Distribution to Workers")
    print("="*60)
    
    task_queue = Queue()
    result_queue = Queue()
    
    # Add tasks
    tasks = [2, 3, 5, 7, 11, 13, 17, 19]
    for task in tasks:
        task_queue.put(task)
    
    # Create 3 workers
    workers = []
    for i in range(3):
        task_queue.put("STOP")  # Stop signal for each worker
        w = Process(target=worker, args=(task_queue, result_queue, i+1))
        workers.append(w)
        w.start()
    
    # Wait for workers to finish
    for w in workers:
        w.join()
    
    # Collect results
    print("\nResults:")
    while not result_queue.empty():
        print(f"  {result_queue.get()}")
    
    print("\n✓ Task distribution completed!")
