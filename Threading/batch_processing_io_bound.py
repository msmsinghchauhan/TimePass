"Using asyncio show one example where data is processed in batches. For example, if you have a list of 1000 items, "
"you can process them in batches of 100 using asyncio. Here's a simple example that demonstrates this concept:"

import asyncio
import random
import time

async def fetch_data(item):
    # Simulate a network call or some I/O operation
    """ This function simulates IO bound operation by sleeping for a random 
     time between 0.1 and 0.5 seconds.
     it gives the control once it gets busy processing the data to other tasks in the event loop.
     to simulate that it sleeps that means actually it gets busy processing the data while
     it give control to other tasks and takes control back when the execution of this function is done to continue
     rest of the code in this function. Here 'item' is the 
    data that is being processed in this function. It can be any data type like string, integer, list, etc.
       """

    await asyncio.sleep(random.uniform(0.1, 0.5))
    return f"Processed {item} in fetch_data function"


async def process_data_in_batches(data, batch_size=10):
      result=[]
      for i in range(0,len(data),batch_size):
           
           temp_data=data[i:i+batch_size]
           tasks=[fetch_data(item) for item in temp_data]
           batch_results = await asyncio.gather(*tasks)
           for temp_result in batch_results:
                result.append(temp_result)
      return result
           