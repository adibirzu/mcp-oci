// Minimal Docusaurus config aligned with MCP best practices
// This is a placeholder; extend as needed for publishing.
// See: https://modelcontextprotocol.io/ and https://gofastmcp.com/

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'MCP OCI',
  url: 'https://example.com',
  baseUrl: '/',
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  presets: [
    [
      'classic',
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
};

module.exports = config;

