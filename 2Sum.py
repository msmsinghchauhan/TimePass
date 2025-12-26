
# 2 SUM problem
# Given an array of integers, return indices of the two numbers such that they add up to a specific target.
# You may assume that each input would have exactly one solution, and you may not use the same element twice.   
# Example 1:
"""
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].
Example 2:

Input: nums = [3,2,4], target = 6
Output: [1,2]
Example 3:

Input: nums = [3,3], target = 6
Output: [0,1]
 

Constraints:

2 <= nums.length <= 104
-109 <= nums[i] <= 109
-109 <= target <= 109
Only one valid answer exists.
 

Follow-up: Can you come up with an algorithm that is less than O(n2) time complexity?
"""

def twoSum(nums, target):
    
    value_index = {}
    for i in range(len(nums)):
        complement=target-nums[i]
        if complement not in value_index:
            value_index[nums[i]]=i
        else:
            return [value_index[complement],i]
    
    return []


# Time complexity: O(n)
# Space complexity: O(n)

# Test cases    
print(twoSum([2,7,11,15],9))
print(twoSum([3,2,4],6))
print(twoSum([3,3],6))
print(twoSum([3,2,4,5,6,7,8,9,10,11,12,13,14,15],20))
print(twoSum([3,2,4,5,6,7,8,9,10,11,12,13,14,15],22))
print(twoSum([3,2,4,5,6,7,8,9,10,11,12,13,14,15],30))
print(twoSum([3,2,4,5,6,7,8,9,10,11,12,13,14,15],31))