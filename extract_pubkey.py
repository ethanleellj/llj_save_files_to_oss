import paramiko

key_path = "/workspace/ssh_key"

try:
    key = paramiko.RSAKey.from_private_key_file(key_path)
    pub_key = f"ssh-rsa {key.get_base64()}"
    print(pub_key)
    print(f"\nKey bits: {key.get_bits()}")
    print(f"Fingerprint: {key.get_fingerprint().hex()}")
except Exception as e:
    print(f"RSA error: {e}")
    try:
        key = paramiko.Ed25519Key.from_private_key_file(key_path)
        pub_key = f"ssh-ed25519 {key.get_base64()}"
        print(pub_key)
    except Exception as e2:
        print(f"Ed25519 error: {e2}")
