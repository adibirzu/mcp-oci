/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'index',
    {
      type: 'category',
      label: 'Servers',
      items: [
        'servers/iam',
        'servers/compute',
        'servers/objectstorage',
        'servers/networking',
        'servers/blockstorage',
        'servers/loadbalancer',
        'servers/filestorage',
        'servers/dns',
        'servers/apigateway',
        'servers/database',
        'servers/oke',
        'servers/functions',
        'servers/logging',
        'servers/monitoring',
        'servers/events',
        'servers/streaming',
        'servers/ons',
        'servers/vault',
        'servers/kms',
        'servers/resourcemanager',
      ],
    },
    {
      type: 'category',
      label: 'Development',
      items: [],
    },
  ],
};

module.exports = sidebars;
