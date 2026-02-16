// NOTE: URLs reference apollosai.dev. If forking this project, update to your domain.
// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import { themes as prismThemes } from "prism-react-renderer";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Apollos AI",
  tagline: "Your Second Brain",

  staticDirectories: ["assets"],

  favicon: "img/favicon-128x128.ico",

  // Set the production url of your site here
  url: "https://docs.apollosai.dev",
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: "/",

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: "jrmatherly", // Usually your GitHub org/user name.
  projectName: "apollos", // Usually your repo name.

  onBrokenLinks: "throw",
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: "warn",
    },
  },

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  // Add a widget for Chatwoot for live chat if users need help
  clientModules: [require.resolve("./src/components/ChatwootWidget.js")],

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: "./sidebars.js",
          routeBasePath: "/",
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            "https://github.com/jrmatherly/apollos/tree/master/documentation/",
        },
        blog: {
          showReadingTime: true,
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            "https://github.com/jrmatherly/apollos/tree/master/documentation/blog/",
        },
        theme: {
          customCss: "./src/css/custom.css",
        },
        sitemap: {
          lastmod: "date",
          changefreq: "weekly",
          priority: 0.5,
          filename: "sitemap.xml",
        },
      }),
    ],
  ],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: "img/apollos_documentation.png",
      metadata: [
        { name: "og:title", content: "Docs" },
        { name: "og:type", content: "website" },
        { name: "og:site_name", content: "Apollos Documentation" },
        {
          name: "og:description",
          content: "Quickly get started with using or self-hosting Apollos",
        },
        { name: "og:url", content: "https://docs.apollosai.dev" },
        {
          name: "keywords",
          content:
            "apollos, apollos ai, chatgpt, open source ai, open source, transparent, accessible, trustworthy, hackable, index notes, rag, productivity",
        },
      ],
      navbar: {
        title: "Apollos",
        logo: {
          alt: "Apollos AI",
          src: "img/favicon-128x128.ico",
        },
        items: [
          {
            href: "https://github.com/jrmatherly/apollos",
            position: "right",
            className: "header-github-link",
            title: "Codebase",
            "aria-label": "GitHub repository",
          },
        ],
      },
      footer: {
        style: "dark",
        links: [
          {
            title: "Docs",
            items: [
              {
                label: "Get Started",
                to: "/",
              },
              {
                label: "Privacy",
                to: "/privacy",
              },
              {
                label: "Features",
                to: "/features/all-features",
              },
              {
                label: "Client Apps",
                to: "/category/clients",
              },
              {
                label: "Self-Host",
                to: "/get-started/setup",
              },
              {
                label: "Contribute",
                to: "/contributing/development",
              },
            ],
          },
          {
            title: "Community",
            items: [
              {
                label: "GitHub",
                href: "https://github.com/jrmatherly/apollos/issues",
              },
              {
                label: "Email",
                href: "mailto:support@apollosai.dev",
              },
            ],
          },
          {
            title: "More",
            items: [
              {
                label: "GitHub",
                href: "https://github.com/jrmatherly/apollos",
              },
              {
                label: "Apollos Inc.",
                href: "https://apollosai.dev",
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Apollos, Inc.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
      algolia: {
        appId: "",
        apiKey: "",
        indexName: "apollos",
        contextualSearch: false,
      },
    }),
};

export default config;
