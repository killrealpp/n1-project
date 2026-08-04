# Reddit Publishing Plan

Reddit is planned as an optional profile-based publishing stream, not as a blocking platform in the main VK/MAX/Telegram chain.

## Positioning

Post from the user's own Reddit profile first. Do not publish into third-party subreddits by default.

The format is not a translated Telegram mirror. Reddit posts should feel like short human market notes:

- one clear angle;
- 3-6 short sentences;
- no formal article voice;
- no forced filler;
- 2-4 hashtags from the controlled list;
- no cross-platform promotional footer by default.

## Cadence

Start with 6 possible windows per day, Moscow time:

- 09:10-10:20
- 11:30-12:50
- 14:00-15:20
- 16:30-17:50
- 19:00-20:20
- 21:30-22:50

These are possible windows, not obligations. If the system does not find a strong post for a window, it skips the window.

The exact minute should be picked inside the window with stable daily jitter. For example, one day the first window can publish at 09:47, another day at 10:06. The selected minute must stay stable after worker restarts on the same day.

After 10-14 days of review, the ceiling can move toward 8-12 posts per day. Extra posts should only come from strong source material, not from filling the calendar.

Hard rule: never publish more than 12 Reddit posts per day.

## Topic Mix

Use topic caps instead of a fixed quota:

- `#markets` / `#russia`: usually 2-3 posts per day.
- `#energy` / `#geopolitics`: 1-2 posts per day when the source has strong material.
- `#crypto`: 1-2 posts per day when there is a concrete market signal.
- `#ai` / `#chips`: 0-2 posts per day; skip when there is no strong signal.

Allowed hashtags:

- `#markets`
- `#russia`
- `#energy`
- `#crypto`
- `#ai`
- `#chips`
- `#geopolitics`
- `#rates`
- `#oil`
- `#bitcoin`

## Quality Gate

Publish only when all of these are true:

- The post can be understood without reading the original Telegram item.
- The title is simple and specific.
- The body has one main thought.
- The post preserves numbers, names, tickers, companies, sources, and dates.
- The text does not invent causality.
- The tags match the topic.
- The post does not sound like an ad, a bot dump, or a newswire headline stack.

Skip when:

- the source item is too small and has no angle;
- the topic already hit its daily cap;
- the text needs a long explanation to make sense;
- the only possible output is a plain translation;
- the model cannot produce a light version without adding facts.

## Example Shape

```text
Title:
Trump-linked American Bitcoin keeps buying BTC

Body:
American Bitcoin, связанная с семьей Трампа, докупила еще 300 BTC.

Теперь у компании больше 8,000 BTC на балансе.

Политика и крипта все сильнее смешиваются. И это уже не мем, а корпоративные резервы.

#crypto #bitcoin #markets
```

## Implementation Structure

Current scaffold:

```text
src/n1_project/reddit/
  __init__.py
  policy.py

obsidian-vault/wiki/reddit-publishing.md
obsidian-vault/prompts/reddit-post-prompt.md
obsidian-vault/raw/2026-07-28-reddit-research.md
```

Future implementation files:

```text
src/n1_project/reddit/selector.py      # choose strong source rows by topic
src/n1_project/reddit/drafts.py        # create draft records and idempotency keys
src/n1_project/reddit/validator.py     # enforce Reddit style and factual safety
src/n1_project/reddit/scheduler.py     # pick due windows, jittered minutes, and topic caps
src/n1_project/publishers/reddit.py    # OAuth submit publisher
tests/test_reddit_selector.py
tests/test_reddit_validator.py
tests/test_reddit_scheduler.py
tests/test_reddit_publisher.py
```

Reddit should use its own queue/status later, separate from `PUBLISH_ORDER`. A Reddit failure must not block VK, MAX, or Telegram publishing.
