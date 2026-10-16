import type {SidebarsConfig} from '@docusaurus/types';

const sidebars: SidebarsConfig = {
  default: [
    'intro',
    'getting-started',
    'targets',
    'installing',
    {
      type: 'category',
      label: 'Reference',
      items: ['compatibility', 'limitations'],
    },
  ],
};

export default sidebars;
