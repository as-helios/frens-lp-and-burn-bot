import json
import os
import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv
from web3 import Web3
from web3_multi_provider import FallbackProvider

load_dotenv()
secret = os.getenv('SECRET')
wallet_address = os.getenv('WALLET_ADDRESS')
burn_address = os.getenv('BURN_ADDRESS')
if not wallet_address or not burn_address or not secret or secret == 'changeme':
    print("Setup your .env file")
    sys.exit()
os.makedirs(log_dir := "./data/logs/", exist_ok=True)
logging.basicConfig(
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level='INFO',
    handlers=[
        TimedRotatingFileHandler(
            "{}/{}.log".format(log_dir, wallet_address),
            when="midnight",
            interval=1,
            backupCount=69
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
os.makedirs("data/wallets", exist_ok=True)
wallet_keystore = "./data/wallets/{}/keystore".format(wallet_address)
if not os.path.isfile(wallet_keystore):
    logging.error("Wallet keystore not found")
    sys.exit()
private_key = Web3().eth.account.decrypt("\n".join([line.strip() for line in open(wallet_keystore, 'r+')]), secret)
account = Web3().eth.account.from_key(private_key)
web3 = Web3(FallbackProvider(json.load(open('./data/rpc_servers.json'))))

# token contract addresses
reward_tokens = [
    "0xCc78A0acDF847A2C1714D2A925bB4477df5d48a6",  # atropa
    "0x0b1307dc5D90a0B60Be18D2634843343eBc098AF",  # legal
    "0x0EB4EE7d5Ff28cbF68565A174f7E5e186c36B4b3",  # mantissa
    "0xd6c31bA0754C4383A41c0e9DF042C62b5e918f6d",  # teddy bear
    "0x463413c579D29c26D59a65312657DFCe30D545A1",  # treasury bill
    "0x4243568Fa2bbad327ee36e06c16824cAd8B37819"  # tsfi
]
wpls_address = "0xA1077a294dDE1B09bB078844df40758a5D0f9a27"

# frens
frens_address = '0x67e3fec6F92e1bCD82E1CD96835220FF9121595E'
frens_abi = json.load(open('./data/abi/ERC20.json'))
frens_contract = web3.eth.contract(address=frens_address, abi=frens_abi)

# router
router_address = '0x165C3410fC91EF562C50559f7d2289fEbed552d9'
router_abi = json.load(open('./data/abi/Uniswapv2_Router.json'))
router_contract = web3.eth.contract(address=router_address, abi=router_abi)


def main():
    # begin work
    for token_address in reward_tokens:
        # load target token
        token_contract = web3.eth.contract(address=token_address, abi=json.load(open('./data/abi/ERC20.json')))
        token_symbol = token_contract.functions.symbol().call()

        # check token is approved
        token_balance = token_contract.functions.balanceOf(wallet_address).call()
        if not token_balance:
            logging.info("No balance found for {}. Skipping...".format(token_symbol))
            continue
        else:
            logging.info("Adding LP for {}...".format(token_symbol))

        # approve target token with pulsex
        allowed_balance = token_contract.functions.allowance(wallet_address, router_address).call()
        if token_balance > allowed_balance:
            try:
                total_supply = token_contract.functions.totalSupply().call()
                tx = token_contract.functions.approve(router_address, total_supply).build_transaction({
                    "nonce": web3.eth.get_transaction_count(web3.to_checksum_address(wallet_address)),
                    "from": wallet_address,
                    "chainId": 369
                })
                web3.eth.estimate_gas(tx)
                tx_signed = web3.eth.account.sign_transaction(tx, private_key=account.key)
                tx_hash = web3.eth.send_raw_transaction(tx_signed.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            except Exception as e:
                logging.error("Could not approve token spender: {}".format(e))
                continue
            else:
                logging.info("Approved PulseX v2 as spender for {} ({})".format(token_symbol, tx_hash.hex()))

        # approve frens with pulsex
        frens_balance = frens_contract.functions.balanceOf(wallet_address).call()
        allowed_balance = frens_contract.functions.allowance(wallet_address, router_address).call()
        if frens_balance > allowed_balance:
            try:
                total_supply = frens_contract.functions.totalSupply().call()
                tx = frens_contract.functions.approve(router_address, total_supply).build_transaction({
                    "nonce": web3.eth.get_transaction_count(web3.to_checksum_address(wallet_address)),
                    "from": wallet_address,
                    "chainId": 369
                })
                web3.eth.estimate_gas(tx)
                tx_signed = web3.eth.account.sign_transaction(tx, private_key=account.key)
                tx_hash = web3.eth.send_raw_transaction(tx_signed.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            except Exception as e:
                logging.error("Could not approve token spender: {}".format(e))
                continue
            else:
                logging.info("Approved PulseX v2 as spender for FRENS ({})".format(tx_hash.hex()))

        try:
            expected_output_amounts = router_contract.functions.getAmountsOut(
                token_balance,
                [token_address, wpls_address, frens_address]
            ).call()
        except Exception as e:
            logging.error("Could not estimate output amounts: {}".format(e))
            continue

        # add liquidity to frens
        try:
            tx = router_contract.functions.addLiquidity(
                token_address,
                frens_address,
                expected_output_amounts[0],
                expected_output_amounts[-1],
                0,
                0,
                account.address,
                int(time.time()) + (60 * 5)
            ).build_transaction({
                "nonce": web3.eth.get_transaction_count(web3.to_checksum_address(wallet_address)),
                "from": wallet_address,
                "chainId": 369
            })
            web3.eth.estimate_gas(tx)
            tx_signed = web3.eth.account.sign_transaction(tx, private_key=account.key)
            tx_hash = web3.eth.send_raw_transaction(tx_signed.rawTransaction)
            tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        except Exception as e:
            logging.error("Could not add to LP: {}".format(e))
            continue
        else:
            logging.info("Added LP for {} and FRENS ({})".format(token_symbol, tx_hash.hex()))

        # transfer lp tokens to burn address
        for log in tx_receipt['logs']:
            if log['topics'][0].hex() != '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                continue
            log_from = web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            log_to = web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
            if log_from != "0x0000000000000000000000000000000000000000" and log_to != wallet_address:
                continue
            # extract lp tokens just created
            lp_balance = int(log['data'].hex(), 16)
            # load the lp token contract
            lp_contract = web3.eth.contract(address=log['address'], abi=json.load(open('./data/abi/ERC20.json')))
            # check if wallet has enough lp tokens to send
            _lp_balance = lp_contract.functions.balanceOf(wallet_address).call()
            if _lp_balance < lp_balance:
                break
            # send only the amount of lp tokens created earlier
            try:
                tx = lp_contract.functions.transfer(burn_address, lp_balance).build_transaction({
                    "nonce": web3.eth.get_transaction_count(web3.to_checksum_address(wallet_address)),
                    "from": wallet_address,
                    "chainId": 369
                })
                web3.eth.estimate_gas(tx)
                tx_signed = web3.eth.account.sign_transaction(tx, private_key=account.key)
                tx_hash = web3.eth.send_raw_transaction(tx_signed.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            except Exception as e:
                logging.error("Could not transfer LP tokens: {}".format(e))
            else:
                logging.info("Transfered LP tokens to {} ({})".format(burn_address, tx_hash.hex()))
            finally:
                break


if __name__ == '__main__':
    print("-" * 50)
    print("Frens LP and Burn")
    print("-" * 50)
    main()
    print("-" * 50)
