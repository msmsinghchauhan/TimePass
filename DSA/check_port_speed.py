def all_numeric(lst):
    print([ i.isnumeric() for i in lst])
    return all(isinstance(i, (int, float)) for i in lst)

# Example usage
example_list = [1, 2.5, 3, 4.0]
#print(all_numeric(example_list))  # Output: True

example_list = [1, '2', 3, 4.0]
#print(all_numeric(example_list))  # Output: Falsei
port_speed=['8.0', '8.0', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', '8.0', '8.0', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown']

print(all_numeric(port_speed))
def contains_only_numbers(lst):
    try:
        [float(i) for i in lst]
        return True
    except ValueError:
        return False

# Example usage
print(contains_only_numbers(port_speed))  # Output: False

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
 