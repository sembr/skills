# SemBr Skills

[Agent Skills](https://agentskills.io/home)
for working with [Semantic Line Breaks](https://sembr.org).
The `sembr-reformat` skill reflows prose while preserving wording,
meaning, and rendered output.

## Installing

The [skills CLI](https://github.com/vercel-labs/skills)
works with Claude Code, Cursor, Codex, OpenCode, Pi,
and other supported coding agents.
With Node.js and npm installed,
run this command in your project directory:

```shell
npx skills add sembr/skills
```

The installer lets you select your agent and installation scope.
Project installation is the default.
To make the skill available across your projects, use `--global`:

```shell
npx skills add sembr/skills --global
```

You can select an agent with `--agent`,
for example `--agent codex` or `--agent claude-code`.
The CLI supports symlinks or copies;
its default symlinks let several agents use one installed copy.

Alternatively, the CLI can discover the skill from the website:

```shell
npx skills add https://sembr.org
```

Use one installation method for each agent
so that it does not load duplicate copies of the skill.
The following sections cover native plugin and package managers.

### Claude Code

In Claude Code, add the marketplace and then install the plugin:

```text
/plugin marketplace add sembr/skills
/plugin install sembr@sembr
```

Adding the marketplace makes its catalog available;
the second command installs the plugin.
The installer offers user, project, and local scopes.
Follow its activation instructions after installation.

The `/plugin` manager lets you view, enable, disable, or remove the plugin.
Under **Marketplaces > sembr**, you can enable auto-update.
Third-party marketplaces have auto-update disabled by default.
See the [Claude Code plugin guide](https://code.claude.com/docs/en/discover-plugins)
for manual updates and scope options.

### Cursor

In **Customize**, open **Plugins**,
then select **Add > From GitHub Repository**
and enter `https://github.com/sembr/skills`.
After importing the marketplace, install the `sembr` plugin.
The repository includes the Cursor marketplace manifest required for import.

The skill appears in Customize with your other skills.
Use Cursor's plugin controls to manage the installation.
See [Cursor plugins](https://cursor.com/docs/plugins)
and [Agent Skills](https://cursor.com/docs/skills)
for installation and usage details.

### Codex

With Codex CLI installed, run these commands in your terminal:

```shell
codex plugin marketplace add sembr/skills
codex plugin add sembr@sembr
```

The first command adds the marketplace;
the second installs the SemBr plugin.
Start a new Codex session to use its skill.
In Codex CLI, `/plugins` opens the plugin browser,
where you can inspect the plugin and turn it on or off.

To fetch marketplace changes and reinstall the plugin:

```shell
codex plugin marketplace upgrade sembr
codex plugin remove sembr@sembr
codex plugin add sembr@sembr
```

Start a new session after the update.
To remove the plugin:

```shell
codex plugin remove sembr@sembr
```

The skills CLI and manual installation remain available
for Codex surfaces without plugin support.
See [OpenAI's plugin guide](https://learn.chatgpt.com/docs/plugins)
for supported surfaces and
[plugin packaging](https://developers.openai.com/plugins/build/plugins)
for marketplace details.

### Pi

Install the skill as a
[Pi package](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md):

```shell
pi install git:github.com/sembr/skills
```

Pi installs packages for your user by default.
Add `--local` to install for the current project.
Project packages load after you trust the project.

You can list, update, or remove packages with:

```shell
pi list
pi update --extensions
pi remove git:github.com/sembr/skills
```

The update command updates installed packages, including SemBr.
For a project installation, use `--local` with the removal command.
See the [Pi command reference](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md#package-commands)
for package management options.

## Using the skill

After installation, ask your agent:

```text
Use sembr-reformat to apply semantic line breaks to README.md.
Preserve the wording and rendered output.
```

Agents can also select the skill when a request matches its description.
Explicit selection and activation depend on the agent;
use its skill selector if the skill does not load for your request.
Review the resulting diff before accepting the changes.

## Managing CLI installations

For skills installed with `npx skills`,
run these commands from your project directory:

```shell
npx skills list
npx skills update sembr-reformat --project
npx skills remove sembr-reformat
```

For a user installation, use `--global`:

```shell
npx skills list --global
npx skills update sembr-reformat --global
npx skills remove sembr-reformat --global
```

These commands manage skills installed by the skills CLI.
For a plugin or Pi package, use the manager that installed it.

## Manual installation

Clone this repository and copy the complete
`skills/sembr-reformat/` folder into your agent's skill directory,
including `SKILL.md` and `agents/openai.yaml`.

| Agent | User skill directory | Documentation |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | [Skills](https://code.claude.com/docs/en/skills) |
| Cursor | `~/.cursor/skills/` | [Agent Skills](https://cursor.com/docs/skills) |
| OpenCode | `~/.config/opencode/skills/` | [Agent Skills](https://opencode.ai/docs/skills/) |
| Codex | `~/.agents/skills/` | [Build skills](https://learn.chatgpt.com/docs/build-skills) |
| Pi | `~/.pi/agent/skills/` | [Skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) |

For example, the Codex copy will contain
`~/.agents/skills/sembr-reformat/SKILL.md`.
See your agent's documentation for project directories
and any reload or restart steps.

Manual copies do not update automatically.
To update, pull the repository and replace the installed skill folder.
To remove the skill, delete the folder you copied.

## Resources

- [Semantic Line Breaks specification](https://sembr.org)
- [Agent Skills standard](https://agentskills.io/home)

## License

Released under the [MIT License](LICENSE).
