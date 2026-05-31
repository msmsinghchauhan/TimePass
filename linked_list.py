
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


       
if __name__ == "__main__":
    data=[1,2,3,4,5]
    data1=[10,20,30]
    linked_list=LinkedList()
    for item in data:
        linked_list.append(item)
    linked_list.print_list()
    """
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
    #print("Inserting 30 at position 10")
    #linked_list.insert_at_position(10,30)
    linked_list.print_list()
    """
    linked_list2=LinkedList()
    for item in data1:
        linked_list2.append(item)
    linked_list2.print_list()
    print("Merging the two linked lists")
    merged_list=linked_list.merge_sorted(linked_list2)
    merged_list.print_list()



        


