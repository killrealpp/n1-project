# Dzen Article Playbook

A Dzen article for this project should be a concise Russian editorial digest built from the day's translated Telegram posts.

## Target Format

- Total length: 1600-2800 characters.
- First sentence: title, under 140 characters.
- Transport: Telegram message sent to Dzen bridge chat.
- Structure: title sentence, opening paragraph, 2-4 compact blocks, closing synthesis.
- The first 1-2 paragraphs must clearly describe the subject because Dzen generates the card description from early text.
- Direct Dzen articles can be much longer, but bridge articles stay under Telegram transport limits.
- Current default cadence: three channel articles per day: one for `russia`, one for `energy`, and one for `tech`.
- Preferred posting windows are configured per channel. The worker chooses a stable random minute inside each window for the current date.

## Writing Pattern

The title should create honest curiosity from the real source facts. It should be strong enough to open through a real tension, consequence, unusual combination, exact figure, or sharp market question from the source posts. The opening should immediately tell the reader what happened, why it matters, and why the article is worth finishing. Do not force a standalone date line such as `Сводка за 6 июля 2026 года:`; the date can appear naturally only when useful. Each body block should explain one idea from the source posts. The conclusion should state what matters now and what investors will watch next.

For `@num1_ch`, a useful article is normally a themed market digest from several posts, not an expanded version of one short signal. The automation uses `DZEN_ARTICLE_CANDIDATE_LIMIT=30` by default in the multi-channel setup, stores persistent queue `topic` values, filters candidates by channel topic, and the draft should usually use the best related subset from those candidates instead of mentioning every candidate.

The channel lanes are:

- `russia`: Russian market, ruble, CBR, IPO, bonds, equities, banks, companies, dividends, jobs, mortgage, and economy-for-people signals.
- `energy`: oil, gas, LNG, fuel, metals, commodities, Hormuz, Iran, sanctions, and geopolitical risks when they affect energy or prices.
- `tech`: crypto, BTC, ETH, DeFi, stablecoins, AI, chips, semiconductors, tech companies, and global tech-market signals.

After an article is published or stored for review, the linked candidate posts are marked with `article_id`, so they are not reused in later articles.

Current production mode is direct bridge publishing with `DZEN_ARTICLE_REVIEW_ENABLED=false`. Set it to `true` only when the Telegram button review gate should be restored.

Energy and Tech can publish through their own Telegram bots via `DZEN_ENERGY_TELEGRAM_BOT_TOKEN` and `DZEN_TECH_TELEGRAM_BOT_TOKEN`; Russia falls back to the main `TELEGRAM_BOT_TOKEN`.

The cross-platform footer should appear in each daily channel article by default. Since each channel now publishes one article per day, links stay visible without repeating three times per channel. Footer wording rotates by slot key and should use direct URLs for Telegram, VK, and MAX.

## Daily Workflow

1. Collect the latest translated source posts that have not yet been considered for an article.
2. Treat those posts as candidates, not a mandatory checklist.
3. Pick one main semantic cluster or two related themes. Good groupings are markets, macro, Russia, China, energy, crypto, companies, banks, currencies, and sanctions/regulation.
4. Exclude weak or isolated posts if they would force an artificial connection.
5. Choose the title only after the theme is clear. The title must sell the real article, not a more dramatic version of it.
6. Draft the opening as the card description: what happened, who/what is affected, and why the reader should continue.
7. Build 3-5 short blocks from source-grounded facts.
8. Finish with a cautious synthesis: what changed today or what is worth watching next.
9. Use short `<b>...</b>` HTML accents for section headings or key takeaways when they make the text easier to scan. Do not bold the first title sentence or whole long paragraphs.
10. Run the quality gate before publishing.

## Title And Card Pattern

The title and first paragraph are the traffic gate. Make the card concrete before making the article long.

Useful title shapes for this project:

- concrete actor + consequence;
- list of concrete market items + unifying point;
- event/fact + restrained consequence: what changed, why it matters, what to watch;
- exact numbers/names/tickers from the source when they are available.

Do not start titles with `Почему`, `Что произошло`, `Что теперь будет`, or `Что означает`. The headline should name a company, country, asset, market, or event from the source posts, not hide the subject behind a repeated question template.

Adapted lessons from Dzen headline practice:

- concrete details beat abstract wording;
- exact numbers, names, tickers, amounts, dates, and source attributions increase trust when they are real;
- a fact-plus-question title can work when the question is answered in the body;
- a list title can work when the list items are visible in the article;
- restrained negative framing is allowed only when the source fact is genuinely negative and the article explains it calmly.

Avoid generic titles such as `Main market news of the day`. Avoid hidden-subject intrigue, fake quotes, exaggerated drama, invented conflict, unsupported negative framing, and shock wording. If a hook appears in the title, the article body must pay it off directly.

The first paragraph should work as Dzen's generated card description: explain what happened, why it matters, and why the reader should continue.

Examples of acceptable project title shapes:

- `Oil, currencies, and banks: what shaped the market news flow today`
- `Qatar, LNG, and Hormuz: why energy signals stayed in focus`
- `Russian banks and payment infrastructure: what changed in today's signals`

These are shapes, not fixed templates. Replace generic nouns with the day's actual facts whenever possible.

## Article Structure

A strong bridge article should not look like a pasted list of Telegram posts. It should read as a short editorial digest:

- title sentence;
- opening paragraph that frames the whole digest;
- 3-5 compact blocks, each built around one theme;
- closing synthesis.

Each body block should follow this logic:

- name the concrete signal;
- preserve the source fact, number, source attribution, company, country, ticker, link, or date;
- explain the limited meaning of that signal;
- connect it to the day's theme only if the connection is supported.

If several source posts do not clearly connect, present them as separate market signals. Do not force causality just to make the article feel more dramatic.

## AI Drafting Pattern

Use the LLM to draft and organize, but keep editorial control over idea grouping, title choice, and fact checks.

Before publishing, remove common AI traces: vague summaries, inflated significance, awkward metaphors, repetitive transitions, unsupported context, and punctuation that looks unnatural in Russian. Check that every number, source attribution, ticker, date, and claim came from the source posts.

Typical edits after an LLM draft:

- replace generic openings with the day's actual topic;
- remove phrases like `it is important to note`, `in the context of current uncertainty`, and similar filler;
- cut unsupported explanations of causes;
- split overloaded paragraphs;
- make the title more concrete;
- remove any fact that cannot be traced to the source posts;
- smooth Russian punctuation and rhythm.

Human readability rules:

- write like an experienced financial journalist explaining the topic to a friend, not like Bloomberg, Reuters, РБК, or an official analytical report;
- avoid bureaucratic phrases such as `формируется противоречивая картина`, `усилилась геополитическая составляющая`, `фундаментальные факторы`, `по итогам дня`, `в краткосрочной перспективе`, `при этом следует отметить`, and `одновременно наблюдается`;
- use dependency-grammar-friendly structure: words that depend on each other should stay close;
- keep subject, verb, and object close when Russian syntax allows it;
- put the main fact early in the sentence;
- move caveats and background after the fact;
- use active, direct Russian phrasing;
- keep one paragraph to one idea;
- split sentences that carry two separate ideas;
- remove robotic transitions unless they are truly needed.
- keep most sentences around 10-18 words;
- explain complex terms such as EIA, SPR, Brent, and FOMC in plain Russian when they appear in sources.

## Quality Gate

Publish only when all checks pass:

- the title is under 140 characters and contains no link;
- the title creates honest curiosity and names enough of the real subject to avoid hidden-subject intrigue;
- every title hook is answered in the article body;
- the first paragraph explains what happened, why it matters, and why the reader should continue;
- the first paragraph can stand alone as a Dzen card description;
- the article uses several source posts or honestly stays short when material is thin;
- all numbers, dates, names, tickers, sources, and links are preserved accurately;
- the text does not give investment advice;
- the text does not invent causes, predictions, quotes, or statistics;
- the tone is natural Russian financial journalism, not promotional, robotic, bureaucratic, or sensational;
- the full bridge message stays below Telegram's 4096-character transport limit.

## Voice

Use natural Russian. Make it readable, not ornamental. Preserve facts, names, links, dates, numbers, tickers, and source meaning. Avoid invented context and vague filler.

## Avoid

- clickbait;
- exaggerated drama;
- hidden-subject intrigue;
- unsupported predictions;
- excessive caps, repeated punctuation, links, or code-like symbols in the title;
- copied source wording without original synthesis;
- medical, financial, legal, or political claims beyond the source material;
- manipulative calls to action.

## Platform Notes

- Dzen uses the first sentence of the Telegram bridge post as the title.
- Dzen title maximum is 140 characters and direct article titles cannot contain links.
- Telegram formatting is not transferred through the bridge.
- Dzen can limit recommendations for clickbait, non-original content, spam, or rule violations.
- Recommendation reach is influenced by audience reaction, topic interest, subscribers, views, likes, and reading behavior.
- Official Dzen rules treat manipulative cards as clickbait and can limit such materials to subscribers. Duplicated or borrowed content can also be limited, so daily articles must be original syntheses of our own source posts.

## Related

- [[prompts/dzen-article-prompt]]
- [[prompts/humanize-russian-prompt]]
- [[raw/2026-07-03-dzen-research]]
- [[raw/2026-07-06-dmitriev-dzen-method]]
