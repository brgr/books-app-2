# Books Frontend

A minimalist Vue 3 frontend for managing your book collection. Designed with a clean, linkding-inspired aesthetic.

## Features

- User authentication (login/register)
- Browse books with pagination
- Add, edit, and delete books
- Track reading status (Want to read, Started, Finished, Abandoned)
- Filter books by reading status
- Search books by title or author
- Simple, clean UI with focus on readability

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe development
- **Vue Router** - Client-side routing
- **Axios** - HTTP client for API requests
- **Vite** - Fast build tool

## Project Structure

```
src/
├── api/              # API client and type definitions
│   ├── auth.ts       # Authentication functions
│   ├── books.ts      # Book API functions
│   ├── client.ts     # Axios client configuration
│   └── types.ts      # TypeScript type definitions
├── components/       # Reusable Vue components
│   ├── BookCard.vue
│   ├── BookFormModal.vue
│   └── NavigationBar.vue
├── views/            # Page components
│   ├── BooksView.vue
│   └── LoginView.vue
├── router/           # Vue Router configuration
│   └── index.ts
├── App.vue           # Root component
├── main.ts           # Application entry point
└── style.css         # Global styles
```

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. Configure the API URL in `.env`:
   ```
   VITE_API_URL=http://localhost:8000
   ```

## Development

Run the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Building for Production

Build the application:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## API Configuration

The frontend uses HTTP Basic Authentication to communicate with the backend API. Credentials are stored in localStorage for persistence across sessions.

### API Endpoints Used

- `POST /register` - Register new user
- `GET /users/me` - Get current user info
- `GET /books` - List books (with pagination)
- `POST /books` - Create new book
- `GET /books/{id}` - Get book details
- `PUT /books/{id}` - Update book
- `DELETE /books/{id}` - Delete book
- `PUT /books/{id}/status` - Set reading status
- `DELETE /books/{id}/status` - Remove reading status

## Design Philosophy

This frontend follows a minimalist design approach inspired by linkding:

- **Clean UI** - Focused on readability and simplicity
- **Minimal Color Palette** - Neutral grays with purple accent
- **Whitespace** - Generous spacing for visual clarity
- **Simple Typography** - System fonts, clear hierarchy
- **Card-based Layout** - Each book displayed in a clean card
- **Responsive** - Works well on mobile and desktop

## Browser Support

Modern browsers with ES6+ support:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
