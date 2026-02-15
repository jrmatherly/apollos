---
sidebar_position: 1
---

<!-- NOTE: URLs reference apollosai.dev. If forking this project, update to your domain. -->

# Desktop

> Upload your knowledge base to Apollos and chat with your whole corpus

## Companion App

Share your files, folders with Apollos using the app.
Apollos will keep these files in sync to provide contextual responses when you search or chat.

## Setup
:::info[Self Hosting]
If you are self-hosting the Apollos server, update the *Settings* page on the Apollos Desktop app to:
- Set the `Apollos URL` field to your Apollos server URL. By default, use `http://127.0.0.1:42110`.
- Do not set the `Apollos API Key` field if your Apollos server runs in anonymous mode. For example, `apollos --anonymous-mode`
:::

1. Install the [Apollos Desktop app](https://apollosai.dev/downloads) for your OS
2. Generate an API key on the [Apollos Web App](https://app.apollosai.dev/settings#clients)
3. Set your Apollos API Key on the *Settings* page of the Apollos Desktop app
4. [Optional] Add any files, folders you'd like Apollos to be aware of on the *Settings* page and Click *Save*.
   These files and folders will be automatically kept in sync for you

# Main App

You can also install the Apollos application on your desktop as a progressive web app.

1. Open the [Apollos Web App](https://app.apollosai.dev) in Chrome.
2. Click on the install button in the address bar to install the app. You must be logged into your Chrome browser for this to work.

![progressive web app install icon](/img/pwa_install_desktop.png)

Alternatively, you can also install using this route:

1. Open the three-dot menu in the top right corner of the browser.
2. Go to 'Cast, Save, and Share' option.
3. Click on the "Open in Apollos" option.

![progressive web app install route](/img/chrome_pwa_alt.png)
