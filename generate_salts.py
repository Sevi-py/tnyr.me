from secrets import token_hex

print("Windows")
print("SALT1:", token_hex(16))
print("SALT2:", token_hex(16))