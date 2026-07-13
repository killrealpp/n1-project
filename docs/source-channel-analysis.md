# Source Channel Analysis: @num1_ch

Checked on 2026-07-03 via the public Telegram preview: https://t.me/s/num1_ch

## Channel Shape

`@num1_ch` is a high-frequency English market/news feed. Posts are usually very short: one sentence, two lines, or a compact bullet/list item. The channel description is "Independent uncensored news 24/7".

Observed topics:

- market indices and flows;
- crypto, especially BTC and public-company bitcoin treasury data;
- Russian market and policy signals;
- oil, gas, gasoline, energy, and electric vehicles;
- China retail and NEV data;
- currencies and analyst forecasts;
- company, bank, exchange, and ministry announcements.

Observed source attributions include IF, LSEG, CryptoQuant, BBG, RTRS, TASS, AUTOSTAT, CPCA, Bitwise, BofA, and Ministry of Finance references.

## Short Post Instruction

The short-post pipeline must translate source items strictly. It should not rewrite, decorate, summarize, or compress them as social media copy.

Rules:

- Preserve the source line count and paragraph structure.
- Preserve numbers, dates, tickers, links, emojis, hashtags, source names, and attribution markers.
- Preserve leading emojis or flags at the start of the translated message.
- Translate source names only when there is a common Russian equivalent; otherwise keep them as source codes.
- Avoid commentary unless the source already contains it.
- Do not add analysis, forecasts, or explanations to a single short post.
- Do not add emojis, hashtags, links, numbers, source names, or attribution markers that are absent from the source.

For a one-line source, the output must remain one line. For a multi-line source, keep the same number of non-empty lines.

## Development Fetching

The project supports `--fetch-public-preview` to read the public preview at `https://t.me/s/num1_ch` before the dedicated MTProto session is ready. This is useful for local testing and source-style inspection. Production reading should still use MTProto because the public preview is not a stable API.

## Dzen Article Instruction

Dzen/channel articles should be themed digests, not expanded versions of one post.

Current cadence:

- three articles per day in the multi-channel setup: one for `russia`, one for `energy`, and one for `tech`;
- each channel uses one daily window with a stable random minute inside that window;
- use the 06:00-22:00 Moscow window and avoid 22:00-06:00 for scheduled publishing;
- if too few matching unused posts are available for a channel, skip automatically unless the run uses `--force-article`.

Article structure:

1. First sentence: factual title under 140 characters.
2. Opening: what the market/news flow shows today.
3. Body: group posts into themes such as markets, macro, Russia, China, energy, crypto, companies, currencies.
4. Closing: careful synthesis of what to watch next.

The article must not invent connections. It may say "signals are mixed" or "several items point to..." only when the grouped posts support that reading.

Title and card rules:

- Use a concrete title with real assets, companies, countries, sources, numbers, or consequences when the source posts support them.
- Treat the first paragraph as the generated Dzen card description.
- Avoid hidden-subject intrigue, fake quotes, exaggerated drama, invented conflict, and shock wording.
- Every hook in the title must be answered in the body.
- If posts do not connect clearly, present them as separate signals instead of forcing causality.
