# Human Writing And OpenRouter Notes

Checked on 2026-07-06.

## Sources

- OpenRouter GPT-4.1 model page: https://openrouter.ai/openai/gpt-4.1
- OpenRouter quickstart: https://openrouter.ai/docs/quickstart
- OpenRouter authentication: https://openrouter.ai/docs/api/reference/authentication
- OpenAI GPT-4.1 announcement: https://openai.com/index/gpt-4-1/
- Dependency length minimization evidence: https://pmc.ncbi.nlm.nih.gov/articles/PMC4547262/
- Plain-language guidance: https://digital.gov/guides/plain-language/writing
- Plain language for experts: https://www.nngroup.com/articles/plain-language-experts/

## Findings

OpenRouter supports an OpenAI-compatible Chat Completions endpoint. The project already calls `https://openrouter.ai/api/v1/chat/completions`, so no extra SDK is needed.

OpenRouter lists `openai/gpt-4.1` as a GPT model option. OpenAI's GPT-4.1 announcement describes the family as stronger on instruction following and long-context work than older GPT-4o-era models, which fits article drafting better than local 8B output.

Human-readable writing guidance aligns with the user's dependency-grammar prompt idea. Dependency length minimization research supports the practical rule that words depending on each other should stay close when possible. Plain-language guidance also recommends active voice, short sentences, familiar words, and easy-to-scan paragraphs.

## Project Adaptation

Use dependency grammar as an editing rule, not as a claim that a text is "100% human":

- keep subject, verb, and object close;
- put the main fact early;
- move caveats and background after the fact;
- use active, direct Russian phrasing;
- keep one paragraph to one idea;
- split sentences that carry two ideas;
- remove robotic transitions and generic AI filler.

For Dzen, this is part of the article prompt and review checklist. It should improve readability without weakening factual validation.
