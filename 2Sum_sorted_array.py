# two sum problem when the array is sorted

def two_sum(arr, target):
   total=0
   left=0
   right=len(arr)-1
   while left<right:
       total=arr[left]+arr[right]
       if total==target:
           return [left,right]
       elif total<target:
           left+=1
       else:
           right-=1 
   return []

# Time complexity: O(n)
# Space complexity: O(1)
# Test cases
print(two_sum([2,7,11,15],9))
print(two_sum([2,7,11,15],26))
print(two_sum([2,7,11,15],18))
print(two_sum([2,7,11,15],22))
print(two_sum([2,7,11,15],26))
print(two_sum([2,7,11,15],30))
print(two_sum([2,7,11,15],26))
print(two_sum([2,7,11,15],33))