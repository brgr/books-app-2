# Books Frontend

A Vue 3 frontend for managing your book collection.

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Create a `.env` file (copy from `.env.example`):

   ```bash
   cp .env.example .env
   ```

## Development

Run the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Code Quality

```shell
npm run lint          # Run ESLint
npm run lint:fix      # Run ESLint and fix any errors
npm run format        # Format files with Prettier
npm run format:check  # Check formatting without changing files
npm run typecheck     # Run TypeScript type checking
```

## Building for Production

Build the application:

```bash
npm run build
```
