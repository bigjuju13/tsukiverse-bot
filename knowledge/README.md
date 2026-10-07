# knowledge/

Everything the bot searches before it answers. Built into `kb_index.db` (next to `tsuki.db`) on boot; rebuilt only when a file here changes.

- `tsukiverse-knowledge-base.md`: the sourced knowledge base (records, reads, rules). Sections on off-limits, to-verify, watched dates and the YouTube index are deliberately skipped.
- `welcome-pack-v5.3.txt`: the welcome pack PDF as text, one chunk per page section.
- `youtube-notes.md`: notes on every @Tsukiverse55 video (BP videos excluded).
- `juju-x-posts.json`: @BigboyJuju's lore posts with safety flags. Posts flagged Q, BP/Kevin, other tokens or politics are skipped.
- `tg-history.jsonl.gz`: the $TSUKI x $RWA Telegram export. One JSON per line: `i` id, `ts` US Eastern, `u` name, `t` text, `re` reply-to id, `fw` forwarded from, `m` media, `rx` reactions; `pin` lines are pins.

Any `.md` you add is read like the knowledge base. This README is ignored.
