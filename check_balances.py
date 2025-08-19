import os
from web3 import Web3
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get wallet address and RPC URL from environment variables
ADDR = os.getenv('WALLET_ADDRESS')
BASE_RPC = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')

# Validate required environment variables
if not ADDR:
    raise ValueError("Missing required environment variable: WALLET_ADDRESS")

# Token addresses (these can stay as constants since they're public)
USDC  = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")  
USDbC = Web3.to_checksum_address("0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA")

ERC20_ABI = [{
    "inputs": [{"name":"account","type":"address"}],
    "name": "balanceOf",
    "outputs": [{"name":"","type":"uint256"}],
    "stateMutability": "view",
    "type": "function"
}]

w3 = Web3(Web3.HTTPProvider(BASE_RPC))

print("Base ETH:", w3.from_wei(w3.eth.get_balance(ADDR), "ether"))

def bal(token):
    c = w3.eth.contract(address=token, abi=ERC20_ABI)
    return c.functions.balanceOf(ADDR).call()

usdc_raw  = bal(USDC)   # 6 decimals
usdbc_raw = bal(USDbC)  # 6 decimals

print("USDC  (Base):", Decimal(usdc_raw)  / Decimal(10**6))
print("USDbC (old) :", Decimal(usdbc_raw) / Decimal(10**6))