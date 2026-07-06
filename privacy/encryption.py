from cryptography.fernet import Fernet
import os

KEY_FILE = "secret.key"


def generate_key():

    key = Fernet.generate_key()

    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)

    print("Encryption key generated successfully.")


def load_key():

    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(
            "secret.key not found. Generate it first."
        )

    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()


def encrypt_data(data):

    if data is None:
        return None

    cipher = Fernet(load_key())

    encrypted = cipher.encrypt(
        str(data).encode("utf-8")
    )

    return encrypted.decode("utf-8")


def decrypt_data(encrypted_data):

    if encrypted_data is None:
        return None

    cipher = Fernet(load_key())

    decrypted = cipher.decrypt(
        encrypted_data.encode("utf-8")
    )

    return decrypted.decode("utf-8")