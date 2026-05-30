
class Node:
    def __init__(self, value):
        self.data=value
        self.next=None

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


if __name__ == "__main__":
    data=[1,2,3,4,5]
    linked_list=LinkedList()
    for item in data:
        linked_list.append(item)
    linked_list.print_list()
    print("Reversing the linked list")
    linked_list.reverse()
    linked_list.print_list()
    linked_list.reverse()
    linked_list.print_list()
    print("Inserting 10 at position 2")
    linked_list.insert_at_position(2,10)

    linked_list.print_list()
    print("Inserting 20 at position 0")
    linked_list.insert_at_position(0,20)
    linked_list.print_list()
    print("Inserting 30 at position 10")
    linked_list.insert_at_position(10,30)
    linked_list.print_list()
        


        


