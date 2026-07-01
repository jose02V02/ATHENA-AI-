import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Athena AI — Il tuo Cervello Digitale',
  description: 'Un assistente AI personale, autonomo, indipendente e locale.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  )
}
