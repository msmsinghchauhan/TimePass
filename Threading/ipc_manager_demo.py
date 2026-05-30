"""
IPC Method 4: MANAGER - Shared complex Python objects (dict, list, etc.)
Best for: Complex data structures shared between processes
"""
from multiprocessing import Process, Manager
import time

def add_to_dict(shared_dict, key, value):
    """Add key-value pair to shared dictionary"""
    shared_dict[key] = value
    print(f"Process added: {key} = {value}")

def append_to_list(shared_list, items, process_id):
    """Append items to shared list"""
    for item in items:
        shared_list.append(f"P{process_id}-{item}")
        print(f"Process {process_id} added: {item}")
        time.sleep(0.1)

def update_inventory(inventory, item, quantity):
    """Update inventory (dict)"""
    if item in inventory:
        inventory[item] += quantity
        print(f"Updated {item}: +{quantity} → Total: {inventory[item]}")
    else:
        inventory[item] = quantity
        print(f"Added {item}: {quantity}")

if __name__ == "__main__":
    print("="*60)
    print("MANAGER Demo 1: Shared Dictionary")
    print("="*60)
    
    manager = Manager()
    shared_dict = manager.dict()
    
    # Multiple processes adding to same dictionary
    processes = []
    data = [("name", "Alice"), ("age", 30), ("city", "NYC")]
    
    for key, value in data:
        p = Process(target=add_to_dict, args=(shared_dict, key, value))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    print(f"\nFinal dictionary: {dict(shared_dict)}")
    print("✓ Shared dictionary demo completed!\n")
    
    # Example 2: Shared List
    print("="*60)
    print("MANAGER Demo 2: Shared List")
    print("="*60)
    
    shared_list = manager.list()
    
    # Two processes appending to same list
    p1 = Process(target=append_to_list, args=(shared_list, ["A", "B", "C"], 1))
    p2 = Process(target=append_to_list, args=(shared_list, ["X", "Y", "Z"], 2))
    
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    
    print(f"\nFinal list: {list(shared_list)}")
    print("✓ Shared list demo completed!\n")
    
    # Example 3: Real-world scenario - Inventory Management
    print("="*60)
    print("MANAGER Demo 3: Inventory System")
    print("="*60)
    
    inventory = manager.dict()
    inventory['apples'] = 10
    inventory['oranges'] = 5
    
    print(f"Initial inventory: {dict(inventory)}\n")
    
    # Simulate multiple warehouse workers updating inventory
    updates = [
        ("apples", 5),
        ("oranges", 3),
        ("apples", -2),
        ("bananas", 7),
        ("oranges", 4)
    ]
    
    processes = []
    for item, qty in updates:
        p = Process(target=update_inventory, args=(inventory, item, qty))
        processes.append(p)
        p.start()
        time.sleep(0.1)
    
    for p in processes:
        p.join()
    
    print(f"\nFinal inventory: {dict(inventory)}")
    print("✓ Inventory system demo completed!\n")
    
    # Example 4: Nested structures
    print("="*60)
    print("MANAGER Demo 4: Nested Data Structures")
    print("="*60)
    
    # Manager can handle nested structures
    data = manager.dict()
    data['users'] = manager.list()
    data['config'] = manager.dict()
    
    def add_user(data, user):
        data['users'].append(user)
        print(f"Added user: {user}")
    
    users = ["Alice", "Bob", "Charlie"]
    processes = []
    
    for user in users:
        p = Process(target=add_user, args=(data, user))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    print(f"\nUsers: {list(data['users'])}")
    print("✓ Nested structures demo completed!")
