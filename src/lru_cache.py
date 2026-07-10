
from collections import defaultdict
from linked_list import DoublyNode,DoublyLinkedList

lru_cache=defaultdict(DoublyLinkedList)

class LRUCache:
      def __init__(self,capacity:int):
            self.capacity=capacity
            self.cache=defaultdict(DoublyNode)
            self.node_tracker=DoublyLinkedList()

      def get(self,key:int)->DoublyNode:
            ## If the key is found in the cache then we will fetch the 
            ## associated node and in order to track the recent access of the node
            ## we well remove the node from its current position and add it to the start of the doubly linked list.
            if key in self.cache:
                  node=self.cache[key]
                  if not self.node_tracker.is_first_node(node):
                    self.node_tracker.remove_node_by_reference(node)
                    self.node_tracker.add_node_at_start_by_reference(node)
                    return node      
            return None
      

      def put(self,key:int,value:int):
            ## If the key is already present in the cache then we will update the value 
            # of the node and move it to the start of the doubly linked list.
            if self.get(key):
                 
                existing_node=self.get(key)
                existing_node.value=value
                self.cache[key]=existing_node
                self.node_tracker.remove_node_by_reference(existing_node)
                self.node_tracker.add_node_at_start_by_reference(existing_node)
            ## if the key is not present in the cache then we will 
            # create a new node and add it to the start of the doubly
            #  linked list.
            else:
                 new_node=DoublyNode(key,value)
                 
                 if len(self.cache) < self.capacity:
                    self.cache[key]=new_node
                    self.node_tracker.add_node_at_start_by_reference(new_node)
                 else:
                      # Delete the least recently used node from the cache and the doubly linked list.
                      
                      node_to_remove=self.node_tracker.tail
                      self.node_tracker.remove_node_by_reference(node_to_remove)
                      del self.cache[node_to_remove.key]
                      self.cache[key]=new_node
                      self.node_tracker.add_node_at_start_by_reference(new_node)

if __name__=="__main__":
      lru=LRUCache(3)
      lru.put(1,1)
      lru.put(2,2)
      lru.put(3,3)
      print(lru.get(1).value)
      lru.put(4,4)
      print(lru.get(2))
      lru.node_tracker.print_list()
                       