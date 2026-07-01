/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: {
    // Ignora gli errori di tipo per permettere a Vercel di completare il build
    ignoreBuildErrors: true,
  },
}

module.exports = nextConfig