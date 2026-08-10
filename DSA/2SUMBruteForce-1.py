"""
This program is a form of two sum problem where i am trying to solve  the problem with brute force method.
It takes a list of numbers and a target number as input, and returns the indices of the two numbers that add up to the target number.
If no such pair exists, it returns an empty list.
"""


def two_sum_brute_force(nums, target):
        dct= {}
        for i in range(len(nums)):
            val= target - nums[i]
            for j in range(len(nums)):
                if nums[j] == val and i != j:
                    dct.setdefault(i, j)
        for item in sorted(dct.keys()):
            if item in dct and dct[item] in dct:
                del dct[dct[item]]
        return list(dct.items())
    
if __name__ == "__main__":
        nums = [2, 7, 11, 15]
        target = 9
        result = two_sum_brute_force(nums, target)
        print(result)
        
        # Example output: [(0, 1)]
        # Explanation: The numbers at indices 0 and 1 (2 and 7)
        # add up to the target number 9.
        # If no such pair exists, it will return an empty list.
        nums = [3,2,4] 
        target = 6
        result = two_sum_brute_force(nums, target)
        print(result)

        # Example output: [(1, 2)]
        # Explanation: The numbers at indices 1 and 2 (2 and 4)
        # add up to the target number 6.
        # If no such pair exists, it will return an empty list.
        nums=[1, 2, 3, 4, 5,6,7,8,9,10]
        target = 10
        result = two_sum_brute_force(nums, target)
        print(result)
    
        nums=[10,9,8,7,6,5,4,3,2,1]
        target = 20
        result = two_sum_brute_force(nums, target)
        print(result)
    