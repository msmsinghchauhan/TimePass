

def alphabet_position(text):
    if text is None:
        return ""
    result=[]
    for char in text:
        if char.isalpha() and char.isupper():
            result.append(ord(char)-64)
        elif char.isalpha() and char.islower():
            result.append(ord(char)-96)
    return " ".join(map(str,result))
        
text="The sunset sets at twelve o' clock."

if __name__ == "__main__":
    print(alphabet_position(text))
