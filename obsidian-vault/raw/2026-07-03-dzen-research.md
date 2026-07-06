# Dzen Research

Checked on 2026-07-03.

## Official Sources

- Telegram bot bridge: https://dzen.ru/help/ru/channel/cross-platform.html
- Article format: https://dzen.ru/help/ru/channel/article.html
- Post format: https://dzen.ru/help/ru/channel/post.html
- Content requirements: https://dzen.ru/help/ru/requirements/rules.html
- Clickbait: https://dzen.ru/help/ru/requirements/clickbait.html
- Content display models: https://dzen.ru/help/ru/models.html
- Card-preview rules: https://dzen.ru/help/ru/requirements/card-preview.html
- Non-original content: https://dzen.ru/help/ru/requirements/copypaste.html

## Bridge Facts

Dzen's Telegram bot can publish posts from a Telegram channel into Dzen after authorization and synchronization. The Telegram channel must be public. One Dzen channel can be linked to one Telegram channel.

The first sentence of the Telegram post becomes the Dzen title, and the title limit is 140 characters. Formatting applied in Telegram is not transferred into the Dzen article. A bridge post can be published automatically or manually depending on bot mode.

In automatic mode, edits in Telegram can update the Dzen publication, but deleting the Telegram post does not delete the Dzen publication. The bridge can transfer media up to 20 MB, but this project currently treats Dzen bridge messages as text-only.

## Article And Post Facts

Direct Dzen Studio articles can contain up to 100,000 characters and up to 100 attachments. Dzen post format is a short note visible in the feed, with a 4096-character limit and up to 10 images.

This project does not publish through Studio directly. It sends text through Telegram, so bridge articles must fit Telegram's 4096-character message limit.

Direct article titles cannot contain links and can be no longer than 140 characters. Dzen post text supports Cyrillic, Latin, emojis, and embedded links.

## Content And Moderation Facts

Dzen says compliant publications can be recommended broadly, while rule violations can limit publication visibility, restrict monetization, or lead to channel restrictions. Risk areas include clickbait, spam, non-original content, hate or violence, illegal information, explicit content, tragic/shocking content used for attention, gambling, and sensitive medical/pharmaceutical claims.

Dzen says recommendation reach also depends on factors such as subscriber base, potentially interested audience, audience reaction, views, likes, reading behavior, and topic popularity. Card previews matter because the description is generated automatically from the first sentences, while the title must be concise, meaningful, non-clickbait, and free of links, excessive caps, repeated punctuation, and code-like symbols.

## Practical Article Guidance

Good Dzen articles should be useful and self-contained. For this project, daily articles should synthesize the day's source posts into one Russian editorial digest. The article should have a factual title sentence, a useful opening, 3-5 compact blocks, and a short conclusion. Avoid bait, overstatement, unsupported predictions, and generic filler.
