



from unittest import result


def hash_tag_generator(text):
    if text is None:
        return False
    
    result = ""
    for str in   text.split():
        #print(result[i])
        temp=str[0].upper()+str[1:]
        result+=temp
    
    if len(result)>140:
        return False
    result="#"+result
    return result
    
def hash_tag_generator_optimized(s):
    if s is None or len(s)==0:
        return False
    result = "".join([s[i].upper() if (i == 0 or s[i-1] == " ") and s[i].isalpha() else s[i].lower() if s[i].isalpha() else s[i] for i in range(len(s)) if s[i] != " " or (i > 0 and s[i-1] == " ")])
    
    if len(result.replace(" ",""))>140:
        return False
    return "#" + result.replace(" ","")
           
        
if __name__ == "__main__":
        text=" Hello there thanks for trying my Kata"
        #print(hash_tag_generator(text))
        print(hash_tag_generator_optimized(text))