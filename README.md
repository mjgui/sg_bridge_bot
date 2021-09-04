# SG Bridge Bot
<img src="https://user-images.githubusercontent.com/9080115/132089017-4d733fee-2a90-4469-891f-055d48bbb55a.png" width="100" height="100">

A Telegram Bot to host games of [Singaporean (Floating) Bridge](https://en.wikipedia.org/wiki/Singaporean_bridge) built in Python3

_Try it out on Telegram at [@sg_bridge_bot](https://t.me/sg_bridge_bot)!_

**Note:** This was built as a project after a long hiatus from coding (>2 years?) so I'm not that proud of the code, but I thought I might as well release it on GitHub regardless as someone might find it interesting

## Setup

**1. Install Dependencies**

The only dependency is `python-telegram-bot`, though do take note that this project uses an outdated version of the library
```bash
pip3 install python-telegram-bot==12.4.2
```

**2. Setup Bot Token**
Setup a new bot on Telegram with [BotFather](https://core.telegram.org/bots#6-botfather) and obtain the API Token. Add your token at line 21 of `bot.py`

**3. Run Bot**
```
python3 bot.py
```
