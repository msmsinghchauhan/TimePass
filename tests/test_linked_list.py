import pytest
from src.linked_list import LinkedList

@pytest.fixture
def clean_list():
    return LinkedList()

def test_acreate_linked_list():
    linked_list = LinkedList()
    assert linked_list.head is None

def test_single_append(clean_list):
    """Scenario 2: Verify appending once sets the head correctly."""
    clean_list.append("First Node")
    
    assert clean_list.head is not None
    assert clean_list.head.data == "First Node"
    assert clean_list.head.next is None

def test_multiple_appends(clean_list):
    """Scenario 3: Verify multiple appends link together in order."""
    clean_list.append(10)
    clean_list.append(20)
    
    # Verify the first element is 10
    assert clean_list.head.data == 10
    # Verify the second element is 20
    assert clean_list.head.next.data == 20
    # Verify the chain ends gracefully
    assert clean_list.head.next.next is None
    
        


