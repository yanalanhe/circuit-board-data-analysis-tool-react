import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Data Analysis Copilot',
  description: 'AI-powered data analysis tool for circuit board datasets',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  )
}
