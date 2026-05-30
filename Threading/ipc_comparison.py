"""
IPC Methods Comparison - All 4 methods side by side
Shows when to use which method
"""
from multiprocessing import Process, Pipe, Queue, Value, Manager
import time

print("="*70)
print("INTER-PROCESS COMMUNICATION (IPC) METHODS COMPARISON")
print("="*70)

# ============================================================
# Method 1: PIPE
# ============================================================
print("\n1️⃣  PIPE - Two-way channel between processes")
print("-"*70)

def pipe_worker(conn):
    data = conn.recv()
    conn.send(f"Processed: {data.upper()}")

parent_conn, child_conn = Pipe()
p1 = Process(target=pipe_worker, args=(child_conn,))
p1.start()
parent_conn.send("hello")
result = parent_conn.recv()
p1.join()
print(f"Sent: hello → Received: {result}")
print("✓ Best for: 2 processes, bidirectional communication")

# ============================================================
# Method 2: QUEUE
# ============================================================
print("\n2️⃣  QUEUE - Thread-safe FIFO queue")
print("-"*70)

def queue_worker(q, n):
    q.put(f"Result from worker {n}")

queue = Queue()
workers = [Process(target=queue_worker, args=(queue, i)) for i in range(3)]
for w in workers:
    w.start()
for w in workers:
    w.join()

print("Results:")
while not queue.empty():
    print(f"  - {queue.get()}")
print("✓ Best for: Producer-consumer, multiple workers")

# ============================================================
# Method 3: SHARED MEMORY (Value/Array)
# ============================================================
print("\n3️⃣  SHARED MEMORY - Direct memory access")
print("-"*70)

def shared_worker(counter):
    counter.value += 10

counter = Value('i', 0)
p3 = Process(target=shared_worker, args=(counter,))
p3.start()
p3.join()
print(f"Counter value: {counter.value}")
print("✓ Best for: High-performance, simple data types")

# ============================================================
# Method 4: MANAGER
# ============================================================
print("\n4️⃣  MANAGER - Shared complex objects")
print("-"*70)

def manager_worker(shared_dict, key, value):
    shared_dict[key] = value

manager = Manager()
shared_dict = manager.dict()

p4 = Process(target=manager_worker, args=(shared_dict, "status", "complete"))
p4.start()
p4.join()
print(f"Shared dict: {dict(shared_dict)}")
print("✓ Best for: Complex objects (dict, list, nested)")

# ============================================================
# SUMMARY TABLE
# ============================================================
print("\n" + "="*70)
print("WHEN TO USE WHICH METHOD?")
print("="*70)
print("""
┌──────────────────┬──────────────┬────────────────────────────────┐
│ Method           │ Speed        │ Use Case                       │
├──────────────────┼──────────────┼────────────────────────────────┤
│ Pipe             │ Fast         │ Parent-child, 2 processes      │
│ Queue            │ Medium       │ Producer-consumer, many tasks  │
│ Shared Memory    │ Fastest      │ Counters, arrays, math ops     │
│ Manager          │ Slower       │ Dict, list, complex objects    │
└──────────────────┴──────────────┴────────────────────────────────┘

Examples:
  Pipe         → Chat between 2 processes
  Queue        → Task distribution to workers
  Shared Mem   → Parallel matrix calculations
  Manager      → Shared configuration, inventory
""")

print("\n" + "="*70)
print("DECISION TREE")
print("="*70)
print("""
Need to share data between processes?
│
├─ Only 2 processes?
│  └─ Use PIPE
│
├─ Many producers/consumers?
│  └─ Use QUEUE
│
├─ Simple data (int, float, array)?
│  └─ Use SHARED MEMORY (Value/Array)
│
└─ Complex objects (dict, list, nested)?
   └─ Use MANAGER
""")
