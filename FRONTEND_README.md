# Data Analysis Copilot - Frontend

A modern, type-safe Next.js frontend for circuit board data analysis powered by AI.

## Quick Start

### Prerequisites
- Node.js 18+ LTS
- npm 8+

### Installation

```bash
npm install
```

### Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser. The page will auto-update when you make changes (HMR enabled).

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   └── globals.css         # Global styles
├── components/             # React components
│   └── ui/                 # shadcn/ui components
├── hooks/                  # Custom React hooks
├── lib/                    # Utility functions
├── types/                  # TypeScript type definitions
└── styles/                 # Additional stylesheets
```

## Tech Stack

- **Framework:** Next.js 14 with React 18
- **Language:** TypeScript 5.3 (strict mode)
- **Styling:** Tailwind CSS 3.4
- **Components:** shadcn/ui
- **Code Quality:** ESLint, Prettier

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Create production build
- `npm start` - Run production build
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

## Architecture

This frontend is designed to work with the Python FastAPI backend running on `http://localhost:8000`.

### Key Patterns

- **Client-Side Rendering:** No SSR required for MVP
- **Component Structure:** Feature-based components in `src/components/`
- **Type Safety:** Strict TypeScript for compile-time error catching
- **API Communication:** REST API via custom `useApi` hook (Story 2.3)

## Next Steps

- Story 2.2: Implement four-panel layout
- Story 2.3: Create API client hook for backend communication
- Story 3.1+: Add data input and analysis features

## Documentation

See the project architecture and PRD in `_bmad-output/planning-artifacts/` for complete specifications.
