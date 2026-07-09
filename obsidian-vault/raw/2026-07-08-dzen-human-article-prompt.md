# User Dzen Human Article Prompt

Date: 2026-07-08
Source: user-supplied editorial prompt in Codex thread.

## Summary

The user rejected the previous dry article style and asked the project to write Dzen articles as readable financial journalism. The new goal is retention, engagement, and CTR through truthful curiosity, simple explanations, short paragraphs, and clear cause-and-effect logic.

## Key Instructions

- Role: experienced financial journalist and Dzen editor.
- Reader: interested in economics, but not a finance professional.
- Tone: human, conversational, simple, and clear.
- Avoid the style of Bloomberg, Reuters, РБК, and official analytical reports.
- Avoid bureaucratic phrases, especially `формируется противоречивая картина`, `усилилась геополитическая составляющая`, `фундаментальные факторы`, `по итогам дня`, `в краткосрочной перспективе`, `при этом следует отметить`, and `одновременно наблюдается`.
- Headline should create honest intrigue, not retell the news and not become clickbait.
- First paragraph should immediately explain what happened, why it matters, and why the reader should continue.
- Do not start the article with `По данным`, `Согласно`, or `Сегодня были опубликованы`.
- Body should not be a list of news. Each paragraph should logically continue the previous one.
- Explain cause and effect after important facts: why it happened, why the market reacts, what it can change, and what it means for a reader or investor.
- Sentences should usually be short, around 10-18 words.
- Paragraphs should usually contain 2-4 sentences and never become long blocks.
- Explain complex terms such as EIA, SPR, Brent, and FOMC in simple words when used.
- Ending should not be dry. It should explain what matters next, what investors will watch, and why the story is not over.

## Applied Project Decision

The article prompt should no longer force a standalone `Сводка за ...` line. The date may appear naturally only when useful. The formatter should preserve a generated article's body instead of inserting a dry date summary automatically.

## Related

- [[prompts/dzen-article-prompt]]
- [[wiki/dzen-article-playbook]]
