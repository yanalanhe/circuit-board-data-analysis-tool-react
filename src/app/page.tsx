'use client'

import React from 'react'
import { SessionProvider } from '@/lib/SessionContext'
import AppLayout from '@/components/AppLayout'

export default function Home() {
  return (
    <SessionProvider>
      <AppLayout />
    </SessionProvider>
  )
}
