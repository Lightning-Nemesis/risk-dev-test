# Client

Vue 3 front end, served by Vite, that talks to the Flask API in `server/`.

## Run

From the `client` folder:

```bash
npm install
npm run dev
```

Open http://localhost:5173. The server must be running too, or the page shows an error instead of data.

If port 5173 is busy, see "If a port is already in use" in the main README.

## Settings (`.env`)

| Variable | Value | Used for |
|---|---|---|
| `API_URL` | `http://127.0.0.1:5001` | Where Vite forwards `/api` requests. Read in `vite.config.js` only, never sent to the browser. |
| `VITE_APP_TITLE` | `Price Observation Data Entry` | Page title and heading |
| `VITE_CURRENCY` | `USD` | Currency for displaying prices (task 6). Display only: prices are not converted |

Only variables that start with `VITE_` reach browser code, as `import.meta.env.VITE_...`. Restart `npm run dev` after editing `.env`.

## How the client reaches the server

```
Browser -> Vite dev server (localhost:5173) -> Flask API (API_URL)
```

The browser only ever talks to `localhost:5173`. Requests to `/api/...` are forwarded to the Flask API, so every request in `src/api.js` uses a path starting with `/api`.

## Adding packages

Install packages with `npm install --save-exact <package>`. This records the exact version in `package.json` and `package-lock.json`, so submit both files. To check, run `npm ls --depth=0`: nothing should be marked `extraneous`.

## Files

| File | Purpose |
|---|---|
| `index.html` | Page shell |
| `vite.config.js` | Dev server settings and the `/api` forwarding |
| `src/main.js` | Starts the Vue app |
| `src/App.vue` | Page layout; loads the data |
| `src/api.js` | Requests to the Flask API |
| `src/format.js` | How prices, dates and times are shown: currency from `VITE_CURRENCY`, dates as MM/DD/YYYY, Added On in the viewer's time zone |
| `src/components/` | `ObservationForm`, `ObservationGraph` and `ObservationTable` |
| `src/assets/` | Styles |
| `Dockerfile` | Container image for the client |
