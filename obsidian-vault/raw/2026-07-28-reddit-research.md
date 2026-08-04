# 2026-07-28 Reddit Research

## Source Links

- Reddit spam policy: https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam
- Reddit Data API Wiki: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- Reddit developer platform and API access: https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data
- Reddit app labels: https://support.reddithelp.com/hc/en-us/articles/45376380316052-Apps-on-Reddit-and-how-to-get-a-label-for-your-app
- Reddit posting/commenting limits: https://support.reddithelp.com/hc/en-us/articles/360060422572-How-do-I-post-and-comment-on-Reddit

## Notes

Reddit treats repeated or unsolicited automated activity as spam risk, even when the action is technically possible through the API. Community and account-level spam filters can affect visibility, especially for new accounts or accounts that post too often without trusted participation.

The project should avoid third-party subreddit autoposting at launch. A profile-based stream is safer because it does not push content into communities that did not ask for it.

API access and automated behavior should be transparent. If the system later publishes through Reddit automation, it should use a registered Reddit app, OAuth, honest user-agent metadata, rate-limit handling, and a conservative posting cadence.

## Product Implication

Reddit should not mirror every Telegram item. It should select only posts with a clear human-readable angle and skip weak slots. The first experiment should target 6 possible posts per day, with a hard cap of 12 after quality is proven.

