import os



os.chdir("D:\\Learning\\Projects\\TimePass")
current_dir = os.getcwd()


for root,dirs,files in os.walk(current_dir):
    print(root,dirs,files,sep="\n")
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
    
    print("Root is :",root)
    print("Directories are :",dirs)
    print("Files are :",files)





