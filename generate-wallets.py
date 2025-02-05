import json
import os
import sys

from dotenv import load_dotenv
from web3 import Web3
from web3_multi_provider import FallbackProvider

load_dotenv()
web3 = Web3(FallbackProvider(json.load(open('./data/rpc_servers.json'))))


def generate_wallet(amount):
    addresses = []
    for i in list(range(0, amount)):
        account = Web3().eth.account.create()
        keystore = Web3().eth.account.encrypt(account.key.hex(), os.getenv('SECRET'))
        folder = "./data/wallets/{}".format(account.address)
        os.makedirs("data/wallets", exist_ok=True)
        os.makedirs(folder, exist_ok=True)
        open("{}/keystore".format(folder), 'w').write(json.dumps(keystore, indent=4))
        addresses.append(account)
    return addresses


# show help
if 'help' == sys.argv[1].lower():
    print("Generates 1 or more number of wallet keystores and optionally displays their private keys.\n")
    print("Example Usage:")
    command = "python {}".format(sys.argv[0])
    examples = ['--create', '--create 1', '--create 1 --show-private-keys', '--show-private-keys 0x1234567891234567891234567891234567891234']
    for e in examples:
        print("{} {}".format(command, e))
    sys.exit()

# make sure you have a unique secrets
secret = os.getenv('SECRET')
if secret == 'changeme' or not secret:
    print('Change your secret in .env')
    sys.exit()

# display private key arg to add to metamask/rabby
if "--show-private-keys" in sys.argv:
    public_key_index = sys.argv.index("--show-private-keys")
    show_private_key = True
elif "-s" in sys.argv:
    public_key_index = sys.argv.index("-s")
    show_private_key = True
else:
    public_key_index = None
    show_private_key = False

# create specified number of wallets arg
if "--create" in sys.argv or "-c" in sys.argv:
    if "--create" in sys.argv:
        amount_index = sys.argv.index("--create")
    else:
        amount_index = sys.argv.index("-c")

    try:
        amount = sys.argv[amount_index + 1]
    except IndexError:
        arg = sys.argv[amount_index].split('=')
        if len(arg) == 1 or not arg[1].isnumeric():
            amount = 1
        else:
            amount = arg[1]
    if not str(amount).isnumeric():
        print("Invalid amount")
        sys.exit()
    else:
        amount = int(amount)
else:
    amount = 0

# create new wallets
if amount:
    # generate X wallets based on sys.argv
    wallets = generate_wallet(int(amount))
    print("\nGenerated {} wallets\n".format(amount))
    # display the generated wallet's keys
    for wallet in wallets:
        print("Public Key: {}".format(wallet.address))
        if show_private_key:
            print("Private Key: {}\n".format(wallet.key.hex()))

# show private keys only
elif show_private_key:
    wallet_address = None
    try:
        wallet_address = sys.argv[public_key_index + 1]
    except IndexError:
        arg = sys.argv[public_key_index].split('=')
        if len(arg) > 1:
            wallet_address = arg[1]
        else:
            print("Not enough args")
            sys.exit()

    try:
        wallet_address = web3.to_checksum_address(wallet_address)
    except ValueError:
        print("Invalid wallet address {}".format(wallet_address))
    else:
        print("\nPublic Key: {}".format(wallet_address))
        secret = os.getenv('SECRET')
        private_key = Web3().eth.account.decrypt("\n".join([line.strip() for line in open("./data/wallets/{}/keystore".format(wallet_address), 'r+')]), secret)
        wallet = Web3().eth.account.from_key(private_key)
        print("Private Key: {}".format(wallet.key.hex()))
        print()
