"""
IPC Method 1: PIPE - Direct communication between two processes
Best for: Parent-child communication, simple bidirectional data transfer
"""
from multiprocessing import Process, Pipe
import time

def child_process(conn, name):
    """Child process receives and sends data through pipe"""
    print(f"[{name}] Child process started")
    
    # Receive data from parent
    message = conn.recv()
    print(f"[{name}] Received from parent: {message}")
    
    # Do some work
    time.sleep(1)
    result = message.upper()
    
    # Send result back to parent
    conn.send(f"Processed: {result}")
    print(f"[{name}] Sent response to parent")
    
    conn.close()

if __name__ == "__main__":
    print("="*60)
    print("PIPE Demo: Two-way communication between processes")
    print("="*60)
    
    # Create a bidirectional pipe
    parent_conn, child_conn = Pipe()
    
    # Create child process
    p = Process(target=child_process, args=(child_conn, "Child-1"))
    p.start()
    
    # Parent sends data
    print("[Parent] Sending data to child...")
    parent_conn.send("hello from parent")
    
    # Parent receives response
    response = parent_conn.recv()
    print(f"[Parent] Received from child: {response}")
    
    p.join()
    print("\n✓ Pipe communication completed!")
    
    # Example 2: Multiple messages
    print("\n" + "="*60)
    print("PIPE Demo 2: Multiple messages")
    print("="*60)
    
    def chatty_child(conn):
        for i in range(3):
            msg = conn.recv()
            print(f"  Child received: {msg}")
            conn.send(f"Reply #{i+1}: Got it!")
    
    parent_conn2, child_conn2 = Pipe()
    p2 = Process(target=chatty_child, args=(child_conn2,))
    p2.start()
    
    for i in range(3):
        parent_conn2.send(f"Message #{i+1}")
        reply = parent_conn2.recv()
        print(f"Parent received: {reply}")
    
    p2.join()
    print("\n✓ Multiple message exchange completed!")
