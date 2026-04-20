# Zevenue GTM Skills

The methodology layer [Zevenue](https://zevenue.com) runs on top of Claude Code. These are the Claude Code skills we use to turn outbound from a guessing game into an engineering discipline — productized and shareable.

If you run outbound, do RevOps, or build GTM systems, these are drop-in skills that encode the frameworks we've tuned across four years of client delivery.

## What's in here

| Skill | What it does |
|---|---|
| [`signal-builder`](.claude/skills/signal-builder/) | Scans a prospect's website + enrichment data and produces a ranked signal analysis. Scores each signal 1-10 and recommends a campaign approach per signal. |
| [`email-writer`](.claude/skills/email-writer/) | Generates 3-email cold campaigns using the Situation → Insight → Inquisition methodology. Enforces deliverability rules, word limits, and a QA checklist. |
| [`prospect-posts`](.claude/skills/prospect-posts/) | Scrapes recent LinkedIn posts from one or more prospect profiles via Apify and scans them for a given theme. Useful for account intelligence. |
| [`job-search`](.claude/skills/job-search/) | Queries the TheirStack API for job postings at a set of companies. Hiring patterns are one of the strongest timing signals for outbound. |
| [`linkedin-extract`](.claude/skills/linkedin-extract/) | Archives your own LinkedIn posts locally for blog/newsletter repurposing. |

They chain:

```
signal-builder → email-writer          (core outbound loop)
job-search     → signal-builder        (hiring is a signal input)
prospect-posts → signal-builder        (content signals feed targeting)
linkedin-extract → [your content repurposing skill]
```

## Install

1. **Clone into your workspace** — these skills assume a Claude Code project structure:
   ```bash
   git clone https://github.com/Zevenue/gtm-skills.git
   cd gtm-skills
   ```
2. **Drop skills into your project's Claude Code config.** Either copy `.claude/skills/*` into your own project's `.claude/skills/`, or run Claude Code from this directory directly.
3. **Copy `utils/` and `context/outreach/` into your project root.** The skills reference these paths.
4. **Set up the environment:**
   ```bash
   cp .env.example .env
   # Fill in APIFY_API_TOKEN and THEIRSTACK_API_KEY as needed
   pip install requests python-dotenv
   ```

### API keys

| Variable | Used by | Get one at |
|---|---|---|
| `APIFY_API_TOKEN` | `prospect-posts`, `linkedin-extract` | https://console.apify.com/account/integrations |
| `THEIRSTACK_API_KEY` | `job-search` | https://app.theirstack.com/settings/api |

`signal-builder` and `email-writer` don't need external APIs — they run on Claude + your context.

## Use

In Claude Code, invoke by name:

```
/signal-builder https://prospect.com  [client-context]
/email-writer   [signal output]       [client-context]       [prospect info]
/job-search     stripe.com,notion.so  --title "SDR,BDR"
/prospect-posts https://linkedin.com/in/someone  "AI-first GTM"
/linkedin-extract https://linkedin.com/in/your-handle  --count 20
```

Each skill's `skill.md` is the authoritative spec for what it expects and what it returns.

## How to think about these

These skills are opinionated. They encode judgments like:

- **Three emails per sequence (max).** If three well-targeted emails don't land, more won't help — the signal or the angle was wrong.
- **The message is only as good as the list.** If you need heavy personalization to make copy work, your targeting is wrong.
- **Ask for truth, not time.** Cold email CTAs should be "Is this you?" not "Can we schedule 30 minutes?"
- **Every signal has a score.** A 4/10 is fine — it helps the Email Writer calibrate tone.

See `context/outreach/outreach-principles.md` for the full framework.


## License

MIT. See [LICENSE](LICENSE).

## About Zevenue

[Zevenue](https://zevenue.com) is a Toronto-based GTM engineering firm. We build custom outbound + RevOps systems for GTM teams. Reach me at: yusuf@zevenue.com
