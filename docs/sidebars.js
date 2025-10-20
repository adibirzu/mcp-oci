/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'index',
    'troubleshooting',
    {
      type: 'category',
      label: 'Clients',
      items: [
        'clients/overview',
        'clients/cursor',
        'clients/cline',
      ],
    },
    {
      type: 'category',
      label: 'Servers',
      items: [
        'servers/overview',
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
        'servers/usageapi',
        'servers/budgets',
        'servers/limits',
        'servers/loganalytics',
        'servers/introspect',
        'servers/security',
        'servers/osub',
      ],
    },
    {
      type: 'category',
      label: 'How-To',
      items: [
        'howto/cost-analysis',
        'howto/rate-cards',
      ],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/architecture',
        'development/conventions',
        'integrations',
        'development/fastmcp',
        'development/testing',
      ],
    },
  ],
};

module.exports = sidebars;
