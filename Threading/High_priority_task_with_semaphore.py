#Build the High-Priority Flood
#Now build the continuous spawner. No low-priority task yet — just observe the semaphore under load.

import asyncio
import time

SEMAPHORE_SLOTS=2
active_count=0
semaphore=asyncio.Semaphore(SEMAPHORE_SLOTS)

async def high_priority_task(task_id):
    global active_count
    start_time = time.time()
    print(f"High-priority task {task_id} is starting at {start_time}.")
    async with semaphore:
        active_count += 1
        print(f"[HIGH {task_id:03d}] acquired | active={active_count}")

        print(f"High-priority task {task_id} started. Active count: {active_count}")
        await asyncio.sleep(0.05)  # Simulate work
        print(f"High-priority task {task_id} completed.")
        active_count -= 1
        print(f"[HIGH {task_id:03d}] released | active={active_count}")
    end_time = time.time()
    print(f"High-priority task {task_id} finished at {end_time}. Duration: {end_time - start_time}")
async def spawner():
    for i in range(20):
        asyncio.create_task(high_priority_task(i))
        await asyncio.sleep(0.02)  # Spawn tasks quickly

async def main():
    await spawner()
    await asyncio.sleep(0.5)  # Wait for all tasks to complete

if __name__ == "__main__":
    asyncio.run(main())