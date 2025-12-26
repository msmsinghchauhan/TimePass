import json
a = int(input('Enter the value of x co-ordinate of origin:'))
b = int(input('Enter the value of y co-ordinate of origin:'))

distance = lambda x, y: ((a - int(x)) ** 2 + (b - int(y)) ** 2) ** 0.5
with open('/Users/sinm/Library/CloudStorage/OneDrive-NetAppInc/Desktop/Mukesh/TimePass/coordinates.json','r' ) as f:
    data = json.load(f)
    sorted_list=sorted(data,key=lambda x:distance(*x['value'].split(',')))
    print(sorted_list)
    
    

  
    