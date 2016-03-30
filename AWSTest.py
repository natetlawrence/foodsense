import time
import sys

with open(sys.argv[1], 'w') as f:
    for num in range(0, 30):
        time.sleep(1)
        f.write('\n'+str(num))
    f.close()