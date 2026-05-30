"""
MUTEX Example - Bank Account Race Condition
Demonstrates why mutex is needed for thread safety
"""
import threading
import time

# Global shared resource
bank_balance = 1000

# Mutex for thread synchronization
mutex = threading.Lock()

def withdraw_with_mutex(amount, person):
    """Safe withdrawal using mutex"""
    global bank_balance
    
    print(f"\n{person} wants to withdraw ${amount}")
    
    mutex.acquire()  # LOCK - Critical section starts
    try:
        print(f"  {person} checking balance: ${bank_balance}")
        
        if bank_balance >= amount:
            time.sleep(0.5)  # Simulate ATM delay
            bank_balance -= amount
            print(f"  ✓ {person} withdrew ${amount}")
            print(f"  Remaining balance: ${bank_balance}")
        else:
            print(f"  ✗ {person} - Insufficient funds!")
    finally:
        mutex.release()  # UNLOCK - Critical section ends

def withdraw_without_mutex(amount, person):
    """Unsafe withdrawal - shows race condition"""
    global bank_balance
    
    print(f"\n{person} wants to withdraw ${amount}")
    print(f"  {person} checking balance: ${bank_balance}")
    
    if bank_balance >= amount:
        time.sleep(0.5)  # Race condition happens here!
        bank_balance -= amount
        print(f"  ✓ {person} withdrew ${amount}")
        print(f"  Remaining balance: ${bank_balance}")
    else:
        print(f"  ✗ {person} - Insufficient funds!")

if __name__ == "__main__":
    print("="*60)
    print("TEST 1: WITH MUTEX (Safe)")
    print("="*60)
    
    bank_balance = 1000
    t1 = threading.Thread(target=withdraw_with_mutex, args=(700, "Alice"))
    t2 = threading.Thread(target=withdraw_with_mutex, args=(700, "Bob"))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    print(f"\n{'='*60}")
    print(f"Final Balance: ${bank_balance} ✓ CORRECT")
    print(f"{'='*60}")
    
    # Now test without mutex
    print("\n\n" + "="*60)
    print("TEST 2: WITHOUT MUTEX (Unsafe - Race Condition)")
    print("="*60)
    
    bank_balance = 1000
    t3 = threading.Thread(target=withdraw_without_mutex, args=(700, "Charlie"))
    t4 = threading.Thread(target=withdraw_without_mutex, args=(700, "David"))
    
    t3.start()
    t4.start()
    t3.join()
    t4.join()
    
    print(f"\n{'='*60}")
    print(f"Final Balance: ${bank_balance} ✗ WRONG (should be $300)")
    print(f"{'='*60}")
