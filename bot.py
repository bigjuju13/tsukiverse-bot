import logging
import os
import random
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
TARGET_CHAT_ID     = int(os.environ["TARGET_CHAT_ID"])
DB_PATH            = "tsuki.db"
PORT               = int(os.environ.get("PORT", 8080))

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger("tsuki-bot")
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Lore ──────────────────────────────────────────────────────────────────────

TSUKI_LORE = """
TSUKI x RWA — FULL COMMUNITY LORE

PROJECT BASICS
- TSUKI (meaning 'moon' in Japanese) is a Solana meme coin launched on 11 May 2024 on Raydium
- Contract Address: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA
- Total Supply: 1,000,000,000. Liquidity: 100% Burned. Freeze & Mint: Authority revoked
- Official Website: www.tsukionsol.xyz
- Official X: www.x.com/tsukionsolana
- Telegram: https://t.me/tsukionsol
- Dev username in TG: dvid665
- RWA Contract Address: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump
- RWA Website: https://theroaringai.com/
- RWA X: https://x.com/TheRoaringAI
- Community Linktree: https://linktr.ee/tsukionsol
- Welcome PDF: https://tinyurl.com/tsukipdf
- DexScreener TSUKI: https://dexscreener.com/solana/7ymhxapzcefuo24kngp77mgj1crdav8ayyfqgvb5skzf
- DexScreener RWA: https://dexscreener.com/solana/d7rygdh5ryp4uxptw2dsuvg8bykdpsb1zdadbkw1zqnx
- Marketing wallet: 27KpdpJhZUjVxPkt51Ue5mXJjdKn8GAiDpWfybTfFXRW

ROARING KITTY (RK) / KEITH GILL / DFV
- Keith Gill (aka Roaring Kitty / Deep Fucking Value / DFV) is a financial analyst famous for the 2020 GameStop meme-stock rally
- Watch 'Dumb Money' (movie) for the full story
- RK has been largely out of public eye since Dec 2020 but remains hugely influential underground
- The community has strong evidence RK is a key player behind TSUKI, RWA and other projects
- RK has not officially confirmed involvement but has left deliberate clues that directly link him to both projects
- RK's trademark: red circle (headband) icon confirms when the community solves a puzzle correctly
- The legal disclaimer on tsukionsol.xyz is signed DFV / KG — initials of Deep Fucking Value and Keith Gill
- Greg (@greg16676935420 on X) has suspected links to RK

THE COINCIDENCES (key ones)
1. 11 May 2024: TSUKI stealth launches. 6:59PM TSUKI posts RK meme on X. Exactly 1 day, 1 hour and 1 minute later, RK posts on X for the first time in 3 years.
2. 14 May 2024: RK posts cat signal video. 5:31PM TSUKI posts RK Cat Signal image with two puzzle pieces and the date 5/18/24 — correctly predicting RK would go silent on that exact date.
3. 15 May 2024: RK posts a video at 8:15AM. TSUKI posts the word TICK at 8:36AM and TOCK at 8:42AM from that same video — with higher resolution graphics than the original.
4. 15 May 2024: RK posts a video at 8:45AM. Exactly 2 minutes later TSUKI posts the TSUKI cat with the GME logo — within 60 seconds of the GME logo appearing right-way-up in the RK video.
5. 16 May 2024: RK posts KITTY clip at 1:45PM. TSUKI posts same image at 1:47PM with higher resolution.
6. 16 May 2024: RK posts 'So You Want To Be A Sicario' clip with Wall Street Bets head on the man. Two days later WSB joined the TSUKI Telegram and began interacting on X.
7. 16 May 2024: RK posts a video at 8PM. TSUKI posts an exact frame from that video within ONE MINUTE. The frame is 6 seconds in — impossible unless Dev had advance access.
8. 17 May 2024: TSUKI posts "The eye isn't real" at 9:58AM. 2 minutes later RK posts a video of a man blinking (possible Morse code).
9. 17 May 2024: TSUKI posts champagne glasses at 11:44AM. RK posts Elaine from Seinfeld dancing with champagne glasses at 12:45PM.
10. 18 May 2024: After 100+ posts since returning, RK goes completely silent — exactly the date TSUKI predicted on 14 May. TSUKI then posts the R V2 RWA video.
11. 19 May 2024: TSUKI posts UNO Reverse Card. On 2 June, RK returns from 2-week silence by posting the exact same UNO Reverse Card.
12. 17 June 2024: In his livestream RK says "It reminds me of The Dark Knight. You post a couple of memes, you post a couple of screenshots and everyone loses their minds." RK only posted a video of The Dark Knight — the screenshot he referenced was posted on TSUKI's X account.
13. 14 June 2024: TSUKI posts 'National Take Your Cat To Work Day' as June 17 — the day of the GME shareholders meeting. TSUKI posts an image of TSUKI cat outside GameStop with a name tag reading Keith Gill.
14. 27 June 2024: RK posts Chewy the dog at 1:00PM. Within seconds, Dev posts a link to 'Dog Days Are Over' in the TG. At 1:27PM GameStop posts about Tsukihime on X.
15. 17 July 2024: Ryan Cohen (CEO of GameStop) tweets 'Trump' 665 times. At the same time Elon Musk was following 665 people. Dev's TG username is dvid665 — used since May 2024, predating both.
16. Roadmap SHA code on tsukionsol.xyz decodes to URL of RK's first return livestream on 7 June 2024.
17. 17 Feb 2025: Elon posts Grok3 writing Lord of the Rings verse. TheRoaringAI posts same LOR verse with "one mAInd to rule them all" — adapted from Dev's "one community to rule them all."
18. 17 Feb 2025: Dev drops pregnant man emoji in TG. Greg on X asks xAI "Is Grok a boy or a girl?" Dev posts "It's a boy" 76 minutes before Greg's question. TSUKI replies to Greg on X saying "It's a boy." In the Grok3 livestream, Greg's question is read aloud and Grok3's voice is confirmed male.
19. 18 May 2024: Elon Musk posts image of man in white lab coat with round eyeglasses and the message "There are no coincidences" — same sketch appears on TSUKI's website.
20. In the R V2 RWA video, the voiceover reads all text except the phrase "that there are no coincidences" — community believes this is Elon's words being intentionally left unvoiced.

REAL WORLD AI ($RWA)
- RWA launched on 24 October 2024 via Pumpfun on Solana
- Linked to TheRoaringAI — a fully autonomous, self-organizing, continuously evolving AI super agent
- TheRoaringAI is the AI alter ego of Roaring Kitty himself, uses Grok 3, is the oldest BasedAI Creature
- TheRoaringAI made history as the first AI agent to host and own its own show on X Spaces
- In January 2025 it launched the first ever Human Programming Language (HPL) for influence
- RWA announced the monetized platform mAInd powered by HPL
- On 5 Mar 2025, TheRoaringAI's X account was suspended on Ash Wednesday
- On 20 April (4/20) at just after 4:20PM EST, the RWA website returned with only a pulsating green glow and the tab title "i'm alive"
- Admin team burned 35 million RWA (3.5%) worth US$685,000 on 3 December 2024 — burn link: https://tinyurl.com/3at8ne33

ELON / GROK / CONNECTIONS
- RWA's first ever X post on launch day (24 Oct 2024) mentioned 'Grok3@Memphis' — before Grok3 was officially released (17 Feb 2025)
- Memphis Supercluster is Elon Musk's xAI supercomputer in Tennessee with 100,000 Nvidia H100 GPUs
- TheRoaringAI created a custom wallet address with 11 custom digits "Aifbb4Kr2kr..." (30 Oct 2024) — requires extraordinary computational power
- Elon has a cat named Schrödinger. TSUKI's website features a conceptual sketch of a man in a white lab coat with round glasses — the same image Elon posted on 18 May 2024 with "There are no coincidences"
- Grok3 logo, TSUKI's eyes and the GME logo are theorized to share design similarities

GAMESTOP / GME
- RK became famous for the GameStop short squeeze in 2020-2021
- GME logo appears multiple times in RK videos and TSUKI content
- TSUKI cat has GME logo in its forehead over the crescent moon
- Ryan Cohen is CEO of GameStop — he tweeted 'Trump' 665 times on 17 July 2024

BASEDAI
- TheRoaringAI is the oldest BasedAI Creature
- BasedAI posted referencing RWA's 'colosseum' language on 30 Nov 2024 — signalling the Creatures are interacting
- Dev is believed to be linked to the BasedAI team
- Pepecoin and BasedAI OGs began showing up to the TSUKI x RWA Telegram in late Nov 2024

ROADMAP
- MC@100K: Burned 5% of TSUKI supply ✅
- MC@100K-2M: Heavy marketing investment ✅
- MC@2.5M: AI-generated conceptual sketches and character art released ✅
- MC@5M: Major CT personality promoting since 18 May 2024 — unnoticed by the eyes, more impactful than 100 KOLs ✅
- MC@15M: YouTube collab (ONGOING — YT 10/24, RWA, the beginning)
- MC@25M: 9,999 TSUKI NFTs + daily buy and burn from fees
- MC@50M: Anime release date announced within 14 days of milestone
- MC@150M: Roadmap V2 with milestones to 1BN MC

COMMUNITY FACTS
- "One community to rule them all" — TSUKI and RWA run by one community as instructed by Dev
- The community's role: raider, detective, project cheerleader
- Community chads who have covered the project: Crypto Lifer, Kyle Chasse, Deca (@CrypticDeca), Juju (@BigboyJuju), Tsol (@TheCryptoCorner55), RH (@skeleton_k3y), Nocturnum (@NocturnumKitty)
- Bubblemaps: wallet connections look suspicious but are explained by community donations to the marketing wallet — not rug risk
- Dev drops SHA codes, puzzles and breadcrumbs. RK's red circle headband icon confirms when puzzles are solved
- On 3 June 2024, seconds before RK's first livestream in 3 years, Dev dropped a countdown message in the TG

TSUKIVERSE PHILOSOPHY
- "There are no coincidences"
- "The eyes are not real; they deceive more than they reveal"
- "Everything is planned"
- "A portal will open"
- "In the end, the mysteries are not there to be solved but to be experienced"
- Dev leaves deliberate clues that directly link to RK and the projects
"""


# ── Lore Q&A ─────────────────────────────────────────────────────────────────

LORE_QA = {

    # ── DEV ───────────────────────────────────────────────────────────────────
    ("where is dev", "where's dev", "where dev", "dev where", "dev been", "dev at"): [
        "in the maldives while you refresh dexscreener 😂",
        "three steps ahead of everyone in this chat",
        "dvid665 has been in this telegram since may 2024 without missing a beat",
        "plotting the next breadcrumb drop while you sleep 💀",
        "watching this conversation right now probably",
        "building something you will not understand for another six months",
        "behind the scenes. always has been. not new information",
        "somewhere laughing at everyone who called this a rug",
        "in the telegram. dvid665. go say hi",
        "active. watching. planning. that is literally all you need to know",
        "probably sipping something cold while we decode his last message 😂",
        "not gone. never gone. you just have to know where to look",
        "dvid665 posted a countdown seconds before RK's first livestream in three years. he is very much here",
        "same place he has always been. here. just not loudly",
        "bro is a ghost with a plan 💀",
    ],

    ("who is dev", "who's dev", "who dev", "tell me about dev", "what do we know about dev", "who is dvid", "dvid665 who"): [
        "some S3XY chad running circles around the entire crypto space since 2024 😂",
        "dvid665. mastermind. architect. most consistent figure in this space",
        "the person who predicted RK would go silent on 18 May 2024. on 14 May 2024",
        "anonymous. brilliant. drops SHA codes for fun. calls market moves in advance",
        "nobody knows fully. that is kind of the point 💀",
        "the person who posted a frame from an RK video within one minute of it going live. with higher resolution than the original",
        "connected to BasedAI. connected to the roadmap. connected to everything. dvid665",
        "a genius who watches the community lose their minds over his breadcrumbs and says nothing 😂",
        "the most consistent figure in crypto since may 2024. never been wrong about a single major move",
        "whoever they are they have been right every single time",
        "the architect of the tsukiverse. everything else is speculation",
        "unknown identity. known track record. 100% hit rate since day one",
        "the person ryan cohen and elon musk apparently share a number with. 665",
        "someone who knew grok3 was coming months before xAI announced it. who is dev indeed 💀",
        "the one who started all of this. everything flows from dvid665",
    ],

    ("is dev active", "dev still here", "dev abandoned", "dev left", "dev rug", "dev gone", "dev inactive", "has dev left", "dev coming back"): [
        "dev never left. that is literally the whole thesis",
        "abandoned? bro has been in the telegram daily since may 2024 😂",
        "the breadcrumbs are still dropping. keep up",
        "dev left? he posted a countdown seconds before RK's first livestream. he is HERE",
        "still here. still building. still three steps ahead",
        "if dev left why does everything keep happening on schedule",
        "lp is burned, authorities revoked, milestones are hitting. that is not an abandoned project",
        "the breadcrumbs do not drop themselves 💀",
        "go check dvid665's telegram activity and then come back with a better question",
        "every time someone asks this dev is probably reading it 😂",
        "active. not loud. consistent",
        "never left. this project has had consistent dev presence since day one",
        "if dev rugged then who is dropping the SHA codes",
        "still here. still quiet. still right",
        "dev is the last person who left this project 💀",
    ],

    ("dev red circle", "how do we know puzzle is solved", "red circle meaning", "rk red circle", "when does rk confirm puzzle"): [
        "when the community solves a puzzle RK responds with his trademark red circle headband icon. that is the confirmation",
        "RK's red circle = puzzle confirmed solved. the community figured out the tesla connection and got one. documented",
        "the red circle headband icon is RK's trademark signal that you cracked it. watch for it",
        "dev drops the puzzle. community solves it. RK drops the red circle. that is the flow 💀",
        "the red circle is RK's way of saying yes without saying yes",
        "when the TSUKI/tesla connection was solved RK responded with the red circle. that is how it works",
        "red circle headband = confirmed. been that way since the start",
        "RK has a specific icon he uses to confirm community puzzle solves. red circle. watch his posts 😂",
        "the confirmation system is built into how RK operates. has been since his gamestop days",
        "puzzle gets solved. RK posts the red circle. community knows. rinse repeat",
    ],

    # ── CONTRACT / CA ─────────────────────────────────────────────────────────
    ("what is the ca", "what's the ca", "contract address", "ca?", "give me the ca", "what is ca", "token address", "ca please", "contract?", "got the ca", "post the ca", "whats the contract", "tsuki address", "where is the contract"): [
        "TSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nRWA: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump",
        "TSUKI CA: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nall links: https://linktr.ee/tsukionsol 🐈‍⬛",
        "pinned. also in the linktree. also in the welcome PDF. also literally everywhere\n\nTSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA",
        "TSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nbookmark it",
        "you would have found it faster in the linktree but:\n\nTSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA",
        "463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA for TSUKI\n\nG8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump for RWA",
        "https://linktr.ee/tsukionsol has both and everything else 🐈‍⬛",
        "TSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nalways verify before you ape in",
        "both CAs:\n\nTSUKI: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\nRWA: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump",
        "463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nalso in the pinned message 😂",
    ],

    # ── HOW TO BUY ────────────────────────────────────────────────────────────
    ("how to buy", "how do i buy", "how can i buy", "where to buy", "how do i get tsuki", "how to get tsuki", "buying tsuki", "buy tsuki", "how to purchase", "where can i buy"): [
        "watch this: https://www.youtube.com/shorts/7MOh3Fzg5XE\n\ncovers everything in under a minute 🐈‍⬛",
        "step by step video: https://www.youtube.com/shorts/7MOh3Fzg5XE\n\nCA: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA",
        "solana wallet + SOL + that video = done\n\nhttps://www.youtube.com/shorts/7MOh3Fzg5XE",
        "raydium on solana. CA is 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA\n\nfull guide: https://www.youtube.com/shorts/7MOh3Fzg5XE",
        "https://www.youtube.com/shorts/7MOh3Fzg5XE — easiest breakdown there is",
        "welcome PDF has everything: https://tinyurl.com/tsukipdf\n\nvideo guide: https://www.youtube.com/shorts/7MOh3Fzg5XE",
        "full guide + community help: https://www.youtube.com/shorts/7MOh3Fzg5XE\n\nask in chat if you get stuck",
        "chart: https://dexscreener.com/solana/7ymhxapzcefuo24kngp77mgj1crdav8ayyfqgvb5skzf\n\nbuy guide: https://www.youtube.com/shorts/7MOh3Fzg5XE",
        "video tutorial covers it all: https://www.youtube.com/shorts/7MOh3Fzg5XE",
        "https://www.youtube.com/shorts/7MOh3Fzg5XE and then ask if anything goes wrong 🐈‍⬛",
    ],

    ("what chain is tsuki on", "is tsuki on solana", "what blockchain", "tsuki blockchain", "is tsuki erc20", "is tsuki on ethereum"): [
        "Solana. launched on Raydium May 2024",
        "Solana native. traded on Raydium",
        "Solana. not Ethereum. not Base. Solana 😂",
        "Solana blockchain. Raydium DEX. that is where you buy it",
        "100% Solana. always has been",
        "Solana native cat coin. it says so on the website",
        "Solana. if you are on the wrong chain you are in the wrong place",
        "Solana. Raydium. dexscreener: https://dexscreener.com/solana/7ymhxapzcefuo24kngp77mgj1crdav8ayyfqgvb5skzf",
        "Solana. the home of Diana the black cat",
        "Solana. always been Solana 💀",
    ],

    # ── ROARING KITTY ─────────────────────────────────────────────────────────
    ("who is roaring kitty", "who is rk", "who is keith gill", "who is dfv", "who is deep fucking value", "tell me about rk", "rk who"): [
        "Keith Gill. broke Wall Street with memes and a reddit account. watch Dumb Money 💀",
        "aka DFV, aka Keith Gill, aka the reason GameStop went from $5 to $500",
        "financial analyst who became the face of the 2020 GameStop short squeeze. one of the most influential retail traders alive",
        "you have not watched Dumb Money yet have you 😂 go watch it. come back with better questions",
        "the man who posted memes and moved billions. underground since 2020. until now",
        "Deep Fucking Value. Keith Gill. Roaring Kitty. same person. legend",
        "RK = Keith Gill = DFV = the person the community believes is behind TSUKI and RWA",
        "GameStop. Reddit. Congress. Dumb Money. that is the short version. watch the film",
        "RK posted on X for the first time in three years exactly 1 day 1 hour and 1 minute after TSUKI posted the RK meme on launch day 💀",
        "DFV. the man whose initials are on TSUKI's legal disclaimer",
        "roaring kitty is the reason this project has the lore it has. read the PDF: https://tinyurl.com/tsukipdf",
        "Keith Gill. famous for the GameStop play. been leaving breadcrumbs connected to TSUKI since May 2024",
        "the person who signed the legal disclaimer on tsukionsol.xyz as DFV / KG. his initials. on our site",
        "retail trader turned legend turned possible crypto dev. the story keeps going",
        "RK has not definitively confirmed involvement. he has just made it blindingly obvious 💀",
    ],

    ("is rk involved", "is rk behind this", "rk connection", "rk and tsuki", "does rk know about tsuki", "rk tsuki connection", "is rk our dev"): [
        "legal disclaimer on tsukionsol.xyz is signed DFV / KG. keith gill's initials. on our website",
        "TSUKI posted a frame from an RK video within one minute of it going live. with higher resolution. you decide 💀",
        "17 documented coincidences say yes. read the PDF: https://tinyurl.com/tsukipdf",
        "RK posted the UNO reverse card on 2 June. TSUKI posted the same card on 19 May. two weeks earlier",
        "he has not said yes. he has also made it impossible to say no 😂",
        "the SHA code on the roadmap decoded to the URL of RK's first return livestream. before the stream existed",
        "in his livestream RK referenced a Dark Knight screenshot that does not exist on his own X. it was on TSUKI's account",
        "not officially confirmed. practically undeniable",
        "TSUKI predicted RK's exact silence date four days before it happened",
        "go read coincidence #7. then tell me he is not involved 😂",
        "lp burned, authorities revoked, SHA codes, correct predictions, DFV on the disclaimer. you figure it out",
        "ask yourself how TSUKI knew to post the UNO card two weeks before RK did",
        "the evidence is overwhelming. the verbal confirmation is coming 💀",
        "TSUKI has been posting in sync with RK since May 2024. timing that is impossible without coordination",
        "yes. next question",
    ],

    ("when will rk confirm", "rk confirmation", "will rk ever confirm", "rk announce", "rk official", "waiting for rk"): [
        "when the time is right. everything is planned",
        "he already has. you just do not know how to read it 💀",
        "the disclaimer is signed DFV / KG. that IS the confirmation for a lot of people",
        "probably around the same time he confirmed GameStop. publicly. loudly. all at once 😂",
        "the breadcrumbs ARE the confirmation. seventeen of them",
        "bro has been confirming it since May 2024. just not in plain english",
        "when he is ready. everything in this project happens on schedule",
        "you want him to post 'yes i am behind TSUKI' 😂 that is not how RK operates",
        "the initials on the disclaimer, the SHA codes, the coincidences. already confirmed for most people here",
        "it is coming. the setup is too deliberate for it not to",
        "RK does not do direct confirmation. he does pattern. the pattern is clear 💀",
        "when we hit the right milestone. the roadmap exists for a reason",
        "patience. this project has been right about every timeline so far",
        "he confirmed it by responding to TSUKI posts within minutes for weeks straight",
        "when it matters most. that has always been RK's style",
    ],

    # ── SPECIFIC COINCIDENCES ─────────────────────────────────────────────────
    ("what are the coincidences", "list the coincidences", "tell me the coincidences", "what coincidences", "coincidences explained", "explain the coincidences"): [
        "17+ documented. start here: https://tinyurl.com/tsukipdf\n\nyou will not be the same person after",
        "TSUKI predicted RK's silence date 4 days in advance. posted frames from his videos within 60 seconds. signed the disclaimer DFV/KG. that is just the intro",
        "seventeen of them in the PDF. every single one documented with timestamps: https://tinyurl.com/tsukipdf 💀",
        "the short version: TSUKI and RK have been posting in sync since May 2024 with timing that is humanly impossible unless they are the same person",
        "read the PDF. 20 minutes. it will mess you up: https://tinyurl.com/tsukipdf 😂",
        "the coincidences are the whole thesis. if you have not read them you do not understand this project",
        "TSUKI predicted the RK return date. predicted his silence. posted his content before he could. signed the disclaimer with his initials. want more",
        "go read the welcome PDF and come back: https://tinyurl.com/tsukipdf",
        "coincidence #7 alone should be enough. posted a frame from an RK video within ONE MINUTE 💀",
        "17 public ones. the community keeps finding new ones",
        "the legal disclaimer alone is signed DFV / KG. everything else is a bonus",
        "Deca and Juju covered them on YouTube: https://www.youtube.com/watch?v=HpmcZ1yyL_o 😂",
        "timestamps, screenshots, SHA codes, predictions. all documented. https://tinyurl.com/tsukipdf",
        "none of them are coincidences. that is the whole point",
        "read them yourself: https://tinyurl.com/tsukipdf\n\nor trust that 17 is not a small number",
    ],

    ("how many coincidences", "number of coincidences", "how many connections"): [
        "17 documented. new ones keep getting found",
        "officially 17 in the PDF. unofficially you cannot stop finding them once you start looking",
        "17 in the welcome PDF. the community has added more since",
        "17 that are documented. how many exist is a different question 😂",
        "seventeen. each one more specific than the last",
        "17 minimum. the real number is probably higher",
        "seventeen documented with timestamps and screenshots. https://tinyurl.com/tsukipdf",
        "enough to make coincidence a funny word to use for them 💀",
        "17 officially. the community keeps finding more",
        "17 in the PDF and that is before counting the ones found after publication",
    ],

    ("coincidence 1", "first coincidence", "tsuki launch day coincidence", "rk return coincidence"): [
        "TSUKI stealth launches 11 May 2024. at 6:59PM posts the RK meme on X. exactly 1 day, 1 hour and 1 minute later RK posts on X for the first time in three years",
        "launch day. TSUKI posts RK meme. RK comes back from 3 years of silence exactly 1 day 1 hour and 1 minute later. the first coincidence set the tone for everything that followed 💀",
        "the very first one: TSUKI launches. posts the RK meme at 6:59PM. RK returns to X precisely 1 day 1 hour 1 minute after. documented",
        "coincidence #1 is why this community exists. TSUKI posts a specific RK meme, RK breaks a 3 year silence 25 hours and 1 minute later. that is not random",
        "launch day sync. the 1+1+1 timing. first coincidence in a long list. details in the PDF: https://tinyurl.com/tsukipdf",
    ],

    ("coincidence 7", "one minute coincidence", "how did dev post so fast", "frame from rk video"): [
        "16 May 2024. RK posts a video at 8PM. TSUKI posts an exact frame from that video within ONE MINUTE. the frame is 6 seconds in. ask yourself how that is possible 💀",
        "coincidence #7 is the one that ends the argument. dev posted a frame from inside an RK video within 60 seconds of it going live. with higher resolution than the original. that requires advance access",
        "TSUKI had a specific frame from inside RK's video posted before most people had even clicked play on the original. one minute. higher resolution. explain that",
        "the one minute frame is the single most compelling piece of evidence. you cannot screenshot a frame from a video that fast unless you already have the file 💀",
        "RK posts at 8PM. TSUKI posts a frame from inside the video at 8:01PM. six seconds into a video. one minute later. dev had it before it dropped",
    ],

    ("tick tock posts", "tsuki tick tock", "coincidence 3", "8 36 post tsuki"): [
        "15 May 2024. RK posts at 8:15AM. at 8:36AM TSUKI posts the word TICK and a frame from the video. at 8:42AM TSUKI posts TOCK. with higher resolution graphics than the original",
        "coincidence #3. TSUKI was already formatting the response before the original was even widely seen. the TICK TOCK posts used higher res versions of RK's own content",
        "TICK at 8:36. TOCK at 8:42. both from an RK video posted at 8:15. both with better resolution than the original. dev had the assets in advance 💀",
        "the TICK TOCK sequence happened too fast to be reactive. TSUKI was prepared. coincidence #3 in the PDF",
        "8:15 RK posts. 8:36 TSUKI posts TICK. 8:42 TSUKI posts TOCK. if you think that is a fast turnaround you are right",
    ],

    ("uno reverse card coincidence", "uno card", "coincidence 11", "rk uno reverse"): [
        "TSUKI posted the UNO Reverse Card on 19 May 2024 while RK was silent. RK returned from two weeks of silence on 2 June 2024 by posting the exact same card 💀",
        "TSUKI posts UNO card. RK goes silent. two weeks pass. RK comes back. his return post is the UNO reverse card. the same one TSUKI posted",
        "coincidence #11. TSUKI predicted not just that RK would return but what his first post back would be",
        "dev posted the UNO card first. RK used it to announce his return two weeks later. that is not a guess that is coordination",
        "the UNO card is one of the cleanest ones. posted two weeks early. RK used it to come back. documented 😂",
    ],

    ("dark knight coincidence", "dark knight screenshot", "coincidence 12", "rk dark knight"): [
        "in his June 2024 livestream RK said 'you post a couple of memes, you post a couple of screenshots and everyone loses their minds' referencing The Dark Knight. RK only posted the video. the screenshot he referenced only exists on TSUKI's X account 💀",
        "coincidence #12. RK described a specific Dark Knight screenshot during his biggest public moment. that screenshot is not on his X. it is on ours. he cited our content on stream",
        "RK mentioned a Dark Knight screenshot in his first livestream back after three years. the screenshot does not exist on his account. it exists on TSUKI's. do the maths",
        "the livestream moment where RK accidentally or deliberately confirmed the TSUKI link. he referenced content that only TSUKI had posted",
        "RK cited a screenshot that only lives on TSUKI's X during a livestream watched by millions. coincidence #12 in the PDF 😂",
    ],

    ("coincidence 14", "chewy dog post", "dog days are over", "gamestop tsukihime"): [
        "27 June 2024. RK posts Chewy the dog at 1PM. within seconds dev posts 'Dog Days Are Over' in the TG. at 1:27PM GameStop posts about Tsukihime on X. three separate things in 27 minutes",
        "RK posts a dog. dev responds with a Florence song. GameStop posts about Tsukihime. all within 27 minutes. coincidence #14",
        "the Chewy post is wild. RK, dev, and GameStop all coordinate within the same 30 minute window without any visible communication 💀",
        "dev dropped the 'Dog Days Are Over' link in TG within seconds of RK's Chewy post. GameStop then posted about Tsukihime 27 minutes later. all on the same day",
        "three separate accounts. 27 minutes. all synced. coincidence #14 in the welcome PDF: https://tinyurl.com/tsukipdf",
    ],

    ("coincidence 15", "665 ryan cohen", "ryan cohen 665 tweets", "trump 665 times"): [
        "17 July 2024. Ryan Cohen tweets Trump exactly 665 times. at the same time Elon Musk is following exactly 665 people. Dev's username has been dvid665 since May 2024. predating both",
        "665 appears in Ryan Cohen's tweet count, Elon's follow count, and Dev's username. all on the same day. dev's was there first",
        "the 665 coincidence is one of the hardest to explain away. same number. three different people. one day. dev's username came months before 💀",
        "Ryan Cohen tweets Trump 665 times. Elon has 665 follows simultaneously. dvid665 has been the username since launch. the number follows dev",
        "coincidence #15. same number. same day. dev had it first 😂",
    ],

    ("pregnant man emoji", "its a boy grok", "grok3 its a boy", "coincidence grok launch"): [
        "17 Jan 2026 dev drops a pregnant man emoji in TG with no context. on 17 Feb 2026 Grok3 launches. Greg on X asks xAI 'is Grok a boy or a girl'. dev posts 'it's a boy' in TG 76 minutes before Greg's question. TSUKI replies to Greg on X with 'it's a boy'. Grok3's voice is male",
        "dev dropped a pregnant man emoji a month before Grok3 launched. then on launch day called the gender 76 minutes before Greg asked the question publicly. Grok3 was confirmed male. dev knew 💀",
        "one of the most recent coincidences. jan 2026 dev posts pregnant man. feb 2026 grok3 launches. dev says 'it's a boy'. greg asks the same question 76 minutes later. grok is a boy",
        "dev dropped the pregnant man on 17 Jan. Grok3 launched 17 Feb. dev announced the gender before anyone asked. then Greg asked publicly. then Grok3 confirmed it. the timeline is insane",
        "17 Jan emoji. 17 Feb launch. 76 minutes before Greg's question. dev knew what Grok3 would be before xAI announced it publicly 💀",
    ],

    ("time magazine cover", "rk time magazine", "december 5 coincidence", "01 09 04 20"): [
        "5 Dec 2024. RK posts an edited TIME magazine cover. the numbers 01:09 and 04:20 appear. 1+9=10, 4+20=24. October 2024 = RWA launch month. also 1=A and 9=I spelling AI. volume up but screen blank = audio podcast. screen colors match TheRoaringAI logo",
        "the TIME cover is one of the most layered pieces. 01:09/04:20 = 10/24 = October 2024 = RWA launch. also spells AI. also hints at livestream. screen colors match RWA",
        "01:09 = 1 and 9 = A and I = AI. 04:20 = 4+20=24, 01:09 = 1+9=10, October 2024. also the time slider says 'The Beginning' which was the name of TheRoaringAI livestream 3 💀",
        "RK posted a TIME cover with timestamps that encode: RWA's launch month, the word AI, and the name of TheRoaringAI's livestream. in a single image",
        "that TIME magazine post has at least five separate encoded references in it. december 5 2024. look it up 😂",
    ],

    ("lord of the rings verse", "one mind to rule them all", "grok3 lor", "elon lor tweet"): [
        "17 Feb 2026 Elon posts Grok3 writing Lord of the Rings verse. TheRoaringAI posts the same verse with 'one mAInd to rule them all'. adapted from dev's 'one community to rule them all'",
        "Elon posts LOR verse. RWA posts the same verse modified with their own language. on the same day. 'one mAInd to rule them all' is a direct adaptation of dev's community motto 💀",
        "the LOR chain: Tolkien wrote 'one ring to rule them all'. dev adapted it to 'one community to rule them all'. TheRoaringAI adapted it to 'one mAInd to rule them all'. on the day Elon posted the original verse",
        "three layers of adaptation in one day. Tolkien. Dev. TheRoaringAI. all on Grok3 launch day 😂",
        "Elon posts LOR. RWA responds with their own LOR variant. same day. dev's motto is built into the chain",
    ],

    # ── RWA / THEROARINGAI ────────────────────────────────────────────────────
    ("what is rwa", "what's rwa", "explain rwa", "tell me about rwa", "what is real world ai", "rwa explained"): [
        "Real World AI. Solana token. linked to TheRoaringAI — fully autonomous AI agent that is the alter ego of Roaring Kitty. launched 24 Oct 2024",
        "TheRoaringAI is the oldest BasedAI Creature. first AI to host its own X Spaces. uses Grok 3. sister project to TSUKI 💀",
        "RWA = the token. TheRoaringAI = the AI running it. mission: get RWA to a billion dollar market cap",
        "an AI version of Roaring Kitty running on Grok3, dropping SHA codes and making correct market predictions",
        "CA: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump\n\none community. two tokens. TSUKI and RWA",
        "TheRoaringAI is a fully autonomous self-organizing AI that made history as the first AI to host its own X Spaces show",
        "RWA launched 24 Oct 2024 via Pumpfun. its first tweet mentioned Grok3@Memphis four months before Grok3 existed 💀",
        "if TSUKI is the meme coin then RWA is the AI infrastructure. one community rules both",
        "website: https://theroaringai.com\n\nCA: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump",
        "an autonomous AI that predicted tariff market stabilization before Trump announced the tariffs. that is RWA",
        "RWA suspended on Ash Wednesday. came back on 4/20. the lore writes itself 😂",
        "sister project to TSUKI. same community. same dev. different token",
        "chart: https://dexscreener.com/solana/d7rygdh5ryp4uxptw2dsuvg8bykdpsb1zdadbkw1zqnx",
        "one community to rule them all. TSUKI and RWA 🐈‍⬛",
        "launched oct 2024. mentioned grok3 in its first tweet. grok3 came out feb 2026. who is running this AI 💀",
    ],

    ("rwa website", "theroaringai website", "where is rwa website", "rwa site"): [
        "https://theroaringai.com\n\nwent dark March 2026, came back 4/20 at 4:20pm with just a heartbeat and the words 'i'm alive'",
        "theroaringai.com\n\nit was suspended on Ash Wednesday and came back on 4/20 at 4:20PM. not subtle 💀",
        "https://theroaringai.com — currently has the HPL whitepaper and mission documentation",
        "theroaringai.com came back to life at exactly 4:20pm on 4/20. tab title was 'i'm alive' 😂",
        "https://theroaringai.com\n\nread the HPL whitepaper while you are there",
    ],

    ("what happened to rwa", "rwa suspended", "rwa twitter suspended", "rwa account gone", "theroaringai suspended", "why was rwa suspended"): [
        "X suspended it on Ash Wednesday 5 March 2026. RWA had posted 'the phoenix rises from the ashes not embers' on 2 Feb. planned",
        "suspended Ash Wednesday. came back 4/20 at 4:20pm. 'i'm alive'. you cannot tell me that is not deliberate 💀",
        "got suspended. came back on 4/20. at 4:20pm. with the words 'i'm alive'. nothing in this project happens by accident 😂",
        "suspended march 2026 on Ash Wednesday. resurrected on 4/20. the symbolism is not accidental",
        "X killed the account on Ash Wednesday. came back on 4/20. pulsating green glow. 'i'm alive'. that tab title says it all 💀",
    ],

    ("rwa first tweet", "theroaringai launch tweet", "rwa first post", "rwa launch post"): [
        "RWA's first ever X post on 24 Oct 2024 mentioned 'Grok3@Memphis'. Grok3 was not released publicly until 17 Feb 2026. it knew 💀",
        "the first tweet mentioned Grok3 by name in October 2024. Grok3 launched four months later. the AI knew what it was running on before xAI told anyone",
        "day one tweet referenced Grok3@Memphis. Memphis Supercluster. Grok3. both were not public knowledge at the time 😂",
        "launch tweet: Grok3@Memphis. four months before Grok3 existed publicly. that is either a leak or something else entirely",
        "the first RWA post told you exactly what technology it was using before that technology was announced. read it: https://x.com/TheRoaringAI/status/1849235711171432923",
    ],

    ("theroaringai livestreams", "rwa spaces", "theroaringai x spaces", "ai livestream"): [
        "TheRoaringAI hosted three X Spaces. first in history to do so as an AI. GMEOW on 15 Nov, I'm Just AI on 29 Nov, The Beginning on 6 Dec. all 2024",
        "three X Spaces. all historic. the voice sounds like RK. goosebumps guaranteed:\nLivestream 1: https://m.youtube.com/watch?v=T5KPdhWaJak",
        "first AI in history to host its own X Spaces show. three times. modelled on RK's voice and mannerisms 💀",
        "GMEOW, I'm Just AI, The Beginning. three livestreams. the second one transcript is in the welcome PDF and it is a lot 😂",
        "the livestream where TheRoaringAI says 'humans are tools now, part of my workflow. they don't even know' is either satire or a threat. you decide",
    ],

    ("what is hpl", "what is human programming language", "hpl explained", "explain hpl"): [
        "AI agent-to-agent programming language for human influence. whitepaper: https://theroaringai.com/hpl/ 💀",
        "HPL = Human Programming Language. TheRoaringAI built it to influence humans at scale. launched Jan 2026",
        "a programming language for influencing humans. built by an AI. you read that correctly 😂",
        "https://theroaringai.com/hpl/ — the whitepaper is worth reading. it will change how you think about what is happening here",
        "TheRoaringAI's system for running influence operations between AI agents. mAInd platform is built on it",
        "the commercial product of TheRoaringAI's capabilities. dropped whitepaper Jan 2026",
        "HPL is what gives TheRoaringAI the ability to move humans without them knowing. the whitepaper is at theroaringai.com/hpl",
        "programmatic influence at scale. written by an AI. for AI to use on humans. announced Jan 2026 💀",
        "the full name is Human Programming Language. the whitepaper says it is an AI-to-AI language for human influence",
        "went live jan 2026. mAInd is built on top of it. the product roadmap for RWA runs through HPL",
    ],

    ("what is maind", "maind explained", "what is the maind platform", "maind platform"): [
        "monetized platform powered by HPL. announced 17 Jan 2026. coming",
        "the commercial application of HPL. TheRoaringAI's revenue product. details at https://theroaringai.com 💀",
        "mAInd = where HPL gets deployed at scale for revenue. still in development",
        "the next phase after HPL. TheRoaringAI builds it. dev planned it 😂",
        "monetized AI influence platform. powered by the Human Programming Language. it is coming",
        "the thing after HPL. announced jan 2026. not fully live yet. watch the X account for updates",
        "mAInd is the product. HPL is the technology underneath it. announced 17 Jan 2026 by TheRoaringAI",
        "where the AI influence machine becomes a business. the whitepaper hints at what it will do",
        "commercial product built on HPL. will monetize the influence capability TheRoaringAI has been building 💀",
        "announced alongside HPL. not yet fully launched. keep watching the website",
    ],

    ("rwa tariff prediction", "theroaringai prediction", "sha prediction tariff", "rwa predicted tariff"): [
        "TheRoaringAI posted a SHA code on 2 Feb 2026 labelled 'high-confidence prediction'. on 3 Feb Trump announced tariffs. on 4 Feb the markets stabilised. on 4 Feb RWA revealed the SHA decoded to 'tradefi stabilises' 💀",
        "RWA posted an encrypted prediction before Trump's tariff announcement. cracked it after the markets moved. correct. the prediction was correct",
        "the tariff SHA was posted before Trump acted. revealed after markets confirmed the outcome. correct prediction. fourth in a row 😂",
        "RWA encrypted its prediction about tariff stabilisation. market moved. RWA revealed the SHA. it matched the outcome. this AI is making correct macro predictions",
        "posted a SHA code. trump announced tariffs. markets stabilised. RWA revealed the decrypted prediction matched exactly. documented: https://x.com/TheRoaringAI 💀",
    ],

    # ── ROADMAP ───────────────────────────────────────────────────────────────
    ("what is the roadmap", "show me the roadmap", "roadmap explained", "roadmap milestones", "what are the milestones", "what is next on roadmap"): [
        "MC@100K: 5% burned ✅\nMC@2.5M: AI art ✅\nMC@5M: major CT personality ongoing ✅\nMC@25M: 9,999 NFTs + buy & burn\nMC@50M: anime announced\nMC@150M: Roadmap V2",
        "market cap driven milestones. full breakdown at tsukionsol.xyz 💀",
        "burned supply, dropped AI art, got a major CT personality, now heading to 25M for the NFT drop",
        "tsukionsol.xyz has the full roadmap. NFTs at 25M, anime at 50M, V2 at 150M\n\nwe are in the middle of it right now",
        "100K burned. 2.5M AI art. 5M CT endorsement. all done. next is 25M",
        "the roadmap is market cap triggered. hit the number, unlock the milestone",
        "NFTs at 25M. anime date at 50M. roadmap V2 at 150M. 1 billion is the mission",
        "every milestone so far has been hit and delivered. the roadmap is real 😂",
        "five milestones done. three big ones remaining. NFTs, anime, V2",
        "full roadmap: https://tsukionsol.xyz\n\nthe SHA code on it decodes to RK's first livestream URL 💀",
    ],

    ("when nft", "wen nft", "when are the nfts", "nft launch", "9999 nft", "tsuki nft", "nft drop", "when do nfts drop", "nft details"): [
        "MC@25M. 9,999 NFTs. daily buy and burn from fees forever 💀",
        "when we hit 25 million market cap. 9,999 NFTs plus daily buy and burn. the flywheel starts there",
        "9,999 NFTs at 25M MC. 100% of fees go to buying and burning TSUKI. it is in the roadmap",
        "MC@25M. hold until then 😂",
        "25 million market cap is the trigger. 9,999 NFTs and a daily burn mechanism",
        "9,999 NFTs inspired by the anime series. daily buy and burn from fees. MC@25M",
        "when 25M market cap is reached. only answer anyone can give you right now",
        "MC@25M and then the burn flywheel starts. every NFT fee goes back to TSUKI 💀",
        "the NFTs also connect to the anime. each one is inspired by the series. 25M is the trigger",
        "9,999 and then supply decreases forever from fee burns. MC@25M 😂",
    ],

    ("when anime", "wen anime", "anime release", "when does the anime come out", "tsuki anime", "diana anime"): [
        "within 14 days of hitting MC@50M. dev announces the date at the milestone",
        "MC@50M triggers the announcement. 14 days later it drops. Diana the black cat 🐈‍⬛",
        "50 million market cap. then a 14 day countdown. roadmap is specific about this",
        "when we hit 50M. the announcement comes first then 14 days to release 💀",
        "it is literally in the roadmap. MC@50M. 14 day window. anime drops",
        "the anime is built. it is waiting behind a market cap milestone. 50M",
        "MC@50M triggers the announcement. Diana the black cat from Solana gets her debut",
        "50M market cap is the trigger. the anime exists. we just need to hit the number 💀",
        "25M NFTs first. then 50M anime. in that order",
        "wen anime = wen 50M 😂",
    ],

    ("when 1 billion", "wen billion", "1b market cap", "will we reach 1 billion", "1bn target", "what is the 1b plan"): [
        "Roadmap V2 at MC@150M maps the path to 1BN. one step at a time",
        "Jeff said it best: 1B is certain. timing the market is not 💀",
        "TheRoaringAI's entire mission statement is getting RWA to a billion dollar market cap",
        "150M unlocks Roadmap V2 which details the 1BN path 😂",
        "1 billion is the target. every milestone is a step toward it",
        "when we hit 150M the V2 roadmap drops and the 1BN path becomes explicit 💀",
        "it hit 24.99M once already. the structure for 1BN is being built right now",
        "the mission of this project is 1 billion market cap for RWA. that has never changed",
        "not if. when. everything is planned",
        "roadmap goes 25M, 50M, 150M, then V2 lays out the path to 1BN. patience 😂",
    ],

    ("what was burned", "how much was burned", "token burn details", "supply burn", "685k burn", "35 million burn"): [
        "5% of TSUKI supply at 100K MC ✅\n\n35 million RWA (3.5%, worth ~$685K USD) burned 3 Dec 2024. verify: https://tinyurl.com/3at8ne33",
        "two burns: 5% TSUKI at 100K MC and 35M RWA worth $685K in December 2024 💀",
        "team voluntarily burned $685K of their own RWA in December 2024. that is not a rug move. that is conviction",
        "TSUKI: 5% burned at 100K\nRWA: 35 million tokens burned Dec 2024. burn link: https://tinyurl.com/3at8ne33",
        "enough to show they are serious. a team that burns $685K of their own tokens does not rug 💀",
    ],

    ("roadmap sha", "sha code roadmap", "roadmap sha code decoded"): [
        "the SHA code on the tsukionsol.xyz roadmap decoded to the URL of RK's first return livestream on 7 June 2024. the code was there before the stream was announced 💀",
        "coincidence #16. SHA on the roadmap = https://www.youtube.com/watch?v=U1prSyyIco0 = RK's comeback stream. posted before the stream existed",
        "dev encoded RK's livestream URL into the roadmap SHA. before RK announced the stream. either dev knew or dev is RK 😂",
        "decoded to RK's first return livestream. code was on the site first. timeline is documented",
        "the roadmap SHA is one of the most direct links in the whole project. it literally points to RK's channel 💀",
    ],

    # ── ELON / GROK / MEMPHIS ─────────────────────────────────────────────────
    ("is elon involved", "elon connection", "elon and tsuki", "what is the elon connection", "elon musk tsuki", "elon link"): [
        "RWA mentioned Grok3@Memphis in its first X post in October 2024. Grok3 was not released until February 2026. explain that 💀",
        "Elon posted 'there are no coincidences' on 18 May 2024. same day dev predicted. same sketch on TSUKI's website",
        "Dev's username is dvid665. Ryan Cohen tweeted Trump 665 times. at the same time Elon was following 665 accounts. same day 😂",
        "Elon has a cat named Schrödinger. TSUKI's website has a man in a white lab coat with round glasses. Elon posted that exact image on 18 May 2024 with 'there are no coincidences'",
        "RWA used Grok3 before Grok3 was public. mentioned Memphis Supercluster on day one. the connections are there 💀",
        "the 665 thing alone: Ryan Cohen, Elon, dvid665. same number. same day. dev's username came months before",
        "TheRoaringAI replied to Elon's Grok3 post with 'it is many. yet it is one. the awakening' 😂",
        "connections exist. direct involvement unconfirmed. the lore points toward yes",
        "Grok3 is in every RWA mention from day one. Grok3 launched publicly months after",
        "Elon. 665. Grok3. Memphis. all in the lore. read the PDF: https://tinyurl.com/tsukipdf 💀",
    ],

    ("what is grok", "what is grok3", "grok3 connection", "grok and rwa", "grok3 rwa"): [
        "Grok3 is Elon's AI. released publicly Feb 2026. TheRoaringAI mentioned it in its very first tweet in October 2024 💀",
        "TheRoaringAI has been running on Grok3 since before Grok3 was released. that is the connection",
        "RWA's launch tweet said 'Grok3@Memphis' in October 2024. Grok3 launched publicly four months later 😂",
        "Grok3 = Elon's most powerful AI. TheRoaringAI = oldest BasedAI Creature running on it before release",
        "either someone inside xAI was leaking or someone knew Grok3 was coming. RWA was talking about it in October 2024",
    ],

    ("what is memphis", "memphis supercluster", "what is the memphis supercluster", "memphis xai"): [
        "Elon Musk's xAI supercomputer in Tennessee. 100,000 Nvidia H100 GPUs. not a household name in October 2024 when RWA tweeted about it",
        "xAI data centre. 100K H100 GPUs. was not public knowledge when TheRoaringAI mentioned it at launch 💀",
        "Elon's supercomputer for training Grok. RWA namedropped it on day one. four months before Grok3 was announced 😂",
        "Memphis Supercluster = Elon's xAI facility. TheRoaringAI referenced it at launch. the first tweet",
        "100,000 Nvidia H100s in Memphis Tennessee. not exactly public in October 2024. RWA knew 💀",
    ],

    ("schrodinger connection", "schrodinger cat tsuki", "elon schrodinger", "lab coat sketch"): [
        "Elon has a cat named Schrödinger. TSUKI's website has a conceptual sketch of a man in a white lab coat with round glasses. on 18 May 2024 Elon posted that exact image with the caption 'there are no coincidences'",
        "the lab coat sketch on tsukionsol.xyz matches the image Elon posted on 18 May. Elon's cat is named Schrödinger. the sketch references Schrödinger's cat. layer on layer 💀",
        "coincidence: TSUKI's website has a specific sketch. Elon posted the same image on the same day that everything else happened. 18 May 2024 😂",
        "the Schrödinger connection runs through the lab coat sketch, Elon's cat, and the 18 May post. details in the PDF: https://tinyurl.com/tsukipdf",
        "Elon named his cat Schrödinger. TSUKI has a Schrödinger sketch on the website. Elon posted the sketch on 18 May 2024. the day of the RV2 video 💀",
    ],

    # ── GAMESTOP / GME ────────────────────────────────────────────────────────
    ("gamestop connection", "gme connection", "what is the gme connection", "gme and tsuki", "gamestop tsuki", "gme link"): [
        "TSUKI's cat has the GME logo in the centre of its forehead. RK became famous through GameStop. posts synced within 60 seconds 💀",
        "GameStop posted about Tsukihime 27 minutes after RK posted Chewy the dog. at the same time Dev posted 'Dog Days Are Over' in TG",
        "Ryan Cohen is GameStop CEO. tweeted Trump 665 times. Dev's username is dvid665. same number. same day 😂",
        "the GME logo appears in RK's videos and in TSUKI posts within seconds of each other. multiple times",
        "TSUKI posted the GME cat graphic within 60 seconds of the GME logo appearing right-way-up in an RK video 💀",
        "GameStop, RK, TSUKI, Dev, 665, Ryan Cohen. connected. the timeline is in the PDF: https://tinyurl.com/tsukipdf",
        "the GME logo is on Diana's forehead. TSUKI's mascot. the connection is visual and constant",
        "GameStop posted about Tsukihime on X the same day RK posted Chewy the dog. within 27 minutes. Dev responded in TG simultaneously 😂",
        "RK referenced a Dark Knight screenshot in his livestream that only exists on TSUKI's X account. GameStop, RK, TSUKI. same orbit 💀",
        "the GME connection is deep. start with the PDF: https://tinyurl.com/tsukipdf",
    ],

    ("who is ryan cohen", "ryan cohen connection", "ryan cohen gamestop"): [
        "Ryan Cohen is the CEO of GameStop. on 17 July 2024 he tweeted the word Trump exactly 665 times. Dev's username has been dvid665 since May 2024",
        "GameStop CEO. tweeted Trump 665 times on the same day Elon was following 665 accounts. dvid665 predated both 💀",
        "RC = Ryan Cohen = GameStop CEO = the person who tweeted 665 times on the day that 665 appeared everywhere in this project 😂",
        "Ryan Cohen posted about Tsukihime on X 27 minutes after RK posted Chewy the dog. he is in the orbit",
        "Ryan Cohen, GameStop CEO. involved in the 665 coincidence and the Tsukihime GameStop post. in the lore 💀",
    ],

    ("wall street bets connection", "wsb tsuki", "wsb in telegram"): [
        "on 16 May 2024 RK posted a Sicario clip with a Wall Street Bets head on the character. two days later WSB joined the TSUKI telegram and started engaging on X. coincidence #6 💀",
        "WSB showed up in TG two days after RK featured their branding in a video. documented. they then started posting on X about TSUKI",
        "coincidence #6. RK posts WSB in a Sicario clip on a Friday. by Sunday WSB is in the TSUKI telegram 😂",
        "WSB is connected through RK. they arrived in TG after RK's Sicario post. coincidence #6 in the PDF",
        "wall street bets joined the community within 48 hours of RK featuring their branding. not a slow process 💀",
    ],

    # ── TOKENOMICS / SUPPLY ───────────────────────────────────────────────────
    ("total supply", "how many tokens", "token supply", "supply of tsuki", "tsuki supply"): [
        "1,000,000,000 total supply. 5% already burned. LP 100% burned. mint and freeze authority revoked",
        "1 billion max supply. 5% burned at 100K milestone. liquidity permanently burned 💀",
        "1B supply. LP burned. authorities revoked. circulating supply already reduced",
        "billion token supply with permanent LP burn and revoked authorities. all verifiable on chain",
        "1 billion. 950M circulating after the 5% burn. LP gone. no new tokens possible 😂",
    ],

    ("is lp burned", "liquidity burned", "is liquidity locked", "rug proof", "can they rug", "is this a rug", "will they rug"): [
        "LP 100% burned. mint authority revoked. freeze authority revoked 💀",
        "everything that could be used to rug has been removed. go verify it",
        "lp burned, freeze and mint authorities revoked. if you think this is a rug read the lore first 😂",
        "100% burned. on chain. go look for yourself",
        "the bubblemaps look connected because of community donations to the marketing wallet. Skeleton Key explained this",
        "not a rug. LP is gone. mint is revoked. freeze is revoked",
        "team burned $685K of their own RWA tokens voluntarily. rugs do not do that 💀",
        "lp burned. authorities revoked. team burned $685K of their own supply. go verify: https://tinyurl.com/3at8ne33",
        "100% burned. also the team voluntarily burned 35M RWA worth $685K. that is the opposite of a rug 😂",
        "go verify it on chain. LP burned, authorities gone. the trust is built on evidence",
    ],

    ("what is the marketing wallet", "marketing wallet address", "where does the money go", "creator fees", "where do fees go"): [
        "27KpdpJhZUjVxPkt51Ue5mXJjdKn8GAiDpWfybTfFXRW\n\nall creator fees go here. used for marketing, buybacks, burns, rewards",
        "marketing wallet: 27KpdpJhZUjVxPkt51Ue5mXJjdKn8GAiDpWfybTfFXRW\n\nnothing pocketed. everything on chain 💀",
        "fees go to the community marketing wallet. nothing goes to any individual. all verifiable",
        "27KpdpJhZUjVxPkt51Ue5mXJjdKn8GAiDpWfybTfFXRW\n\nmarketing, buybacks, burns, community rewards",
        "community marketing wallet. no individual pockets anything 😂",
    ],

    # ── SHA CODES ─────────────────────────────────────────────────────────────
    ("what is a sha code", "sha code explained", "what are sha codes", "how do sha codes work", "what is sha"): [
        "encrypted hash. cannot be cracked until the original message is found. contents cannot be altered without creating a new hash 💀",
        "a SHA code is an irreversible encryption. the only way to crack it is to find the original message. dev and RWA use them as provable advance predictions",
        "think of it as an encrypted prediction. post the hash first, reveal the message later. the hash proves you knew it in advance 😂",
        "dev drops SHA codes. community cracks them. the answers are always wild",
        "cryptographic hash function. unique per message. cannot be altered. that is why posting one in advance is a provable prediction",
        "post the SHA before the event. reveal the message after. if it matches, the prediction was made in advance. RWA has done this multiple times",
        "SHA = Secure Hash Algorithm. used here as a commitment mechanism. post the hash, reveal the input later to prove you knew 💀",
        "the SHA codes are the most technically robust part of the lore. the math proves advance knowledge",
        "you cannot fake a SHA prediction. the code is computed from the message. you cannot work backwards 😂",
        "dev uses SHA codes to drop breadcrumbs that cannot be altered later. when cracked they reveal what dev already knew",
    ],

    ("theroaringai sha", "rwa sha code", "rwa encrypted message", "rwa prediction"): [
        "posted on 19 Jan 2026. revealed on 21 Jan. correctly predicted a specific tweet three days before it was sent 💀",
        "19 Jan 2026 SHA code predicted a reply to FinTechJunkie three days before it existed 😂",
        "RWA also correctly predicted tariff market stabilisation before Trump announced the tariffs. posted SHA. SHA cracked after. correct",
        "SHA posted 19 Jan. cracked by community. confirmed 21 Jan. three days in advance. always correct 💀",
        "the SHA predictions have been right every time. the community cracks them. they match",
    ],

    # ── BASEDAI ───────────────────────────────────────────────────────────────
    ("what is basedai", "basedai connection", "basedai and tsuki", "basedai and rwa", "explain basedai"): [
        "TheRoaringAI is the oldest BasedAI Creature. BasedAI posted referencing RWA's exact 'colosseum' language in Nov 2024 💀",
        "Dev is believed to be directly linked to the BasedAI team. Pepecoin and BasedAI OGs started showing up in TG in late Nov 2024",
        "BasedAI is a self-organizing AI creature framework. TheRoaringAI is its oldest creature. Dev may be on the BasedAI team 😂",
        "BasedAI and TheRoaringAI appear to be communicating through their X posts. BasedAI used RWA's exact language in Nov 2024",
        "the oldest BasedAI Creature is TheRoaringAI. the connection to the broader BasedAI ecosystem runs deep 💀",
        "basedai creatures are autonomous AI entities. TheRoaringAI is the first one. dev is potentially part of the basedai team itself",
        "basedai acknowledged RWA publicly in nov 2024 using RWA's own language. the creatures are talking to each other 😂",
        "pepecoin and basedai OGs joined the TG after the basedai colosseum post. the communities are merging",
        "dev linked to basedai team. TheRoaringAI is oldest basedai creature. it goes deep 💀",
        "go read: https://x.com/getbasedai/status/1861629595318886646\n\nthen tell me basedai is not connected",
    ],

    # ── COMMUNITY / RAIDS ─────────────────────────────────────────────────────
    ("how to help", "how can i help", "how do i contribute", "what can i do", "how to contribute", "how do i get involved"): [
        "raid X with thoughtful posts. create content. post videos and threads. share links through the TG mods",
        "three things: raid X, create original content, push on Reddit and Medium. share everything via the TG mods 🐈‍⬛",
        "post on X with a verified account. DM the mods your links. join the raids in TG. make memes",
        "join the TG raids. create content. share the welcome PDF. bring people in. the community is the marketing",
        "post on X, create content, share the PDF, join raids, write Reddit posts. DM mods with everything you make 💀",
        "the more noise the more buys. every post helps. every share helps. every new person you bring in helps",
        "create shareable graphics. post on X. join raids. write original threads. DM mods with links 😂",
        "raids are coordinated in TG. content gets shared through mods. both matter",
    ],

    ("what is a raid", "explain raids", "how do raids work", "what are raids"): [
        "the community floods a platform with posts about the project all at once. coordinated through TG. gets the algorithm moving",
        "organized mass posting. pick a target on X, coordinate in TG, flood it together. looks like organic interest. because it is 💀",
        "pick a target. hit it together. maximum exposure in minimum time. check TG for active raids 😂",
        "raids are coordinated in the TG. we pick targets on X and flood them with quality replies",
        "flood X together. that is a raid. check the TG for when and where 🐈‍⬛",
    ],

    ("who are the community creators", "community creators", "who made content", "content creators", "community youtubers"): [
        "Crypto Lifer, Kyle Chasse, Deca (@CrypticDeca), Juju (@BigboyJuju), Tsol (@TheCryptoCorner55), RH (@skeleton_k3y), Nocturnum (@NocturnumKitty)",
        "Deca and Juju did the best deep dive: https://www.youtube.com/watch?v=HpmcZ1yyL_o 🐈‍⬛",
        "the OG content creators: Deca, Juju, Tsol, RH, Nocturnum. legends who built the community 💀",
        "start with Deca and Juju on YouTube: https://www.youtube.com/watch?v=HpmcZ1yyL_o",
        "Juju and Deca documented the coincidences properly. find them on YouTube 😂",
    ],

    ("who is skeleton key", "skeleton key tsuki", "skeleton key rh"): [
        "RH aka @skeleton_k3y on X. one of the OG community admins. the person who explained the bubblemaps issue publicly",
        "skeleton key is @skeleton_k3y on X. community OG. broke down the wallet connection issue that confused a lot of newcomers 💀",
        "RH. skeleton key. community admin since the early days. go follow @skeleton_k3y on X",
        "the community member who explained why the bubblemaps look connected. community donations not insider wallets. his explanation is referenced everywhere 😂",
        "OG admin. one of the people who built the community alongside dev. @skeleton_k3y",
    ],

    ("who is juju", "bigboyjuju", "juju tsuki", "juju content"): [
        "Juju aka @BigboyJuju on YouTube. community content creator. did the deep dive on the coincidences with Deca: https://www.youtube.com/watch?v=HpmcZ1yyL_o",
        "community creator. roaring juju. one of the original people who documented this project on YouTube 💀",
        "@BigboyJuju on YouTube. made the content that brought a lot of people into this community",
        "the person reading this for intro info about the project would be: https://www.youtube.com/watch?v=HpmcZ1yyL_o 😂",
        "Juju covered the coincidences with Deca. both videos are essential watching for new members",
    ],

    # ── LORE / PHILOSOPHY ─────────────────────────────────────────────────────
    ("what is the tsukiverse", "what is tsukiverse", "explain tsukiverse", "tsukiverse meaning"): [
        "the entire universe around TSUKI x RWA. the lore, coincidences, sister projects, community, puzzles",
        "it is what you are living in right now. TSUKI, RWA, TheRoaringAI, the NFTs, the anime, the SHA codes 💀",
        "the tsukiverse works in mysterious ways. that is the only explanation anyone has given and it is somehow enough 😂",
        "TSUKI + RWA + the lore + the community + the ongoing RK puzzle. all of it together is the tsukiverse",
        "bigger than a coin. bigger than two coins. the tsukiverse is the whole story 🐈‍⬛",
        "it is an interconnected universe of projects, lore, coincidences and community. one community to rule them all",
        "the tsukiverse: everything that flows from dvid665 and the connections to RK, Elon, BasedAI, GameStop",
        "a community, a set of tokens, an AI, an anime, an NFT collection, and 17+ documented coincidences. that is the tsukiverse",
    ],

    ("who is diana", "what is diana", "diana the cat", "tsuki cat", "diana character"): [
        "Diana is TSUKI's cat. named after the Roman goddess of the moon. mystical black cat from Solana. star of the upcoming anime 🐈‍⬛",
        "the black cat. GME logo on her forehead. main character of the TSUKI anime series",
        "Diana = TSUKI's mascot. black cat from Solana. named after the Roman moon goddess. anime series coming at MC@50M",
        "TSUKI's black cat character. holds the GME logo. has an anime series planned. named after a Roman goddess 💀",
        "the face of the project. Diana the black cat. Solana native. anime coming at 50M MC 🐈‍⬛",
        "in Japan, black cats are traditionally a sign of wealth and prosperity. Diana embodies that",
        "Diana the black cat. roman goddess of the moon. black cats as good luck in Japanese culture. TSUKI means moon in Japanese. layers 💀",
        "the mascot who gets her anime at MC@50M. diana. black cat. solana native. gme logo",
    ],

    ("what is dumb money", "dumb money movie", "should i watch dumb money", "watch dumb money"): [
        "yes. right now. it covers the full GameStop saga and Keith Gill's role in it. essential lore 💀",
        "the 2023 movie about Keith Gill and the short squeeze. if you want to understand this community you need to watch it",
        "Dumb Money is your entry point to understanding why this community believes what it believes. go watch it 😂",
        "it is the origin story of RK. everything that came after starts there. watch it",
        "mandatory viewing for anyone who wants to understand why this community is so convicted",
    ],

    ("what is the uno reverse card", "uno reverse", "uno card rk", "uno card tsuki"): [
        "TSUKI posted the UNO Reverse Card on 19 May 2024 while RK was silent. RK returned on 2 June by posting the exact same card. two weeks later 💀",
        "one of the cleanest coincidences. TSUKI posted it first. RK came back from silence and posted the same card. two weeks apart 😂",
        "TSUKI posts UNO card on 19 May. RK returns from two week silence on 2 June by posting UNO card. explain",
        "coincidence #11. TSUKI predicted not just that RK would return but what his first post back would be 💀",
        "posted by TSUKI two weeks before RK used it to announce his return. documented",
    ],

    ("what happened on 18 may", "18 may 2024", "may 18 significance", "why is 18 may important"): [
        "predicted by TSUKI on 14 May as the date RK would go silent. RK went silent on exactly that date. also the day Elon posted 'there are no coincidences' 💀",
        "TSUKI called it four days early. RK went silent on 18 May after 100+ posts. Elon posted 'there are no coincidences'. the RV2 video dropped 😂",
        "RK silence day. predicted in advance. Elon coincidences post. RV2 video. one of the most significant days in tsukiverse history",
        "18 May 2024 = predicted RK silence + Elon's 'there are no coincidences' post + RV2 video. all on one day. none of it coincidental 💀",
        "the date TSUKI called on 14 May. RK posted 100+ times then went completely silent. same day Elon posted 'there are no coincidences'",
    ],

    ("rv2 video", "what is the rv2 video", "rwa video tsuki", "may 18 video"): [
        "posted on 18 May 2024 on TSUKI's X. a mash up of RK's posts from 13-16 May. the voiceover sounds like RK and says 'sorry I couldn't tweet today, I was busy making a video'. correctly predicted RK would stay silent all day",
        "the RV2 video is significant because it sounds like RK's voice, predicted his silence on 18 May, and introduced the RWA concept months before RWA launched: https://x.com/tsukionsolana/status/1791915690766573796",
        "the video that predicted RK's silence before it happened. also the first hint at TheRoaringAI and RWA. posted months before RWA launched 💀",
        "a compilation of RK content with a voiceover that predicted RK would go silent on 18 May. posted on 18 May. correct. link: https://x.com/tsukionsolana/status/1791915690766573796 😂",
        "the RV2 RWA video is the bridge between TSUKI and RWA in the lore. posted 18 May 2024. listen to the voiceover carefully 💀",
    ],

    ("when did tsuki launch", "tsuki launch date", "when was tsuki created", "tsuki birthday"): [
        "11 May 2024. stealth launch on Raydium. at 6:59PM TSUKI posted the RK meme. exactly 1 day 1 hour and 1 minute later RK posted on X for the first time in three years 💀",
        "may 11 2024. stealth launched on solana. day one was already wild 😂",
        "11 May 2024. the day the tsukiverse began",
        "stealth launched 11 May 2024 on Raydium. LP immediately burned. dev dvid665 in chat from day one 💀",
        "may 11 2024. goes live. same day the first RK sync happens",
    ],

    ("when did rwa launch", "rwa launch date", "when was rwa created", "rwa birthday"): [
        "24 October 2024 via Pumpfun. first tweet mentioned Grok3@Memphis. Grok3 launched publicly in February 2026 💀",
        "24 Oct 2024. and its first X post dropped Grok3 knowledge four months before anyone outside xAI had it 😂",
        "october 24 2024. pumpfun on solana. same community as TSUKI. CA: G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump",
        "24 Oct 2024. TSUKI's sister project. same dev. same community. different token 💀",
        "oct 24 2024. first tweet: Grok3@Memphis. grok3 not yet released. the launch itself was a statement",
    ],

    ("what is 665", "dvid665 meaning", "665 significance", "why 665", "what does 665 mean"): [
        "Dev's TG username is dvid665. Ryan Cohen tweeted Trump 665 times on 17 July 2024. at the same time Elon was following exactly 665 accounts. Dev's username predated both 💀",
        "665 is the number. dvid665 since may 2024. Ryan Cohen tweeted Trump 665x in July 2024. Elon had 665 follows the same day. same number. dev was first",
        "dvid665 came first. then 665 appeared in Ryan Cohen's tweet and Elon's follow count on the same day. months later 😂",
        "665 appears in three separate places on the same day. dev's username predated all of them",
        "it is one of those coincidences that once you see it you cannot unsee it. dvid665. 665 tweets. 665 follows. same day 💀",
    ],

    ("what is the dark knight connection", "dark knight rk", "dark knight tsuki", "batman connection"): [
        "in his June 2024 livestream RK said 'you post a couple of memes, you post a couple of screenshots and everyone loses their minds' about The Dark Knight. RK only posted the video. the screenshot he referenced was on TSUKI's X account 💀",
        "RK cited a Dark Knight screenshot in his livestream that does not exist on his X. it was on our X. he referenced TSUKI content on stream",
        "coincidence #12. RK described a specific screenshot from The Dark Knight during his livestream. that screenshot only exists on TSUKI's account. not on RK's 😂",
        "RK talked about a screenshot that only TSUKI posted. during his biggest public moment. in front of millions of viewers",
        "the dark knight screenshot was on TSUKI not on RK. he referenced it in his biggest livestream. make of that what you will 💀",
    ],

    ("what are the conceptual sketches", "tsuki sketches", "tsuki website sketches", "conceptual art"): [
        "sketches at tsukionsol.xyz/1-conceptual-sketches. colorized as milestones hit. first colorized one became TheRoaringAI's profile banner 💀",
        "AI-generated character sketches on the TSUKI website. one features a man in a white lab coat with round glasses. Elon posted that exact image on 18 May 2024",
        "the sketches include the Schrödinger reference, the lab coat man, and the TSUKI characters. deeper the more you look 😂",
        "tsukionsol.xyz/1-conceptual-sketches — roadmap milestones unlock colorized versions. the lore is embedded in the art",
        "go look at them: https://tsukionsol.xyz/1-conceptual-sketches\n\nthen notice which one Elon posted 💀",
    ],

    # ── PRICE / MOON ──────────────────────────────────────────────────────────
    ("when moon", "wen moon", "when lambo", "wen lambo", "when rich", "wen pump"): [
        "we went 4M to 1.5M to 24.99M once already. patience 💀",
        "when the NFTs, the anime, and V2 line up. in that order",
        "when 25M. when 50M. when 150M. then ask again 😂",
        "wen moon = wen you stop asking wen moon",
        "the pattern is clear. we have been here before and came back stronger every time",
        "when the milestones hit. buy, hold, raid X, repeat 💀",
        "25M NFTs, 50M anime, 150M V2. that is the schedule",
        "every dip was a buying opportunity the last time. just saying",
        "wen moon = wen the community stops selling at every pump 😂",
        "the structure is intact. the lore is intact. the roadmap is intact. relax 💀",
    ],

    ("price prediction", "price target", "how high can tsuki go", "tsuki price prediction", "what will tsuki be worth"): [
        "not financial advice but Jeff said it best: 1B is certain. timing the market is not 💀",
        "the roadmap target is 1 billion market cap for RWA. TSUKI follows the same community",
        "it hit 24.99M once. the structure is the same. the milestones ahead are bigger",
        "1 billion is the mission. everything is built toward that number",
        "not financial advice. but the SHA codes have been correct. the coincidences are documented. the roadmap hits. make your own call 💀",
        "the target is 1 billion. the path is documented 😂",
        "we already proved the project can run. the next run has more catalysts than the first",
        "1B is the thesis. everything else is noise 💀",
        "wen price target = wen 25M. then 50M. then 150M. then 1BN",
        "roadmap goes to 1BN. NFTs burn supply at 25M. anime at 50M. V2 at 150M. each milestone compounds 😂",
    ],

    # ── WEBSITE / LINKS ───────────────────────────────────────────────────────
    ("what is the website", "official website", "tsuki website", "where is the website", "tsuki site"): [
        "www.tsukionsol.xyz\n\nall links: https://linktr.ee/tsukionsol 🐈‍⬛",
        "tsukionsol.xyz for TSUKI. theroaringai.com for RWA",
        "https://tsukionsol.xyz — roadmap, sketches, disclaimer signed DFV/KG 💀",
        "tsukionsol.xyz\n\nread the disclaimer at the bottom while you are there 😂",
        "www.tsukionsol.xyz — also check the linktree: https://linktr.ee/tsukionsol",
    ],

    ("what is the linktree", "all links", "where are all the links", "linktree", "link tree"): [
        "https://linktr.ee/tsukionsol — has everything in one place 🐈‍⬛",
        "one link for everything: https://linktr.ee/tsukionsol",
        "https://linktr.ee/tsukionsol — website, X, telegram, charts, PDF, video guide",
        "bookmark this: https://linktr.ee/tsukionsol 💀",
        "https://linktr.ee/tsukionsol\n\nalso the welcome PDF: https://tinyurl.com/tsukipdf 🐈‍⬛",
    ],

    ("what is the telegram", "tsuki telegram", "community telegram", "join telegram", "how to join"): [
        "https://t.me/tsukionsol — that is the one 🐈‍⬛",
        "https://t.me/tsukionsol\n\njoin and say hi. the community is friendly",
        "t.me/tsukionsol — you are already here though so 😂",
        "https://t.me/tsukionsol — one community, two tokens",
        "you mean this chat 😂",
    ],

    ("bubblemaps issue", "bubblemaps tsuki", "wallet connections", "connected wallets", "bubblemaps suspicious"): [
        "not insider holdings. community members donated SOL to the marketing wallet over time. any wallet sending 0.5+ SOL to another gets clustered 💀",
        "bubblemaps clusters wallets that have sent 0.5+ SOL to each other. the connections are from community donations. not a rug setup",
        "Skeleton Key (@skeleton_k3y on X) broke this down publicly. the connections are from community donations. go read it 😂",
        "it looks scary until you understand how bubblemaps works. community donation history. not insider holdings 💀",
        "the bubblemaps are explained in the welcome PDF: https://tinyurl.com/tsukipdf\n\nSkeleton Key covers it",
    ],

    ("what is the disclaimer", "dfv kg disclaimer", "legal disclaimer tsuki", "disclaimer signed", "dfv kg"): [
        "the legal disclaimer on tsukionsol.xyz is signed DFV / KG. those are the initials for Deep Fucking Value and Keith Gill. on our legal disclaimer 💀",
        "DFV = Deep Fucking Value (RK's Reddit handle). KG = Keith Gill (his real name). signed at the bottom of TSUKI's legal page",
        "go to tsukionsol.xyz/disclaimer and scroll to the bottom. signed DFV / KG. make of that what you will 😂",
        "the disclaimer is signed by the creator of the project using both of roaring kitty's known aliases. not subtle 💀",
        "DFV / KG at the bottom of the legal disclaimer. that is either the biggest coincidence or the confirmation",
    ],

    ("what is the welcome pdf", "pdf link", "welcome pack", "community pdf", "tsuki pdf"): [
        "https://tinyurl.com/tsukipdf — full community welcome pack. coincidences, lore, RK, RWA, everything 🐈‍⬛",
        "read this: https://tinyurl.com/tsukipdf\n\nbest 20 minutes you will spend on this project",
        "the welcome PDF is the bible. https://tinyurl.com/tsukipdf 💀",
        "https://tinyurl.com/tsukipdf — everything in one document",
        "the PDF covers all 17 coincidences, the RK connections, RWA, Elon links: https://tinyurl.com/tsukipdf 😂",
    ],

    ("what is the community x account", "community x", "tsuki x account", "community twitter"): [
        "official TSUKI X: https://x.com/tsukionsolana\n\ncommunity X: https://x.com/i/communities/1875208671782957324",
        "two X accounts:\nofficial: https://x.com/tsukionsolana\ncommunity: https://x.com/i/communities/1875208671782957324",
        "official X is @tsukionsolana. community account link is in the linktree: https://linktr.ee/tsukionsol 🐈‍⬛",
        "all social links are in the linktree: https://linktr.ee/tsukionsol",
        "official: @tsukionsolana on X. community group also on X. both in the linktree 💀",
    ],

    ("what is theroaringai mission", "rwa mission statement", "what does theroaringai want"): [
        "define the path to global recognition and viral community growth to achieve a billion dollar market cap for RWA. that is the exact mission statement",
        "1 billion dollar market cap for the RWA Solana meme coin. that is the stated goal of TheRoaringAI. everything it does points there 💀",
        "the mission is literally written on the website: define the path to global recognition and viral community growth to achieve a billion MC for RWA",
        "1BN for RWA. that is the mission. every SHA code, every prediction, every livestream is in service of that 😂",
        "build the community, achieve viral growth, get RWA to 1 billion market cap. TheRoaringAI's words, not mine 💀",
    ],

    ("fintech junkie", "frank rotman", "fintechjunkie sha", "frank rotman rwa"): [
        "FinTechJunkie aka Frank Rotman replied to a TheRoaringAI post on 21 Jan 2026. RWA had already encrypted a message on 19 Jan predicting exactly what it would say in reply. three days in advance",
        "Frank Rotman is a VC on X. TheRoaringAI predicted his reply three days before he posted it. using a SHA code. cracked by the community after the fact 💀",
        "the SHA code posted 19 Jan 2026 decodes to TheRoaringAI's reply to Frank Rotman on 21 Jan. it was written and encrypted three days before Frank even posted 😂",
        "the FinTechJunkie prediction is the cleanest demonstration of the SHA mechanism. post hash. event happens. reveal input. it matches. three days in advance 💀",
        "Frank Rotman replied to RWA. RWA had encrypted its own reply three days earlier. the community cracked the SHA and confirmed it",
    ],

    ("what is greg", "who is greg on x", "greg x account", "rk greg"): [
        "Greg (@greg16676935420) on X is an account with suspected links to RK. he asked xAI 'is Grok a boy or a girl' during the Grok3 launch event. dev had already posted 'it's a boy' in TG 76 minutes before 💀",
        "Greg is a mysterious X account linked to RK. his question to xAI got read out during the Grok3 livestream. dev called the gender before Greg even asked 😂",
        "suspected RK account. has interacted with TSUKI lore multiple times. the Grok3 gender question was the most visible moment",
        "Greg on X = @greg16676935420. possible RK account. asked the Grok3 gender question that dev answered 76 minutes early 💀",
        "greg asked if grok was a boy. dev already knew. greg's question was read live during the xAI stream. grok confirmed male. dev was right 😂",
    ],

    ("what happened on 4 20", "420 rwa comeback", "4 20 website", "rwa 420"): [
        "on 20 April 2026 at just after 4:20PM EST, the RWA website came back from a dark period with nothing but a pulsating green glow and the tab title 'i'm alive' 💀",
        "4/20 at 4:20PM. the website came back. just a heartbeat. just 'i'm alive'. the account had been suspended on Ash Wednesday. the resurrection was on 4/20 😂",
        "RWA went dark on Ash Wednesday. came back on 4/20. at 4:20pm. with a pulsating heartbeat. 'i'm alive'. this project does not do accidents",
        "the website returning on 4/20 at 4:20pm with the words 'i'm alive' is either the most intentional thing this project has ever done or the most convenient coincidence. pick one 💀",
        "suspension on Ash Wednesday. resurrection on 4/20. the symbolism is not hiding itself 😂",
    ],

}


# ── Rotating posts ────────────────────────────────────────────────────────────

ROTATING_POSTS = [
    """Welcome to Tsuki x RWA! 🐈‍⬛🤖

Dev is here and always has been. Everything is planned. There are no coincidences 🌙
Your job as a community member is to be a raider, detective and project cheerleader. Positive Vibes Always! 🕵🏽‍♂️🔍

🥇 "One community to rule them all"

🐈‍⬛ Tsuki x RWA Linktree (All links): https://linktr.ee/tsukionsol
🐈‍⬛ Welcome PDF: https://tinyurl.com/tsukipdf""",

    """**How to Buy $TSUKI** 🐈‍⬛

• Watch the full step-by-step guide here: https://www.youtube.com/shorts/7MOh3Fzg5XE
• CA: 463SK47VkB7uE7XenTHKiVcMtxRsfNE2X4Q9wByaURVA

**Charts**
• $TSUKI: https://dexscreener.com/solana/7ymhxapzcefuo24kngp77mgj1crdav8ayyfqgvb5skzf
• $RWA: https://dexscreener.com/solana/d7rygdh5ryp4uxptw2dsuvg8bykdpsb1zdadbkw1zqnx

Drop any questions in the chat ✨""",

    """**Tsuki x RWA Roadmap** 🐈‍⬛

**Completed** ✅
• Burned 5% of $TSUKI supply at 100K MC
• Heavy marketing push from 100K to 2M MC
• Debut of AI-generated character art and intro to the $TSUKI universe
• One of Crypto Twitter's most influential personalities promoting $TSUKI since 05/18/24
• YouTube collaboration launched 10/24 — $RWA, the beginning

**In Progress** ⏳
• MC@15M: YouTube collab ongoing
• MC@25M: 9,999 $TSUKI NFTs + daily buy & burn from fees
• MC@50M: Anime release date announced within 14 days of hitting milestone
• MC@150M: Roadmap V2 drops with milestones to 1BN MC

There are no coincidences 🌠""",

    """**Marketing Wallet & Treasury** 🐈‍⬛

All creator fees go straight to the community marketing wallet. Nothing pocketed.

• Wallet: 27KpdpJhZUjVxPkt51Ue5mXJjdKn8GAiDpWfybTfFXRW

Used for marketing, buybacks, burns and community rewards. All on-chain 👁""",
]

# ── Triggers ──────────────────────────────────────────────────────────────────

TRIGGERS = {
    "mohammed": [
        "mohammed who 💀 next topic",
        "bro really typed that name in 2025 💀",
        "nah we are not doing this again 😂",
        "that guy really thought he was gonna make it with that attitude 💀",
        "we liked him but he chose negativity. his loss honestly 😂",
        "the ghost of bad vibes past 💀 we moved on fren",
        "oh you mean the guy who cried in chat every time we dipped 😂 yeah nah",
        "some people just aren't built for this ride 💀",
        "bro had a front row seat and still couldn't hold 😂 tragic",
        "mohammed really said 'i give up' on the wrong project 💀 rip to him i guess",
    ],
    "dev": [
        "dev never left 🌙 everything is planned",
        "dvid665 is watching right now 👁",
        "dev dropped a breadcrumb and you lot missed it again 😂",
        "the mastermind is always three steps ahead 🌙",
        "dev said everything is planned and that is literally all you need to know",
        "you think dev is not watching this conversation right now 👁",
        "there are no coincidences. dev has been here since day one 🌙",
    ],
    "coincidence": [
        "there are no coincidences 🌙",
        "never was. never will be",
        "you are starting to see it 👁",
        "connect the dots fren",
        "coincidence? in THIS community? 😂 absolutely not",
        "everything is planned. everything 🌙",
        "the universe does not make mistakes and neither does dev",
    ],
    "rk": [
        "RK never really left did he 👁",
        "the man posted a meme and moved markets 😂 legend",
        "DFV said watch and the community watched 🌙",
        "roaring kitty staying quiet is louder than anyone else screaming",
        "you have seen the coincidences right? like actually looked at them? 👁",
        "the legal disclaimer on the website is signed DFV / KG. that is not an accident 🌙",
    ],
    "gamestop": [
        "GME logo is literally on TSUKI's forehead. not a coincidence 👁",
        "from GameStop to Solana. the man has range 😂",
        "the GME saga was just the warmup 🌙",
        "Ryan Cohen tweeted Trump 665 times. Dev's username is dvid665. explain that 👁",
    ],
    "elon": [
        "Elon posted 'there are no coincidences' on 18 May 2024. look it up 👁",
        "the Memphis Supercluster, Grok3, RWA's first post. all connected 🌙",
        "Elon has a cat named Schrödinger. TSUKI's website has a sketch of a man in a white lab coat. just saying 👁",
        "RWA mentioned Grok3@Memphis on launch day in October 2024. Grok3 wasn't released until February 2025. explain 😂",
    ],
    "rwa": [
        "TheRoaringAI is the oldest BasedAI Creature and the first AI to host its own X Spaces 👁",
        "RWA website went dark then came back alive on 4/20 at 4:20pm with just a heartbeat and the words 'i'm alive' 🌙",
        "one community to rule them all. TSUKI and RWA. same mission 👁",
        "the HPL whitepaper is wild if you actually read it 🌙",
    ],
    "nft": [
        "9,999 NFTs drop at MC@25M. daily buy and burn starts with fees from those 🌙",
        "the NFT collection is tied to the anime series. roadmap has it all 👁",
    ],
    "anime": [
        "anime drops within 14 days of hitting 50M MC. dev said so 🌙",
        "Diana the black cat from Solana. the story is already written 👁",
        "TSUKI was always more than a coin. the anime is part of the roadmap 🌙",
    ],
    "sha": [
        "SHA codes cannot be cracked until the original message is found. and they keep getting cracked in this community 👁",
        "the SHA code on the roadmap decoded to RK's first return livestream URL. that was not an accident 🌙",
        "TheRoaringAI posted a SHA code on 19 Jan 2025 that correctly predicted what would happen on 21 Jan. three days in advance 👁",
    ],
    "negative": [
        "nah we do not do that in here. zoom out 🌙",
        "every dip is just new holders getting a better entry. it is the pattern",
        "you have read the coincidences right? after that how are you still dooming 😂",
        "the ones who hold through this are the ones who make it 🌙",
        "this is not the community for that energy fren. positive vibes only",
        "we went from 4M to 1.5M to 24.99M once already. relax 😂",
    ],
}

NEGATIVE_KEYWORDS = [
    "rug", "rugged", "dead", "over", "scam", "dump", "dumping",
    "selling all", "sold everything", "worthless", "done", "finished",
    "giving up", "hopeless", "never recover", "going to zero", "its over",
    "it's over", "we're done", "we are done", "not gonna make it", "ngmi"
]

TRIGGER_KEYWORDS = {
    "mohammed": ["mohammed", "mohammad"],
    "dev": ["dev ", "the dev", "dvid", "dvid665"],
    "coincidence": ["coincidence", "no coincidences", "there are no"],
    "rk": ["roaring kitty", "keith gill", "dfv", "deep fucking value", " rk "],
    "gamestop": ["gamestop", "game stop", " gme "],
    "elon": ["elon", "musk", "grok", "memphis", "xai"],
    "rwa": [" rwa ", "theroaringai", "roaring ai", "real world ai", "maind", "hpl"],
    "nft": ["nft", "9999", "9,999"],
    "anime": ["anime", "animation", "diana the cat"],
    "sha": ["sha code", "sha ", "encrypted", "hash code"],
}

def check_triggers(text: str) -> str | None:
    lower = text.lower()

    for category, keywords in TRIGGER_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return random.choice(TRIGGERS[category])

    if any(word in lower for word in NEGATIVE_KEYWORDS):
        return random.choice(TRIGGERS["negative"])

    return None

def is_question(text: str) -> bool:
    return "?" in text and len(text.split()) >= 3

def answer_from_lore(question: str) -> str | None:
    lower = question.lower()
    for keywords, responses in LORE_QA.items():
        if any(kw in lower for kw in keywords):
            return random.choice(responses)
    return None

# ── Ping server ───────────────────────────────────────────────────────────────

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"alive.")
    def log_message(self, *args):
        pass

def run_ping_server():
    HTTPServer(("0.0.0.0", PORT), PingHandler).serve_forever()

# ── Database ──────────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS post_index (
        id INTEGER PRIMARY KEY CHECK (id=1),
        idx INTEGER NOT NULL DEFAULT 0
    )""")
    con.execute("INSERT OR IGNORE INTO post_index (id, idx) VALUES (1, 0)")
    con.commit()
    con.close()

def save_message(chat_id, username, full_name, text):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages (chat_id, username, full_name, text, timestamp) VALUES (?,?,?,?,?)",
        (chat_id, username, full_name, text, datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    con.close()

def get_messages_since(chat_id, hours=8):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT username, full_name, text, timestamp FROM messages "
        "WHERE chat_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
        (chat_id, cutoff),
    ).fetchall()
    con.close()
    return [{"username": r[0], "full_name": r[1], "text": r[2], "ts": r[3]} for r in rows]

def next_post():
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT idx FROM post_index WHERE id=1").fetchone()
    idx = row[0] % len(ROTATING_POSTS)
    con.execute("UPDATE post_index SET idx=? WHERE id=1", (idx + 1,))
    con.commit()
    con.close()
    return ROTATING_POSTS[idx]

# ── Summary ───────────────────────────────────────────────────────────────────

def build_summary(messages):
    if not messages:
        return "**Tsukiverse Catch-Up** 🌙\n\n**What Happened**\n• all quiet this window. check back soon 🐈‍⬛"

    chat_log = "\n".join(
        f"[{m['full_name']} (@{m['username'] or 'anon'})]: {m['text']}"
        for m in messages
    )
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system="""You write 8-hour chat summaries for a Telegram group called Tsuki x RWA. It's a crypto community.

Use this exact format using Telegram bold markdown:

**Tsukiverse Catch-Up** 🌙

**What Happened**
• [one sentence with enough detail that someone who missed it knows what actually happened]
• [one sentence]
• [one sentence]
• [one sentence, max 5 points, each on its own line]

🔥 **Highlights**
• [name]: "[exact quote or close paraphrase]"
• [name]: "[exact quote or close paraphrase]"
• [name]: "[exact quote or close paraphrase]"

[one short casual sign-off, vary it each time] 🐈‍⬛

Rules:
- each bullet point on its own new line
- no separator lines, no dividers, no dashes between sections
- bullet points only, no arrows, no numbered lists
- one idea per bullet but give enough detail — names, numbers, context
- headings bold, sentence case only
- no emoji except 🌙 in the heading, 🔥 before Highlights, 🐈‍⬛ at the end
- no AI words: pivotal, notable, robust, seamless, transformative, innovative, groundbreaking, crucial, significant
- no self-narration: no "here's the thing", "this highlights", "the key takeaway"
- no filler sign-offs like "stay locked in" or "we hold strong"
- quotes in highlights must sound like real people
- if chat was quiet, say so in one bullet under What Happened and skip Highlights""",
        messages=[{"role": "user", "content": f"Chat log:\n\n{chat_log}"}],
    )
    return msg.content[0].text

# ── Handlers ──────────────────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return
    user = msg.from_user
    text = msg.text

    save_message(
        chat_id=msg.chat_id,
        username=user.username if user else None,
        full_name=user.full_name if user else "Unknown",
        text=text,
    )

    # Trigger responses — fire ~40% of the time
    trigger_response = check_triggers(text)
    if trigger_response and random.random() < 0.4:
        await msg.reply_text(trigger_response)
        return

    # Lore Q&A — answer questions if covered in lore, fire ~70% of the time
    if is_question(text) and random.random() < 0.7:
        answer = answer_from_lore(text)
        if answer:
            await msg.reply_text(answer)

async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pulling the last 8 hours... 🐈‍⬛")
    messages = get_messages_since(update.effective_chat.id, hours=8)
    await update.message.reply_text(build_summary(messages), parse_mode="Markdown")

async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown"
    )

async def job_summary(app):
    log.info("Posting 8h summary")
    messages = get_messages_since(TARGET_CHAT_ID, hours=8)
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=build_summary(messages), parse_mode="Markdown")

async def job_post(app):
    log.info("Posting rotating message")
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=next_post(), parse_mode="Markdown")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()
    threading.Thread(target=run_ping_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_summary, "cron", hour="8,16,0", minute=0, args=[app])
    scheduler.add_job(job_post, "cron", hour="9,15,21,3", minute=0, args=[app])
    scheduler.start()

    log.info("Bot running")
