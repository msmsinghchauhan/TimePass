"This is a common file to write python code for generic problems"

def remove_duplicates_from_list(lst: list) -> list:
    """
    Remove duplicates from a list while preserving the order of first occurrence.
    
    Args:
        lst (list): The input list from which duplicates need to be removed.
    
    Returns:
        list: A new list with duplicates removed, preserving the order of first occurrence.
    Time Complexity: O(n) - where n is the number of elements in the input list.
    Space Complexity: O(n) - in the worst case, if all elements are unique,
    """
    
    return list(dict.fromkeys(lst))

def remove_duplicates_from_list_lookup(lst: list) -> list:
    """
    Remove duplicates from a list while preserving the order of first occurrence using a set for lookup.
    
    Args:
        lst (list): The input list from which duplicates need to be removed.
    
    Returns:
        list: A new list with duplicates removed, preserving the order of first occurrence.
    Time Complexity: O(n) - where n is the number of elements in the input list.
    Space Complexity: O(n) - in the worst case, if all elements are unique,
"""
    unique_elements = []
    for item in lst:
        if item not in unique_elements:
            unique_elements.append(item)
    return unique_elements  

