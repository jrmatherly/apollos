---
sidebar_position: 2
---

# Emacs

<img src="https://stable.melpa.org/packages/apollos-badge.svg" width="130" alt="Melpa Stable Badge" />
<img src="https://melpa.org/packages/apollos-badge.svg" width="150" alt="Melpa Badge" />

<img src="https://github.com/jrmatherly/apollos/actions/workflows/build_apollos_el.yml/badge.svg" width="150" alt="Build Badge" />
<img src="https://github.com/jrmatherly/apollos/actions/workflows/test_apollos_el.yml/badge.svg" width="150" alt="Test Badge" />

<br />
<br />
> Query your Second Brain from Emacs

## Features
- **Chat**
  - **Faster answers**: Find answers quickly, from your private notes or the public internet
  - **Assisted creativity**: Smoothly weave across retrieving answers and generating content
  - **Iterative discovery**: Iteratively explore and re-discover your notes
- **Search**
  - **Natural**: Advanced natural language understanding using Transformer based ML Models
  - **Incremental**: Incremental search for a fast, search-as-you-type experience

## Interface

| Search | Chat |
|:------:|:----:|
| ![apollos search on emacs](/img/apollos_search_on_emacs.png) | ![apollos chat on emacs](/img/apollos_chat_on_emacs.png) |

## Setup
:::info[Self Hosting]
If you are self-hosting the Apollos server modify the install steps below:
- Set `apollos-server-url` to your Apollos server URL. By default, use `http://127.0.0.1:42110`.
- Do not set `apollos-api-key` if your Apollos server runs in anonymous mode. For example, `apollos --anonymous-mode`
:::

1. Generate an API key on the [Apollos Web App](https://app.apollosai.dev/settings#clients)
2. Add below snippet to your Emacs config file, usually at `~/.emacs.d/init.el`

#### **Direct Install**
*Apollos will index your org-agenda files, by default*

```elisp
;; Install Apollos.el
M-x package-install apollos

; Set your Apollos API key
(setq apollos-api-key "YOUR_APOLLOS_CLOUD_API_KEY")
(setq apollos-server-url "https://app.apollosai.dev")
```

#### **Minimal Install**
*Apollos will index your org-agenda files, by default*

```elisp
;; Install Apollos client from MELPA Stable
(use-package apollos
  :ensure t
  :pin melpa-stable
  :bind ("C-c s" . 'apollos)
  :config (setq apollos-api-key "YOUR_APOLLOS_CLOUD_API_KEY"
                apollos-server-url "https://app.apollosai.dev"))
```

#### **Standard Install**
*Configures the specified org files, directories to be indexed by Apollos*

```elisp
;; Install Apollos client from MELPA Stable
(use-package apollos
  :ensure t
  :pin melpa-stable
  :bind ("C-c s" . 'apollos)
  :config (setq apollos-api-key "YOUR_APOLLOS_CLOUD_API_KEY"
                apollos-server-url "https://app.apollosai.dev"
                apollos-index-directories '("~/docs/org-roam" "~/docs/notes")
                apollos-index-files '("~/docs/todo.org" "~/docs/work.org")))
```

#### **Straight.el**
*Configures the specified org files, directories to be indexed by Apollos*

```elisp
;; Install Apollos client using Straight.el
(use-package apollos
  :after org
  :straight (apollos :type git :host github :repo "jrmatherly/apollos" :files (:defaults "src/interface/emacs/apollos.el"))
  :bind ("C-c s" . 'apollos)
  :config (setq apollos-api-key "YOUR_APOLLOS_CLOUD_API_KEY"
                apollos-server-url "https://app.apollosai.dev"
                apollos-org-directories '("~/docs/org-roam" "~/docs/notes")
                apollos-org-files '("~/docs/todo.org" "~/docs/work.org")))
```

## Use
### Search
See [Apollos Search](/features/search) for details
1. Hit  `C-c s s` (or `M-x apollos RET s`) to open apollos search
2. Enter your query in natural language<br/>
  E.g. *"What is the meaning of life?"*, *"My life goals for 2023"*

### Chat
See [Apollos Chat](/features/chat) for details
1. Hit `C-c s c` (or `M-x apollos RET c`) to open apollos chat
2. Ask questions in a natural, conversational style<br/>
  E.g. *"When did I file my taxes last year?"*

### Find Similar Entries
This feature finds entries similar to the one you are currently on.
1. Move cursor to the org-mode entry, markdown section or text paragraph you want to find similar entries for
2. Hit `C-c s f` (or `M-x apollos RET f`) to find similar entries

### Advanced Usage
- Add [query filters](/miscellaneous/query-filters) during search to narrow down results further
  e.g. `What is the meaning of life? -"god" +"none" dt>"last week"`

- Use `C-c C-o 2` to open the current result at cursor in its source org file
  - This calls `M-x org-open-at-point` on the current entry and opens the second link in the entry.
  - The second link is the entries [org-id](https://orgmode.org/manual/Handling-Links.html#FOOT28), if set, or the heading text.
    The first link is the line number of the entry in the source file. This link is less robust to file changes.
  - Note: If you have [speed keys](https://orgmode.org/manual/Speed-Keys.html) enabled, `o 2` will also work

### Apollos Menu
![Apollos Menu](/img/apollos_emacs_menu.png)
Hit `C-c s` (or `M-x apollos`) to open the apollos menu above. Then:
- Hit `t` until you preferred content type is selected in the apollos menu
  `Content Type` specifies the content to perform `Search`, `Update` or `Find Similar` actions on
- Hit `n` twice and then enter number of results you want to see
  `Results Count` is used by the `Search` and `Find Similar` actions
- Hit `-f u` to `force` update the apollos content index
  The `Force Update` switch is only used by the `Update` action

## Upgrade
Use your Emacs package manager to upgrade `apollos.el`
<!-- tabs:start -->

#### **With MELPA**
1. Run `M-x package-refresh-content`
2. Run `M-x package-reinstall apollos`

#### **With Straight.el**
- Run `M-x straight-pull-package apollos`

<!-- tabs:end -->
