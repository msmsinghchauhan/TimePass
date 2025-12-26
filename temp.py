
import re 

input_string = """Canister firmware : E70D
Canister firmware date : 2025-03-20T14:58:07+00:00
Canister build type : Release
Canister commit hash : 481b01531489ffbfb735c2246bbeb306a872d7b2
Canister BIOS : 21.2X3
Canister bootloader : 8.5.0X5
Canister bridge : 4.0.9
Canister enclosure mgmt: E7.0D
Canister VPD structure : 0x0C
Canister VPD CRC : 0xEAB9FAD3
Canister FPGA : 0x02
Midplane VPD structure : 0x11
Midplane VPD CRC : 0x4525AB4E
Boot Media firmware : 42A4SB6E
Ethernet e1a firmware : 28.44.1036
Ethernet e1b firmware : 28.44.1036
Ethernet e2a firmware : 28.44.1036
Ethernet e2b firmware : 28.44.1036
Ethernet e3a firmware : 28.44.1036
Ethernet e3b firmware : 28.44.1036
Ethernet e4a firmware : 28.44.1036
Ethernet e4b firmware : 28.44.1036
Ethernet e0c firmware : 2.26
Ethernet e0d firmware : 2.26
PSU 1 firmware : 01.34.32
PSU 2 firmware : 01.34.32
PSU 1 VPD structure : 0x01
PSU 2 VPD structure : 0x01
PSU 1 VPD CRC : 0x14EF40F6
PSU 2 VPD CRC : 0xC648FF60
Canister Slot(Mode) : 0(S)"""

## Test 1

"""
pattern = r"Canister\s* Slot\(Mode\)\s*:\s*\d+\((\w+)\)"
mode = re.search(pattern, input_string)
shelf_mode=mode.group(1)  # Fetch the value matched within the parentheses
print(shelf_mode)
if shelf_mode == 'S':
    print ("Module A is slave")
else :
    print ("Module A is master")


#dct={"0":"1","1":"0"}

dct={"1":"2","2":"1"}
for i in list(dct):
    if dct[i] in dct:
        del dct[i]
        
dct={"1":"2","2":"1"}
print( sorted(dct.keys()))
for i in sorted(dct.keys()):
    print(i, dct[i])
    if dct[i] in dct:
        print("Deleting", i, dct[i])
        del dct[i]

print(dct)

for item in dct.items():
    print(item)
   
dct={"1":"2","2":"1"}    
del dct[dct["1"]]
print(dct)

"""
## Test 2
import re

disk_num = re.findall("\d+\.\d+\.(\d+)", "2.2.10")
print(disk_num)
for item in disk_num:
    print(item)
#disk_id = int(disk_num[0])

## Test 3
# Find the NVME disk id from string " NVMe  0, temperature = 36 override = 88, wctemp = 73 cctemp = 83."

nvme_string = " NVMe  0, temperature = 36 override = 88, wctemp = 73 cctemp = 83."
nvme_disk_id = re.search("NVMe\s+(\d+)", nvme_string).group(1)
print("NVME id of the disk is %s" % nvme_disk_id)

## Test 4
sensor_string = "Sensor  8, temperature = 42."
if re.search("Sensor\s+(\d+),\s+temperature\s+=\s+(\d+)", sensor_string):
    sensor_id = re.search("Sensor\s+(\d+),\s+temperature\s+=\s+(\d+)", sensor_string).group(1)
    sensor_temp = re.search("Sensor\s+(\d+),\s+temperature\s+=\s+(\d+)", sensor_string).group(2)
    print("Sensor id is %s and temperature is %s" % (sensor_id, sensor_temp))
    
module_B_sensor= list(range(27,49))
print(module_B_sensor)
module_A_sensor= list(range(5,28))
print(module_A_sensor)

## Test 5
print("Test 5:=> ")

A=[{ "a":"1","b":"2","c":"3","d":"4"},{"x":"9","y":"8","z":"7","w":"6"},{"p":"11","q":"12","r":"13","s":"14"}]
B=[{"p":"11","q":"12","r":"13","s":"14"},{"a":"1","b":"2","c":"3","d":"4"},{"x":"9","y":"8","z":"7","w":"6"}]

print(zip(A,B))
for i,j in zip(A,B):
    print(i)
    print(j)    
    print(i==j)
    if i==j:
        print("Matched")
    else:
        print("Not matched")
        
## Test 6
sample_string= "core.151755310.2012-04-19.12_19_50.nz"

match =sample_string.startswith("core.")
print("Test6 match:", match)