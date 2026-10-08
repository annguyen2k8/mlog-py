from mlog import sensor, control, print, printflush, wait

heat = sensor("reactor1", "@heat")
cryo = sensor("reactor1", "@cryofluid")

if heat > 0.5:
    control("enabled", "reactor1", 0)
    print("EMERGENCY SHUTDOWN")
    printflush("message1")
elif cryo < 10:
    control("enabled", "reactor1", 0)
    print("LOW CRYOFLUID")
    printflush("message1")
else:
    control("enabled", "reactor1", 1)
    print("NOMINAL")
    printflush("message1")

wait(0.5)
