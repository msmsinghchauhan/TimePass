from linked_list import LinkedList


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
