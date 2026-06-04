import pytest
from src.linked_list import LinkedList

@pytest.fixture
def clean_list():
    return LinkedList()

def test_acreate_linked_list():
    linked_list = LinkedList()
    assert linked_list.head is None

    


