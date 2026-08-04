# Reddit Publishing

Reddit is a planned optional publishing stream for short profile posts, not a replacement for Telegram, VK, MAX, or Dzen. The first version should publish from the user's own profile, use a light human voice, and skip weak slots instead of filling a quota.

## Current Decisions

- Publish from the user's own Reddit profile first.
- Do not post into third-party subreddits by default.
- Keep Reddit outside the main `PUBLISH_ORDER`; Reddit failures must not block VK, MAX, or Telegram.
- Start with 6 possible daily windows: 09:10-10:20, 11:30-12:50, 14:00-15:20, 16:30-17:50, 19:00-20:20, 21:30-22:50 Moscow time.
- Pick the exact minute inside each window with stable daily jitter, so timing changes from day to day but survives worker restarts.
- Treat windows as opportunities, not obligations.
- Hard cap: 12 Reddit posts per day.
- Use controlled hashtags: `#markets`, `#russia`, `#energy`, `#crypto`, `#ai`, `#chips`, `#geopolitics`, `#rates`, `#oil`, `#bitcoin`.
- Skip `#ai` and `#chips` slots when there is no strong source material.

## Style

Reddit posts should be lighter than Dzen articles and less formal than Telegram translations.

Good shape:

- short specific title;
- 3-6 simple sentences;
- one clear market angle;
- optional direct question only when natural;
- 2-4 hashtags at the end.

Avoid:

- heavy analytical paragraphs;
- filler;
- bureaucratic wording;
- clickbait;
- promo footers;
- plain Telegram translation with tags pasted underneath.

## Future Files

- `src/n1_project/reddit/policy.py` stores initial cadence and hashtag policy.
- `src/n1_project/reddit/selector.py` should choose strong source rows by topic.
- `src/n1_project/reddit/drafts.py` should store draft records and idempotency keys.
- `src/n1_project/reddit/validator.py` should enforce style and factual safety.
- `src/n1_project/reddit/scheduler.py` should decide due windows, jittered minutes, and topic caps.
- `src/n1_project/publishers/reddit.py` should handle OAuth posting later.

## Open Questions

- Should the first working version publish automatically, or send Reddit drafts to the admin Telegram chat for approval?
- Should Reddit posts be Russian-only, English-only, or mixed by topic?
- Should the profile eventually be supported by an owned subreddit?

## Related

- [[prompts/reddit-post-prompt]]
- [[raw/2026-07-28-reddit-research]]
- [[wiki/platform-status]]
- [[wiki/source-channel-style]]

## Sources

- https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam
- https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- https://support.reddithelp.com/hc/en-us/articles/45376380316052-Apps-on-Reddit-and-how-to-get-a-label-for-your-app
