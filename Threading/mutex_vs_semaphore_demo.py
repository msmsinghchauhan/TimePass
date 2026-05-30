"""
MUTEX vs SEMAPHORE - Direct Comparison
Shows the difference between mutex and semaphore in action
"""
import threading
import time

print("="*70)
print("MUTEX vs SEMAPHORE COMPARISON")
print("="*70)

# ============================================================
# SCENARIO 1: MUTEX - Single Database Connection
# ============================================================
print("\n🔒 MUTEX Example: Single Database Connection")
print("-"*70)

db_mutex = threading.Lock()
query_count = 0

def execute_query_mutex(user):
    global query_count
    print(f"{user} requesting database access...")
    
    db_mutex.acquire()  # Lock database
    print(f"  ✓ {user} got exclusive access to database")
    
    time.sleep(1)  # Simulate query execution
    query_count += 1
    
    print(f"  ✓ {user} finished query #{query_count}")
    db_mutex.release()  # Unlock database

threads = []
for user in ["Alice", "Bob", "Charlie"]:
    t = threading.Thread(target=execute_query_mutex, args=(user,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("→ Result: Only 1 person used database at a time (sequential)\n")

# ============================================================
# SCENARIO 2: SEMAPHORE - Connection Pool (3 connections)
# ============================================================
print("🔢 SEMAPHORE Example: Database Connection Pool (3 connections)")
print("-"*70)

db_pool = threading.Semaphore(3)  # 3 connections available
query_count = 0

def execute_query_semaphore(user):
    global query_count
    print(f"{user} requesting database connection...")
    
    db_pool.acquire()  # Get one connection from pool
    print(f"  ✓ {user} got a connection from pool")
    
    time.sleep(1)  # Simulate query execution
    query_count += 1
    
    print(f"  ✓ {user} finished query")
    db_pool.release()  # Return connection to pool

threads = []
for user in ["Alice", "Bob", "Charlie", "David", "Eve"]:
    t = threading.Thread(target=execute_query_semaphore, args=(user,))
    threads.append(t)
    t.start()
    time.sleep(0.1)  # Stagger arrivals slightly

for t in threads:
    t.join()

print("→ Result: Up to 3 people used database simultaneously\n")

# ============================================================
# SUMMARY
# ============================================================
print("="*70)
print("SUMMARY")
print("="*70)
print("""
┌─────────────────┬─────────────────────┬─────────────────────┐
│                 │ MUTEX               │ SEMAPHORE           │
├─────────────────┼─────────────────────┼─────────────────────┤
│ Value           │ Binary (0 or 1)     │ Counter (0,1,2...)  │
│ Max Concurrent  │ 1                   │ N (configurable)    │
│ Ownership       │ Yes (lock=unlock)   │ No                  │
│ Use Case        │ Critical section    │ Resource counting   │
│ Example         │ Single printer      │ Printer pool        │
└─────────────────┴─────────────────────┴─────────────────────┘

Real-world analogy:
  MUTEX     = Key to single bathroom (only 1 person at a time)
  SEMAPHORE = Parking lot counter (tracks N available spots)
""")
