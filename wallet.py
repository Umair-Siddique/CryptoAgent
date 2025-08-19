import base64
import os
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Your x402 wallet keys from environment variables ---
wallet_data = {
    "id": os.getenv('WALLET_ID'),
    "privateKey": os.getenv('WALLET_PRIVATE_KEY_B64')
}

# Validate that required environment variables are set
if not wallet_data["id"] or not wallet_data["privateKey"]:
    raise ValueError("Missing required environment variables: WALLET_ID and WALLET_PRIVATE_KEY_B64")

# --- Decode base64 to bytes ---
decoded_bytes = base64.b64decode(wallet_data["privateKey"])

# --- Use only first 32 bytes (Ethereum-compatible private key) ---
private_key_bytes = decoded_bytes[:32]
private_key_hex = "0x" + private_key_bytes.hex()

# --- Create wallet account ---
account = Account.from_key(private_key_hex)

print("Wallet Initialized ✅")
print(f"Wallet ID: {wallet_data['id']}")
print(f"Address: {account.address}")
print(f"Private Key (hex): {private_key_hex}")