# Dzen Article Playbook

Checked on 2026-07-06.

## Sources

- Official Dzen Telegram bot help: https://dzen.ru/help/ru/channel/cross-platform.html
- Official Dzen article help: https://dzen.ru/help/ru/channel/article.html
- Official Dzen post help: https://dzen.ru/help/ru/channel/post.html
- Official Dzen content rules: https://dzen.ru/help/ru/requirements/rules.html
- Official Dzen clickbait rules: https://dzen.ru/help/ru/requirements/clickbait.html
- Official Dzen content display models: https://dzen.ru/help/ru/models.html
- Official Dzen card-preview rules: https://dzen.ru/help/ru/requirements/card-preview.html
- Official Dzen non-original content rules: https://dzen.ru/help/ru/requirements/copypaste.html

## Bridge Constraints

The project publishes Dzen material by sending a Telegram message to the Dzen bridge chat. That makes Telegram the transport limit even though direct Dzen Studio articles can be longer.

- Keep bridge article text around 1600-2800 characters.
- Keep the first sentence under 140 characters because Dzen uses it as the title.
- Do not put links in the first sentence.
- Do not depend only on Telegram formatting; Dzen says Telegram formatting may not be transferred.
- Use blank lines, short paragraphs, and clear section labels. Telegram channel articles may use short `<b>...</b>` HTML accents for readability.
- Text-only Telegram posts are accepted by the bridge as Dzen articles or posts depending on bridge settings.
- The source Telegram channel connected to Dzen must be public, and one Dzen channel can be linked to only one Telegram channel.
- Dzen bridge can work automatically or manually. In automatic mode, Telegram edits can update Dzen, but Telegram deletions do not delete Dzen publications automatically.

## Direct Dzen Limits To Remember

These are direct Dzen Studio limits. They are useful for editorial rules even though this project sends articles through Telegram bridge.

- Article title: no links, maximum 140 characters.
- Article text: up to 100,000 characters including spaces.
- Article attachments: up to 100 images, videos, or embeds.
- Article image/GIF: minimum width 300 px, up to 30 MB.
- Dzen post: 4096 characters including spaces, up to 10 images.
- Post text supports Cyrillic, Latin, emojis, and embedded links.

## Good Dzen Article Shape

A good daily article should feel like an original Russian editorial digest, not a mechanically translated bundle of Telegram posts.

Start with a title sentence that creates honest curiosity from the real source facts. It should not merely retell the news. Good titles use a real market fear, question, consequence, unexpected signal, exact figure, company, country, or asset from the source posts. Avoid missing key facts, bait phrases, and invented drama.

Use the next paragraph to answer: what happened, why it matters, and why the reader should continue. Do not force a standalone date line such as `Сводка за 6 июля 2026 года:`. The date can appear naturally when useful, but the first screen should feel like an article, not a service bulletin.

Build the body from 3-5 compact blocks. Each block should have one idea, one clear connection to the source posts, and a short takeaway. Prefer concrete nouns and verbs over generic media phrasing. After important facts, explain the cause-and-effect link: why markets reacted, what this can change, and what it means for a normal reader or investor.

End with a short synthesis: what matters now, what investors will watch next, and why the story is not finished. Do not add predictions unless the source posts support them.

## Daily Editorial Workflow

1. Collect the latest translated posts that have not yet been considered for an article.
2. Treat those posts as candidates, not a mandatory checklist.
3. Pick one main semantic cluster or two closely related clusters. Good groupings are markets, macro, Russia, China, energy, crypto, companies, banks, currencies, and regulation.
4. Exclude weak or isolated posts if they would force an artificial connection.
5. Choose the title after the theme is clear. The title must sell the real article, not a more dramatic version of it.
6. Draft the opening as the card description: what happened, who or what is affected, and why the reader should continue.
7. Build 2-4 short blocks from source-grounded facts.
8. Finish with a cautious synthesis: what changed today or what is worth watching next.
9. Run the quality gate before publishing.

## Title And Card Rules

The title and first paragraph are the traffic gate. Make them concrete before making the article long.

Useful title shapes for this project:

- concrete actor + consequence;
- concrete market items + one unifying theme;
- event/fact + restrained consequence about what changed or what to watch;
- exact number, company, country, source, or ticker when the source supports it.

Do not start titles with `Почему`, `Что произошло`, `Что теперь будет`, or `Что означает`. The headline should name a company, country, asset, market, or event from the source posts, not hide the subject behind a repeated question template.

Adapted Dzen headline lessons:

- concrete details beat abstract wording;
- exact numbers, names, tickers, amounts, dates, and source attributions increase trust when they are real;
- a fact-plus-question title can work when the question is answered in the body;
- a list title can work when the list items are visible in the article;
- restrained negative framing is allowed only when the source fact is genuinely negative and the article explains it calmly.

Avoid generic titles such as `Main market news of the day`. Avoid hidden-subject intrigue, fake quotes, exaggerated drama, invented conflict, unsupported negative framing, and shock wording. If a hook appears in the title, the article body must pay it off directly.

## Recommendation Logic And Card Rules

Dzen says unrestricted recommendation depends first on meeting platform requirements. After that, reach depends on factors such as subscribers, the potentially interested audience, reader reaction, views, likes, completion or reading behavior, and topic popularity.

For this project, the article should therefore optimize for a truthful card and useful first screen:

- The title sentence must be short, specific, and factual.
- The first 1-2 paragraphs should make the article's subject clear because Dzen generates the card description from the first sentences.
- Avoid vague intrigue, hidden-subject hooks, excessive caps, code-like symbols, links, many question marks, and many exclamation marks in the first sentence.
- Do not exaggerate market moves or imply investment conclusions that the source posts do not support.
- If the article references external sources from the Telegram posts, preserve their attribution markers instead of pretending the analysis is original reporting.

## Source Channel Fit

The source channel `@num1_ch` is a high-frequency English feed of short market, macro, crypto, energy, company, and Russia/China news signals. Channel articles should therefore be themed digests. They should group related items from one channel lane rather than inflate one post into a full article.

Current cadence for this project is three articles per day: one for `russia`, one for `energy`, and one for `tech`.

The channel lanes are:

- `russia`: Russian market, ruble, CBR, IPO, bonds, equities, banks, companies, dividends, jobs, mortgage, and economy-for-people signals.
- `energy`: oil, gas, LNG, fuel, metals, commodities, Hormuz, Iran, sanctions, and geopolitical risks when they affect energy or prices.
- `tech`: crypto, BTC, ETH, DeFi, stablecoins, AI, chips, semiconductors, tech companies, and global tech-market signals.

Each lane has one daily window. The worker chooses a stable random minute inside that window for the current date. If there are too few matching unused posts for a lane, skip that article instead of padding it.

The automation uses `DZEN_ARTICLE_CANDIDATE_LIMIT=30` by default in the multi-channel setup, stores a persistent `topic` on queue messages, then filters candidates by that channel topic. A good article should usually come from the best related subset inside that candidate pool, normally 4-8 posts, not from every candidate.

Each scheduled article uses a persistent slot key such as `2026-07-10 energy:daily`. Published or pending slots are skipped on later worker passes to avoid duplicate bridge posts after restarts.

Current production behavior is direct bridge publishing (`DZEN_ARTICLE_REVIEW_ENABLED=false`). Set it to `true` only when the button-based admin review gate should be restored.

Energy and Tech can publish through their own Telegram bots via `DZEN_ENERGY_TELEGRAM_BOT_TOKEN` and `DZEN_TECH_TELEGRAM_BOT_TOKEN`; Russia falls back to the main `TELEGRAM_BOT_TOKEN` unless a Russia-specific token is configured.

The cross-platform footer should appear in each daily channel article by default. Since each channel now publishes one article per day, this keeps links present without repeating them three times per channel. Footer variants should rotate and use direct URLs for Telegram, VK, and MAX.

The article body may use short HTML bold accents through `<b>...</b>` for section headings or key takeaways. Do not bold the first title sentence, do not bold entire long paragraphs, and do not use Markdown.

## Style Rules

- Write in natural Russian.
- Write like an experienced financial journalist explaining the topic to a friend who follows economics but is not a professional.
- Preserve the topic and facts of the English source posts.
- Avoid literal translation patterns such as "eto imeet smysl dlya" when Russian would say "eto vazhno dlya" or "eto obyasnyaet".
- Keep sentences short. A good average is 10-18 words.
- Keep paragraphs short: 2-4 sentences and one idea per paragraph.
- Use numbers, names, links, tickers, and dates exactly as in sources unless explicitly translating a date format.
- Keep emojis only when they fit the Russian article tone.
- Do not overuse exclamation marks, rhetorical questions, or salesy calls to action.
- Do not use clickbait templates like "vy ne poverite", "vse ahnuli", "to, chto proizoshlo dalshe", or hidden-subject intrigue.
- Do not turn a one-line market signal into broad investment advice.
- Do not write like Bloomberg, Reuters, РБК, or an official analytical report.
- Never use bureaucratic phrases such as `формируется противоречивая картина`, `усилилась геополитическая составляющая`, `фундаментальные факторы`, `по итогам дня`, `в краткосрочной перспективе`, `при этом следует отметить`, or `одновременно наблюдается`.
- Explain complex terms such as EIA, SPR, Brent, and FOMC in simple words when they appear in the source material.

## LLM Editing Rules

Use the model to draft and organize, but keep editorial control over idea grouping, title choice, and fact checks.

Before publishing, remove common AI traces:

- vague summaries;
- inflated significance;
- awkward metaphors;
- repetitive transitions;
- unsupported context;
- punctuation that looks unnatural in Russian.

Human readability rules:

- use dependency-grammar-friendly structure: words that depend on each other should stay close;
- keep subject, verb, and object close when Russian syntax allows it;
- put the main fact early in the sentence;
- move caveats and background after the fact;
- use active, direct Russian phrasing;
- keep one paragraph to one idea;
- split sentences that carry two separate ideas;
- remove robotic transitions unless they are truly needed.

Typical edits after an LLM draft:

- replace generic openings with the day's actual topic;
- remove filler such as "it is important to note";
- cut unsupported explanations of causes;
- split overloaded paragraphs;
- make the title more concrete;
- remove any fact that cannot be traced to the source posts;
- smooth Russian punctuation and rhythm.

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

## Moderation Guardrails

Dzen can limit recommendations or block content for rule violations. The article generator must avoid:

- clickbait or misleading titles;
- copied, non-original, or unauthorized content;
- spam and artificial engagement schemes;
- hate, dehumanization, extremism, violence promotion, or group-based hostility;
- illegal goods/services or instructions for illegal acts;
- drug, weapon, gambling, or suicide instructions;
- graphic/shocking content used for attention;
- medical or pharmaceutical claims framed as advice without careful context;
- personal data exposure;
- unverified accusations against specific people or organizations.

## Article Prompt Contract

The model receives a set of translated source posts and produces one bridge-safe article.

The output must contain only the final article text. The first sentence is the title and must be under 140 characters. The full output must stay under `DZEN_ARTICLE_TARGET_MAX_CHARS`. The model must not invent facts, sources, quotes, statistics, or links.

If the source posts are too thin for a useful article, the model should produce a short digest instead of stretching the material.
