""" Temporary file"""







from heapq import merge


def minion_game(string):
    stuart=0
    kevin=0
    n=len(string)
    for i in range(len(string)):
        
            if string[i] in "aeiouAEIOU" :
                kevin+=n-i  
            else:
                stuart+=n-i

    if stuart>kevin:
        print("Stuart", stuart)
    elif kevin>stuart:
        print("Kevin", kevin)    
    else:
        print("Draw")
    
        
def reverse_string(string):
    #return string[::-1] 
    n=len(string)//2
    st= list(string)
    for i in range(n):
         """ swap string[i] with string[len(string)-1-i]"""
         st[i], st[len(string)-1-i] = st[len(string)-1-i], st[i]
    return "".join(st)


def reverse_string_pointer(string):
     
     reverse_string=list(string)
     left=0
     right=len(string)-1
     while left<right:
         reverse_string[left],reverse_string[right] =reverse_string[right],reverse_string[left]
         left+=1
         right-=1
     return "".join(reverse_string)

def is_palindrome(string):
    left=0
    right=len(string)-1
    while left<right:
         if string[left]!=string[right]:
              return False
         left+=1
         right-=1
    return True

def is_anagaram(string1, string2):
    """ Check if string1 and string2 are anagram or not
    Time complexity: O(n^2) because of the "in" operator in string2
    Space complexity: O(1) because we are not using any extra space
    """
    if len(string1)!=len(string2):
        return False
    for ch in string1:
        if ch not in string2:
            return False
    return True

def is_anagram_dict(string1, string2):
    """ Check if string1 and string2 are anagram or not
    Time complexity: O(n) because we are using dictionary to store the count of characters in string1 and then checking the count of characters in string2
    Space complexity: O(n) because we are using dictionary to store the count of characters in string1
    """
    if len(string1)!=len(string2):
        return False
    count={}
    for  i in range(len(string1)):
        count[string1[i]]=count.get(string1[i],0)+1
        count[string2[i]]=count.get(string2[i],0)-1
    if all(val==0 for val in count.values()):
        return True
    return False

def remove_duplicates_from_string(string):
    return "".join(dict.fromkeys(string))


def remove_duplicates_from_string_dict(string):
    count={}
    for ch in string:
        count[ch]=count.get(ch,0)+1
    return "".join(count.keys())


def first_non_repeating_character(string):
    count={}
    for ch in string:
        count[ch]=count.get(ch,0)+1
    for ch in string:
        if count[ch]==1:
            return ch
    return None

def string_compression(string):
    temp_dict=dict.fromkeys(string,0)
    for ch in string:
        temp_dict[ch]=temp_dict.get(ch,0)+1

    return "".join( item[0]+str(item[1]) for item in temp_dict.items())    

print(string_compression("aaabbcc"))

def longest_substring_without_repeating_characters(string):
    seen={}
    left=0
    max_length=0
    for right,char in enumerate(string):
        if  char in seen and seen[char]>=left:
            left=seen[char]+1
        seen[char]=right
        character_window_length=right-left+1
        max_length=max(max_length,character_window_length)
    return max_length

def minSubArraySum(target, nums):
    """ Assumption is that all the elements in the array are positive integers and target is also a positive integer
    Time complexity: O(n) because we are traversing the array once
    Space complexity: O(1) because we are not using any extra space"""
    left=0
    subarray_sum=0
    min_length=float("inf")

    for right in range(len(nums)):
        subarray_sum+=nums[right]
        while subarray_sum>=target:
            min_length=min(min_length,right-left+1)
            subarray_sum-=nums[left]    
            left+=1
    return min_length if min_length!=float("inf") else 0

def reverse_words_in_string(string):
    """ Time complexity: O(n) because we are traversing the string once
    Space complexity: O(n) because we are using extra space to store the reversed string"""
    return " ".join(string.strip().split()[::-1])
      
def is_rotation(string1,string2):
    """ Check if string1 and string2 are rotation of each other or not
    Time complexity: O(n) because we are traversing the string once
    Space complexity: O(n) because we are using extra space to store the concatenated string"""
    if len(string1)!= len(string2):
        return False
    return string1 in string2+string2

def longest_common_prefix_brute_force(strs):
    """ Time complexity: O(n*m) where n is the number of strings in the array and m is the length of the longest common prefix
    Space complexity: O(m) because we are using extra space to store the longest common prefix"""
    if not strs or len(strs)==0:
        return ""
    if len(strs)==1:
        return strs[0]
    strs.sort()
    first_word=strs[0]
    last_word=strs[-1]
    i=0
    while i<len(first_word) and i<len(last_word):
        if first_word[i]!=last_word[i]:
            break
        i+=1
    return first_word[:i]

def longest_common_prefix_vertical_scanning(strs):
    """ Time complexity: O(n*m) where n is the number of strings in the array and m is the length of the longest common prefix
    Space complexity: O(m) because we are using extra space to store the longest common prefix"""
    
    """ check if the list is empty or there is just one string in the list then return that string as longest common prefix"""
    if not strs or len(strs)==0:
        return ""
    if len(strs)==1:
        return strs[0]
    
    """ assume the fist word is the longest common prefix and 
    then iterate through each character of the first word then compare it with other words in the list 
    if the character is not same then break and update the longest common prefix accordingly """

    longest_common_prefix=strs[0]

    for i in range(len(longest_common_prefix)):
        character_to_match=longest_common_prefix[i]
        for  word in strs[1:]:
            if i>=len(word) or word[i]!=character_to_match:
                     return longest_common_prefix[:i]
                    
        
    return longest_common_prefix

def longest_palindromic_substring_brute_force(string):
    """ Time complexity: O(n^3) where n is the length of the string
    Space complexity: O(n) because we are using extra space to store the longest palindromic substring"""

    longest_palindrome=""
    for i in range(len(string)):
        for j in range(i+1,len(string)+1):
            substring=string[i:j]
            if is_palindrome(substring):
                if len(substring)>len(longest_palindrome):
                    longest_palindrome=substring
    return longest_palindrome

def longest_palindromic_substring(string: str) -> str:
    # 1. Handle empty string edge case immediately
    if not string:
        return ""
        
    start, end = 0, 0          # Tracks boundaries of the longest palindrome
    longest_len_seen = 1       # A single character always has a baseline length of 1
    
    # 2. Helper function to scan outward from a center point
    def expand_from_center(left: int, right: int) -> int:
        while left >= 0 and right < len(string) and string[left] == string[right]:
            left -= 1
            right += 1
        return right - left - 1

    # 3. Main loop over every single character index
    for i in range(len(string)):
        # Case 1: Odd-length palindromes (e.g., "aba", center is 'b')
        len1 = expand_from_center(i, i)
        
        # Case 2: Even-length palindromes (e.g., "abba", center is between 'b' and 'b')
        len2 = expand_from_center(i, i + 1)
        
        # Find the best length achieved at this specific index spot
        max_len = max(len1, len2)
        
        # 4. Check if this beats our previous true length record
        # Note: (end - start + 1) represents the actual length of our active record
        if max_len > (end - start + 1):
            longest_len_seen = max_len
            
            # Calculate the exact slice boundaries using symmetric division
            start = i - (max_len - 1) // 2
            end = i + max_len // 2
            
    # 5. Return the single final text slice
    return string[start : end + 1]

def bubble_sort(arr):
    n=len(arr)
    for i in range(n-1):
        swapped=False
        for j in range(n-1-i):
            if arr[j]>arr[j+1]: 
                arr[j],arr[j+1]=arr[j+1],arr[j]
                swapped=True
        if swapped==False:
            break
    return arr

def insertion_sort(arr):
    n=len(arr)
    for i in range(1,n):
        key=arr[i]
        indx=-1
        for j in range(i-1,-1,-1):
            if arr[j]>key:
                arr[j+1]=arr[j]
                indx=j
            else:
                break    
        if indx!=-1:
            arr[indx]=key
    return arr    

def insertion_sort_optimized(arr):
    n=len(arr)
    for i in range(1,n):
        key=arr[i]
        j=i-1
        while j>=0 and arr[j]>key:
            arr[j+1]=arr[j]
        arr[j+1]=key
    return arr

def selection_sort(arr):
    n=len(arr)
    for i in range(n-1):
        min_index=i
        for j in range(i+1,n):
            if arr[j]<arr[min_index]:
                min_index=j

        arr[i],arr[min_index]=arr[min_index],arr[i]
    return arr

def merge_sort(arr):
    n=len(arr)
    if n<=1:
        return arr
    mid=n//2
    left_sorted=merge_sort(arr[:mid])
    right_sorted=merge_sort(arr[mid:])
            
    return merge(left_sorted,right_sorted)


def merge(left_arr, right_arr):
    i=0
    j=0
    result=[]
    while i<len(left_arr) and j<len(right_arr):
        if left_arr[i]<right_arr[j]:
            result.append(left_arr[i])
            i+=1
        else:
            result.append(right_arr[j])
            j+=1
    result.extend(left_arr[i:])
    result.extend(right_arr[j:])
    return result

""" Printing pattern """

def print_pyramid(rows):
    for i in range(rows):
        # 1. Print leading spaces
        spaces = " " * (rows - i - 1)
        # 2. Print stars (always an odd number: 1, 3, 5, 7...)
        stars = "*" * (2 * i + 1)
        
        # Combine and print the row
        print(spaces + stars)


def print_inverted_pyramid(rows):
    for i in range(rows, -1, -1):
        # 1. Print leading spaces
        spaces = " " * (rows - i)
        # 2. Print stars (always an odd number: 1, 3, 5, 7...)
        stars = "*" * (2 * i - 1)
        
        # Combine and print the row
        print(spaces + stars)

import os

def print_files_recursively(directory):
    

#print_pyramid(8)       
#print_inverted_pyramid(10)