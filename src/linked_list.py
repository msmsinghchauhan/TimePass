
class Node:
    def __init__(self, value):
        self.data=value
        self.next=None


class DoublyNode:
    def __init__(self,key:int|None=None,value:int|None=None):
        self.key=key
        self.value=value
        self.next=None
        self.prev=None



class LinkedList:
    def __init__(self):
        self.head=None
    def append(self,value):
        new_node=Node(value)

        """ Insert if the linked list is empty"""
        if self.head is None:
            self.head=new_node
            return
        else:
            """ Insert at the end of the linked list"""
            tail=self.head
        while tail.next:
            tail= tail.next
        """ Insert at the end of the linked list"""
        tail.next=new_node

    def print_list(self):
        current=self.head
        while current:
            print(current.data)
            current=current.next
            
    def reverse(self):
        "if there is just one node or no node, return the head"

        if self.head is None or self.head.next is None:
            return self.head

        temp=self.head.next
        
        self.head.next=None

        while temp is not None:
            temp2=self.head
            self.head=temp
            temp=temp.next
            self.head.next=temp2

    def insert_at_position(self,position,value):
        new_node=Node(value)
        if position==0:
           temp=self.head
           self.head=new_node
           new_node.next=temp
        else:
            temp=self.head
            while position-1 and temp is not None:
                temp=temp.next
                position-=1
            if temp is None:
                raise IndexError("Position out of bounds")
            temp2=temp.next
            temp.next=new_node
            new_node.next=temp2
    
    def delete_at_position(self,position):
        if self.head is None:
            raise IndexError("Position out of bounds")
        if position == 0:
            temp=self.head
            self.head=self.head.next
            del temp
        else:
            temp_prev=None
            temp=self.head
            while position-1 and temp is not None :
                temp_prev=temp
                temp=temp.next
                position-=1
            if temp is None:
                raise IndexError("Position out of bounds")
            temp_prev.next=temp.next
            temp.next=None
            del temp

    def merge_sorted(self,other):
        if self.head is None and other.head is None:
            return None
        elif self.head is None and other.head is not None:
            return other
        elif self.head is not None and other.head is None:
            return self
        else:
            if self.head.data < other.head.data :
                temp=self.head
                self.head=self.head.next
            else:
                temp=other.head
                other.head=other.head.next         
            tail=temp
            while self.head is not None and other.head is not None:
                if self.head.data < other.head.data :
                   tail.next=self.head
                   tail=tail.next 
                   self.head=self.head.next
                else:  
                    tail.next=other.head
                    tail=tail.next
                    other.head=other.head.next  

            while self.head is not None: 
                tail.next=self.head
                tail=tail.next
                self.head=self.head.next
            while other.head is not None:
                tail.next=other.head
                tail=tail.next
                other.head=other.head.next
            tail.next=None
            merged_list=LinkedList()
            merged_list.head=temp
            return merged_list

    def find_cycle(self):
        slow_pointer=self.head
        fast_pointer=self.head
        while slow_pointer is not None and fast_pointer is not None and fast_pointer.next is not None:
            slow_pointer=slow_pointer.next
            fast_pointer=fast_pointer.next.next
            if slow_pointer==fast_pointer:
                return True
        return False
    
    def find_cycle_start(self):
        visited_nodes=set()
        slow_pointer=self.head
        previous_node=None
        
        while slow_pointer is not None :
            
            if slow_pointer  not in visited_nodes:
                visited_nodes.add(slow_pointer)
            else: 
                break
            previous_node=slow_pointer
            slow_pointer=slow_pointer.next
        if slow_pointer is None:
            return (None, None)
        return (previous_node,slow_pointer)           
                

class DoublyLinkedList:
    def __init__(self):
        self.head=None
        self.tail=None
    def add_node(self,key:int|None=None,value:int|None=None):
        ## Add a new node to a doubly linked list whic is empty
        if self.head is None and self.tail is None:
            self.head=DoublyNode(key,value)
            self.tail=self.head
        else:
            temp=DoublyNode(key,value)
            prev_node=self.tail
            self.tail.next=temp
            self.tail=temp
            self.tail.prev=prev_node
            self.tail.next=None
    def add_node_at_start(self,key:int|None,value:int|None):
        ## Add a new node to a doubly linked list whic is empty  
        node=DoublyNode(key,value)
        if self.head is None and self.tail is None:
            self.head=node
            self.tail=node 
            self.head.prev=None
            self.tail.next=None
        else:
            node.next=self.head
            node.prev=None
            self.head.prev=node
            self.head=node

    def remove_node_by_reference(self,node:DoublyNode):
        ## If the list from where a given node is to be removed is empty
        if self.head is None and self.tail is None:
            return
        ## if the node to be deleted is the head node 
        if node==self.head:
            node.next.prev=None
            self.head=node.next
        ## if the node to be deleted is the tail node
        elif node== self.tail:
            node.prev.next=None
            self.tail=node.prev 
        ## if the node to be deleted is in the middle
        else:    
            node.prev.next=node.next
            node.next.prev=node.prev
            node.next=None
            node.prev=None
            del node

    def add_node_at_start_by_reference(self,node:DoublyNode):
        # Add a new node to a doubly linked list which is empty
        if self.head is None and self.tail is None:
            self.head=node
            node.prev=None
            node.next=None
            self.tail=node
        else:
            ## Add a new node at the start of the doubly list
            node.next=self.head
            node.prev=None
            self.head.prev=node
            self.head=node
    def print_list(self):
        temp=self.head
        while temp is not None:
            print(f"Key:{temp.key}, Value:{temp.value}")
            temp=temp.next
    def is_first_node(self,node:DoublyNode)->bool:
        if node==self.head:
            return True
        return False
    def is_last_node(self,node:DoublyNode)->bool:
        if node==self.tail:
            return True
        return False
    

        




        


