# Publisher Command Center

**Publisher Command Center** is a web-based application designed to help publishers manage and track their content.

## Features

- **Mithril.js** for lightweight and efficient UI rendering
- **Bootstrap** for responsive and consistent styling
- **FontAwesome** for scalable vector icons
- **Vite** for a fast development build system
- **FastAPI** as the backend framework

## Getting Started

### Prerequisites

Ensure you have the following installed:

- [Node.js](https://nodejs.org/) (for frontend development)
- [Python](https://www.python.org/) (for backend development)
- [uv](https://github.com/astral-sh/uv) (for running backend server)

### Installation

Clone the repository and install dependencies:

```sh
npm install
uv sync
```

### Running the Development Server

Start the frontend development server:

```sh
npm run preview
```

Start the backend development server:

```sh
npm run server
```

Start the watcher to enable continuous rebuilds of the frontend:

```sh
npm run watch
```



### Building for Production

To build the frontend for production:

```sh
npm run build
```

## Technologies Used

### [Mithril.js](https://mithril.js.org/)

Mithril.js is a modern client-side JavaScript framework that focuses on simplicity and performance. It is lightweight (~10kb gzipped) and offers a virtual DOM implementation for efficient rendering.

### [Bootstrap](https://getbootstrap.com/)

Bootstrap is a popular CSS framework that helps create responsive and mobile-first designs with prebuilt components and utilities.

### [FontAwesome](https://fontawesome.com/)

FontAwesome provides scalable vector icons and social logos that can be used in web applications.

### [Date-fns](https://date-fns.org/)

Date-fns is a modern JavaScript date utility library that provides comprehensive, yet simple-to-use functions for date manipulation.

### [Filesize.js](https://filesizejs.com/)

Filesize.js is a small utility for formatting file sizes in human-readable formats.

### [Vite](https://vitejs.dev/)

Vite is a next-generation frontend tooling system that enables fast build times and instant development server start-up.

### [SASS](https://sass-lang.com/)

SASS (Syntactically Awesome Stylesheets) is a CSS preprocessor that extends CSS with features like variables, nested rules, and mixins.

### [FastAPI](https://fastapi.tiangolo.com/)

FastAPI is a modern web framework for building APIs with Python 3.7+ that provides automatic OpenAPI and JSON Schema documentation.

## Code Formatting

This project uses **Prettier** for consistent code formatting. Run the following command to format your code:

```sh
npx prettier --write .
```
