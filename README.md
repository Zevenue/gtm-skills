# Zevenue GTM Skills

The methodology layer [Zevenue](https://zevenue.com) runs on top of Claude Code. These are the Claude Code skills we use to turn outbound from a guessing game into an engineering discipline — productized and shareable.

If you run outbound, do RevOps, or build GTM systems, these are drop-in skills that encode the frameworks we've tuned across four years of GTM delivery.

## What's in here

| Skill | What it does |
|---|---|
| [`signal-builder`](.claude/skills/signal-builder/) | Scans a prospect's website + enrichment data and produces a ranked signal analysis. Scores each signal 1-10 and recommends a campaign approach per signal. |
| [`email-writer`](.claude/skills/email-writer/) | Generates 3-email cold campaigns using the Situation → Insight → Inquisition methodology. Enforces deliverability rules, word limits, and a QA checklist. |
| [`creative-variable`](.claude/skills/creative-variable/) | Specs the personalization variables for a campaign — names, grammar, sources, Claygent prompts, fallbacks, rendered examples. Encodes the four archetypes (verbatim-pain, manual-task, strategic-alternative, failure-mode). |
| [`prospect-posts`](.claude/skills/prospect-posts/) | Scrapes recent LinkedIn posts from one or more prospect profiles via Apify and scans them for a given theme. Useful for account intelligence. |
| [`job-search`](.claude/skills/job-search/) | Queries the TheirStack API for job postings at a set of companies. Hiring patterns are one of the strongest timing signals for outbound. |

They chain:

```
signal-builder → creative-variable → email-writer    (core outbound loop)
job-search     → signal-builder                      (hiring is a signal input)
prospect-posts → signal-builder                      (content signals feed targeting)
```

## Install

1. **Clone into your workspace** — these skills assume a Claude Code project structure:
   ```bash
   git clone https://github.com/Zevenue/gtm-skills.git
   cd gtm-skills
   ```
2. **Install the skills.** Either:
   - **Globally** (recommended) — copy `.claude/skills/*` into `~/.claude/skills/` so they're available in every Claude Code session, or
   - **Per project** — copy `.claude/skills/*` into your project's `.claude/skills/`, or run Claude Code from this directory directly.
3. **Copy `utils/` and the entire `context/` directory into your project root.** The skills reference paths under `context/outreach/`, `context/playbooks/`, and (optionally) `context/offer.md`.
4. **Set up the environment:**
   ```bash
   cp .env.example .env
   # Fill in APIFY_API_TOKEN and THEIRSTACK_API_KEY as needed
   pip install -r requirements.txt
   ```
   Python 3.10+ recommended. `signal-builder`, `email-writer`, and `creative-variable` need no Python or API keys at all.

### API keys

| Variable | Used by | Get one at |
|---|---|---|
| `APIFY_API_TOKEN` | `prospect-posts` | https://console.apify.com/account/integrations |
| `THEIRSTACK_API_KEY` | `job-search` | https://app.theirstack.com/settings/api |

`signal-builder` and `email-writer` don't need external APIs — they run on Claude + your context.

## Use

In Claude Code, invoke by name:

```
/signal-builder    https://prospect.com  [offer-context]
/email-writer      [signal output]       [offer-context]       [prospect info]
/creative-variable [campaign angle]      [ICP]                 [existing copy?]
/job-search        stripe.com,notion.so  --title "SDR,BDR"
/prospect-posts    https://linkedin.com/in/someone  "AI-first GTM"
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
