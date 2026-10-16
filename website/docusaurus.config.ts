import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Lemon',
  tagline: 'A concurrent build system for OCaml and Reason',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://manasjayanth.github.io',
  baseUrl: '/lemon/',

  organizationName: 'ManasJayanth',
  projectName: 'lemon',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/ManasJayanth/lemon/tree/main/website/',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Lemon',
      logo: {
        alt: 'Lemon logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'default',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://github.com/ManasJayanth/lemon',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Introduction',
              to: '/docs/intro',
            },
            {
              label: 'Getting started',
              to: '/docs/getting-started',
            },
            {
              label: 'Known limitations',
              to: '/docs/limitations',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/ManasJayanth/lemon',
            },
            {
              label: 'Compatibility notes',
              to: '/docs/compatibility',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Lemon contributors. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['ocaml', 'reason', 'bash'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
