import sys
from secrets import token_hex

salt1 = token_hex(16)
salt2 = token_hex(16)

if "--env" in sys.argv:
    print(f"export TNYR_SALT1_HEX={salt1}")
    print(f"export TNYR_SALT2_HEX={salt2}")
else:
    print("SALT1:", salt1)
    print("SALT2:", salt2)