<p align="center"><img src="https://assets.apollosai.dev/apollos-logo-sideways-1200x540.png" width="230" alt="Apollos Logo"></p>

<div align="center">

[![test](https://github.com/jrmatherly/apollos/actions/workflows/test.yml/badge.svg)](https://github.com/jrmatherly/apollos/actions/workflows/test.yml)

</div>

<div align="center">
<b>Your AI second brain</b>
</div>

<br />

## Overview

[Apollos](https://github.com/jrmatherly/apollos) is a personal AI app to extend your capabilities. It smoothly scales up from an on-device personal AI to a cloud-scale enterprise AI.

- Chat with any local or online LLM (e.g llama3, qwen, gemma, mistral, gpt, claude, gemini, deepseek).
- Get answers from the internet and your docs (including image, pdf, markdown, org-mode, word, notion files).
- Access it from your Browser, Obsidian, Emacs, Desktop, Phone or Whatsapp.
- Create agents with custom knowledge, persona, chat model and tools to take on any role.
- Automate away repetitive research. Get personal newsletters and smart notifications delivered to your inbox.
- Find relevant docs quickly and easily using our advanced semantic search.
- Generate images, talk out loud, play your messages.
- Apollos is open-source, self-hostable. Always.
- Run it privately on [your computer](https://docs.apollosai.dev/get-started/setup)

***

## Full feature list
You can see the full feature list [here](https://docs.apollosai.dev/category/features).

## Self-Host

To get started with self-hosting Apollos, [read the docs](https://docs.apollosai.dev/get-started/setup).

## Development

The project uses [mise-en-place](https://mise.jdx.dev) for tool management and task automation:

```bash
git clone https://github.com/jrmatherly/apollos && cd apollos
mise install          # Python 3.12, bun, uv — pinned versions
mise run setup        # Install deps, migrate DB, build frontend
mise run dev          # Server at http://localhost:42110
```

Run `mise tasks ls` to see all available tasks. See [CLAUDE.md](CLAUDE.md) for full development docs.
