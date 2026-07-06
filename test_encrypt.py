# test_encrypt.py

from privacy.encryption import (
    encrypt_data,
    decrypt_data
)

text = "Bought a laptop"

encrypted = encrypt_data(text)

print("Encrypted:", encrypted)

print(
    "Decrypted:",
    decrypt_data(encrypted)
)

