# Print Buffer Formatting
# Demonstrates appending text to Mindustry Logic's print buffer and flushing to message block.
# Note: print() does NOT automatically append a newline character. Consecutive print()
# calls concatenate on the same line ("Status: ONLINE"). To start a new line, explicitly add "\n".
from mlog import print, printflush

print("Status: ")
print("ONLINE")
printflush("message1")
