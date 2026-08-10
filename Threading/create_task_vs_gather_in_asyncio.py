#  create_task() vs gather() in asyncio

"""
The event loop only runs other tasks when the CURRENT coroutine yields.
main() is a coroutine just like any other.
If main() never yields, the event loop never gets control,
and no scheduled task ever runs.
gather forces main() to yield by design — that is its entire purpose.

create_task never forces main() to yield — you must do it manually with await

Event loop takes control only when main yields, and it will not yield until it hits an await or return statement.
If main() never yields, the event loop never gets control, and no scheduled task ever runs

"gather internally awaits all tasks — so main() is suspended at that line and the event loop runs freely until all 
tasks complete. create_task just schedules tasks and 
returns immediately — main() keeps running and exits before the event loop ever processes the 
scheduled tasks. The sleep or yield in main() is not about giving tasks time to sleep 
— it is about suspending main() so the event loop gets control at all. 
The individual awaits inside each task only matter once those tasks have actually started."


"""

import asyncio
import random
import time


async def say_hello(name:str,delay:int):
    start_time = time.time()
    await asyncio.sleep(delay)
    print(f"Hello, {name} after {delay} seconds!")
    end_time = time.time()
    print(f"{name} Actual execution time: {end_time - start_time:.2f} seconds")


async def main():
    start_time = time.time()
    
    print("Using asyncio.gather()")
    await asyncio.gather(
        say_hello("Alice", 0.1),
        say_hello("Bob", 0.2),
        say_hello("Charlie", 0.3)
    )
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    

    print("\nUsing asyncio.create_task()")  
    start_time = time.time()
    
    asyncio.create_task(say_hello("X", 0.1))
    asyncio.create_task(say_hello("Y", 0.2))
    asyncio.create_task(say_hello("Z", 0.3))
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    #await asyncio.sleep(1)  # Wait for all tasks to complete
    
async def main_no_sleep():
    print("No-sleep version using asyncio.create_task()")
    start_time = time.time()
    asyncio.create_task(say_hello("X", 0.1))
    asyncio.create_task(say_hello("Y", 0.2))
    asyncio.create_task(say_hello("Z", 0.3))
      # Wait for all tasks to complete
    #await asyncio.sleep(1)  # Wait for all tasks to complete
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main_no_sleep())
    


