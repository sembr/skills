# SemBr Skills

A collection of [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
for working with [Semantic Line Breaks](https://sembr.org).

## Installing

These skills work with any agent that supports the Agent Skills standard,
including [Claude Code](https://claude.com/claude-code),
[Cursor](https://cursor.com),
[OpenCode](https://opencode.ai),
[OpenAI Codex](https://developers.openai.com/codex/),
and [Pi](https://pi.dev).

### Claude Code

Install using the [plugin marketplace](https://code.claude.com/docs/en/discover-plugins#add-from-github):

```console
/plugin marketplace add sembr/skills
```

### Cursor

Install from the [Cursor Marketplace](https://cursor.com/marketplace),
or add manually via **Settings > Rules > Add Rule > Remote Rule (Github)** with `sembr/skills`.

### npx skills

Install using the [`npx skills`](https://skills.sh) CLI from
[sembr.org](https://sembr.org):

```console
npx skills add https://sembr.org
```

`sembr.org` serves the skills under the
[`/.well-known/agent-skills/`](https://sembr.org/.well-known/agent-skills/index.json)
endpoint
([RFC 8615](https://www.rfc-editor.org/rfc/rfc8615)).

Alternatively, install directly from GitHub:

```console
npx skills add sembr/skills
```

### Pi

Install as a [Pi Package](https://github.com/earendil-works/pi/tree/main/packages/coding-agent#pi-packages):

```console
pi install git:github.com/sembr/skills
```

### Clone / Copy

Clone this repo and copy the skill folders into the appropriate directory for your agent:

| Agent        | Skill Directory                | Docs                                                                         |
|--------------|--------------------------------|------------------------------------------------------------------------------|
| Claude Code  | `~/.claude/skills/`            | [docs](https://code.claude.com/docs/en/skills)                               |
| Cursor       | `~/.cursor/skills/`            | [docs](https://cursor.com/docs/context/skills)                               |
| OpenCode     | `~/.config/opencode/skills/`   | [docs](https://opencode.ai/docs/skills/)                                     |
| OpenAI Codex | `~/.codex/skills/`             | [docs](https://developers.openai.com/codex/skills/)                          |
| Pi           | `~/.pi/agent/skills/`          | [docs](https://pi.dev)                                                       |

## Skills

Skills are contextual and auto-loaded based on your conversation.
When a request matches a skill's triggers,
the agent loads and applies the relevant skill.

| Skill            | Useful for                                                     |
|------------------|----------------------------------------------------------------|
| `sembr-reformat` | Reflowing prose into [Semantic Line Breaks](https://sembr.org) |

## Resources

- [Semantic Line Breaks specification](https://sembr.org)
- [Anthropic: Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## License

Released under the [MIT License](LICENSE).
