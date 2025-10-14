/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'intro',
    'installation',
    'configuration',
    'tools',
    'usage',
    'development',
    {
      type: 'category',
      label: 'Services',
      items: [
        'services/compute',
        'services/objectstorage',
        'services/iam',
        'services/networking',
      ],
    },
    'license',
  ],
};

module.exports = sidebars;

