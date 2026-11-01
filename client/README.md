# Client

Vue 3 front end, served by Vite, that talks to the Flask API in `server/`.

## Run

From the `client` folder:

```bash
npm install
npm run dev
```

Open http://localhost:5173. The server must be running too. If the port is busy, see "If a port is already in use" in the main README.

## Settings (`.env`)

| Variable | Value | Used for |
|---|---|---|
| `API_URL` | `http://127.0.0.1:5001` | Where Vite forwards `/api` requests. Read only in `vite.config.js`, never sent to the browser |
| `VITE_APP_TITLE` | `Price Observation Data Entry` | Page title and heading |
| `VITE_CURRENCY` | `USD` | Currency prices are shown in. Display only: nothing is converted |

Only variables that start with `VITE_` reach the browser. Restart `npm run dev` after editing `.env`. The drop-down choices aren't set here; they come from the server (`server/options.json`).

## How the client reaches the server

```
Browser -> Vite dev server (localhost:5173) -> Flask API (API_URL)
```

The browser only talks to `localhost:5173`. Vite forwards requests to `/api/...` to the Flask API, so every request in `src/api.js` uses a path starting with `/api`.

The client fetches results and presents them. The server does the filtering, grouping and averaging; the client adds formatting, styling and interaction.

## Tests

```bash
npm test
docker compose exec client npm test   # in Docker, from the project root
```

They check how prices, dates and times are shown, in a US time zone where reading `2022-06-29` with `new Date()` would show June 28.

## Adding packages

Install packages with `npm install --save-exact <package>`. This records the exact version in `package.json` and `package-lock.json`, so submit both files. To check, run `npm ls --depth=0`: nothing should be marked `extraneous`.

## Files

| File | Purpose |
|---|---|
| `index.html` | Page shell; loads the Inter and Source Serif 4 fonts from Google Fonts |
| `vite.config.js` | Dev server settings and the `/api` forwarding |
| `src/main.js` | Starts the Vue app |
| `src/App.vue` | Page layout. Loads the data, and shares the form's Date with the graph |
| `src/api.js` | Requests to the Flask API |
| `src/components/` | `ObservationForm` (save and delete), `ObservationGraph` (both charts), `ObservationTable` (newest rows, with "Load more") |
| `src/format.js` | Prices, dates and times for display |
| `src/theme.js` | Series colors shared by the graph and the table |
| `src/assets/main.css` | Styles, with the design's colors and fonts as CSS variables at the top |
| `src/format.test.js` | Tests for `format.js` |
| `Dockerfile` | Container image for the client |
