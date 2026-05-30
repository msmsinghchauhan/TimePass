"""Valid Square (High Frequency): Given four coordinates in a 2D plane, 
write a function to determine if they form a valid square 
(four equal sides and four right angles)."""

def squared_length(p1, p2) -> float:
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

def is_valid_square(points):
    distances=[]
    for i in range(0,len(points)):
        for j in range(i+1, len(points)):
            distances.append(squared_length(points[i], points[j]))
        
    if len(set(distances)) == 2 and distances.count(min(distances)) == 4:
        print("The points form a valid square.")
    else:
        print("The points do not form a valid square.")





if __name__ == "__main__":
    points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    is_valid_square(points)





