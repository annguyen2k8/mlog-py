# Decompiled from print_buffer.mlog
# Verified via ast.parse and semantic argument recovery
# Note: print() appends to Mindustry's print buffer without automatic newlines; consecutive calls concatenate.
from mlog import print, printflush

print("Status: ")
print("ONLINE")
printflush("message1")
