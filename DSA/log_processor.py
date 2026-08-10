  # Clear the error log file
error_file = open("error.log", "a")
with open("server.log", "r") as file:
    for line in file:
        if "ERROR" in line:
            error_file.write(line)
error_file.close()

with open("error.log", "r") as file:
    for line in file:
        print(line.strip()
              )
