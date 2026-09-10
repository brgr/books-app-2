# End-to-end tests

Full-stack Playwright suite.

## Running

```sh
npm install
npx playwright install chromium
npm run typecheck
npm run test:e2e
```

Both this project and the Vue frontend use TypeScript 6 until `vue-tsc` and
`typescript-eslint` support TypeScript 7.
