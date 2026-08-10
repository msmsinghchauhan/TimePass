# This module contains problems related to dictionary operations in Python.

# Word frequency problem: Given a string, count the frequency of each word in the string and return a dictionary with words as keys and their frequencies as values.

def word_frequency(text):
    words=text.split()
    frequency_dict={}
    for word in words:
        frequency_dict[word]=frequency_dict.get(word, 0)+1
    return frequency_dict



def group_anagrams(words):
    anagram_dict={}
    for word in words:
        anagram_dict.setdefault(tuple(sorted(word.lower())),[]).append(word)    
    return anagram_dict.values()

def dct_merge(dct1,dct2):
    for key,value in dct2.items():
            dct1[key]=value
        
    return dct1
    
if __name__ == "__main__":
    #sample_text = "hello world hello"
    #print(word_frequency(sample_text))  # Output: {'hello': 2, 'world': 1}
    agm=["Listen", "Silent", "Earth",  "Heart", "Rescue", "Secure","Danger",  "Gander","Integral" , "Triangle","Lemon", "Melon"]

    print(group_anagrams(agm))