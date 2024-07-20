# frens-lp-and-burn-bot

Pairs your reward tokens with FRENS once per day. Burning is optional.

## Getting Started

- Rename `sample.env` to `.env`
- Change your `SECRET` to a random string. Don't lose this.
- Generate your bot wallet
```commandline
python generate-wallets.py --create 1
```
- Save the bot wallet address to `.env` as `WALLET_ADDRESS`
- Save your main wallet or a burn address as `BURN_ADDRESS`
- Send PLS for gas and FRENS to your bot wallet
- Start the bot
```commandline
python main.py
```

## Notes

- By setting your own wallet to the burn address the bot will send all LP tokens back to you
- You are responsible for gas. The bot will not sell any reward tokens