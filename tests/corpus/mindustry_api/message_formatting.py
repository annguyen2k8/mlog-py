from mlog import print, printflush, sensor

copper = sensor("vault1", "@copper")
lead = sensor("vault1", "@lead")

print("RESOURCE REPORT:\n")
print("Copper: ")
print(copper)
print("\nLead: ")
print(lead)
printflush("message1")
