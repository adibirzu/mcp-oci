// Minimal Docusaurus config for MCP-OCI, mirroring AWS MCP site structure
// This is a stub to enable local docs preview/build.

 // @ts-nocheck

const config = {
  title: 'MCP-OCI',
  url: 'https://adibirzu.github.io',
  baseUrl: '/mcp-oci/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  organizationName: 'adibirzu',
  projectName: 'mcp-oci',
  trailingSlash: false,
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */ ({
        docs: {
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'MCP-OCI',
      items: [
        { to: '/', label: 'Overview', position: 'left' },
        { to: '/installation', label: 'Installation', position: 'left' },
        { to: '/configuration', label: 'Configuration', position: 'left' },
        { to: '/tools', label: 'Tools/Resources', position: 'left' },
        { to: '/usage', label: 'Usage', position: 'left' },
        { to: '/development', label: 'Development', position: 'left' },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `Copyright © ${new Date().getFullYear()} MCP-OCI`,
    },
  },
};

module.exports = config;
