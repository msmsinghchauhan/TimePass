# Two sum problem brute force solution
# Given an array of integers, return indices of the two numbers such that they add up to a specific target.
# You may assume that each input would have exactly one solution, and you may not use the same element twice.
# Example:  nums = [2, 7, 11, 15], target = 9
# Output: [0, 1]    Because nums[0] + nums[1] = 2 + 7 = 9
# Time complexity: O(n^2)   Space complexity: O(1)

def two_sum(nums, target):
    for i in range(len(nums)):
       for j in range(i+1,len(nums)):
              if nums[i]+nums[j]==target:
                return [i,j]
    return []

# Test cases
print(two_sum([2,7,11,15],9))
print(two_sum([2,7,11,15],26))
print(two_sum([2,7,11,15],18))
print(two_sum([2,7,11,15],22))   