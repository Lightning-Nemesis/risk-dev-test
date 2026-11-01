# Beneficient Risk Developer Coding Test

This repo contains a coding test for potential risk developers: a small app for entering price observations and charting them. It has two parts:

| Folder | What it is |
|---|---|
| `server/` | Flask REST API and the Python data logic. See `server/README.md`. |
| `client/` | Vue 3 front end (built with Vite) that calls the API. See `client/README.md`. |

You are encouraged to use AI-assisted development tools such as Claude Cowork/Code/Design, GitHub Copilot, OpenAI Codex, and others. However, **you are still expected to have a solid understanding of the architecture, underlying business and engineering requirements, issues and gaps you addressed, the code you submitted, and the reasoning behind your design and implementation decisions.**

If you used any AI-assisted development tools, **you must disclose them in the `Disclosures` section at the end of this file.** You must also include the relevant project configuration files in your submission so we can understand how you configured and used these tools. Examples include `CLAUDE.md` and the `.claude/` directory, or the equivalent files and directories for your tool (e.g., `AGENTS.md` or `.cursor/`). **Remove all API keys, access tokens, and other secrets from these files before submitting them.**

Feel free to add comments anywhere in the code.

## Quick start

Docker is optional. Option B runs the app with just Python and Node.js, so if you don't have Docker, skip Option A and start with Option B instead of installing it.

### Option A: Docker

Open the Docker Desktop app first and wait until it shows Docker is running. Then, from the project folder, run:

```bash
docker compose up --build
```

Open http://localhost:5173. Press `Ctrl+C` to stop. If Docker says it can't connect to the Docker daemon, Docker Desktop isn't running yet.

### Option B: Run each part yourself (no Docker needed)

You need Python 3.12, the same version the Docker setup uses, so the packages you freeze install the same way for us. You also need Node.js 22.12+. Open two terminals in the project folder.

**Terminal 1: server**

```bash
cd server
py -3.12 -m venv .venv          # Windows
python3.12 -m venv .venv        # macOS / Linux
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
python app.py
```

Run `python --version` after activating to confirm it shows 3.12. If you use conda instead, run `conda create -n risk-dev-test python=3.12` and `conda activate risk-dev-test` in place of the venv lines.

**Terminal 2: client**

```bash
cd client
npm install
npm run dev
```

Open http://localhost:5173.

| | Address |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:5001/api/observations |

### If a port is already in use

The server uses port 5001 and the client uses 5173. If one is taken, stop the program that's using it, or move the app to another port:

- **Find what's using it:** on Windows, `netstat -ano | findstr :5001`, then end that process ID in Task Manager. On macOS or Linux, `lsof -i :5001`.
- **Server:** change `FLASK_RUN_PORT` in `server/.env`, and use the same port in `API_URL` in `client/.env`.
- **Client:** change `port: 5173` in `client/vite.config.js`.
- **Docker:** change the first number of the port in `compose.yaml`, e.g. `"5002:5001"`. Only the address on your machine changes.

## Project structure

```
risk-dev-test/
├── compose.yaml         Docker setup for both parts
├── server/              Flask REST API (Python)
│   ├── .env             server settings
│   ├── app.py           API routes and input validation
│   ├── cpi.py           Observation model and database access
│   ├── options.json     categories, items, states and cities for the drop-downs (editable)
│   ├── migrate.py       one-off clean-up of the existing rows
│   ├── test_*.py        unit tests (python -m unittest)
│   └── test.db          SQLite database with sample data
└── client/              Vue 3 front end (JavaScript)
    ├── .env             client settings
    ├── vite.config.js   dev server and /api forwarding
    └── src/             App.vue, api.js, format.js, theme.js, components/, assets/, format.test.js (npm test)
```

## Adding categories, items, states and cities

The drop-down choices aren't in the code: they're listed in `server/options.json`. To add or change a category, item, state or city:

1. Edit that file. For example, to add an item to a category, add `{ "name": "Whole Milk, Gallon", "sample_base_price": 3.49 }` to that category's `items`.
2. Refresh the page. In debug mode (the default) the server restarts by itself when the file is saved.

The server checks the file when it starts and names any mistake, such as a missing price or a city listed in two states. See "Editing the options" in `server/README.md` for every field and rule.

## Tasks

Complete these in any order. Keep data transformations (filtering, grouping, averaging) in the server; the client should fetch the results and display them.

1. When the **Save Observation** button is clicked, send the form values to the server through a new API endpoint, store them as a new row in the database, then update the table and the graph.
2. Complete the `Observation.delete_matching` method in `server/cpi.py`, which contains detailed instructions.
3. When the **Delete Matching Observations** button is clicked, call `Observation.delete_matching` through a new API endpoint, then update the database, the table and the graph.
4. When **Graph Type** is set to **Item Prices Over Time**, multiple observations of the same item with the same price should make the point size scale in proportion to the number of matching observations.
5. Implement the **Average Item Price by City** graph type: a grouped bar chart where each bar's height is the average price of an item in a city on the date in the **Date** field. Group the bars by item, and color each bar by the city it applies to:

   ![Grouped bar chart example](grouped_bar.png)

6. `server/.env` and `client/.env` include settings the code doesn't use yet. Use `MAX_PRICE` so the API rejects prices above it, and `VITE_CURRENCY` to display prices as currency in the client.

## Bonus tasks

Add any enhancements that would make the code production quality, for example:

- Make the display (theme, layout, fonts, etc.) more polished and professional/commercial looking. You are encouge to use AI tools like Claude Design.
- Add data validations that make sense for the business logic
- Format data cleanly, in line with American business conventions
- Refactor existing code where it improves readability, extensibility or performance
- Add tests that verify the behavior of your changes
- Document the server and client in `server/README.md` and `client/README.md`: how to run them, the endpoints and components you added, and the decisions you made

List your enhancements in the **Enhancements** section below.

## Grading criteria

- Completion of the tasks and bonus tasks
- Maintainability and readability of the code
- Thoughtful comments and descriptive variable names
- Performance: no noticeable delay when changing graphs or deleting points
- A sensible split of work between the server and the client

## Submitting

Before you zip the project, record every package you used so we can install the same versions:

- **Python:** from `server/`, with the virtual environment active, run `pip freeze > requirements.txt`. If you used conda instead of a venv, run `pip list --format=freeze > requirements.txt`.
- **JavaScript:** add packages with `npm install --save-exact <package>`, which records the exact version in `client/package.json` and `client/package-lock.json`. To check, run `npm ls --depth=0` from `client/`: nothing should be marked `extraneous`.

Then list your enhancements in the **Enhancements** section below, zip the project folder without the `node_modules` and `.venv` folders, and email it to your recruiter, who will send it to us.

## Who do I talk to?

- recruiting@beneficient.com

## Enhancements

All six tasks are done. Beyond them:

**Look and feel**
- The page is redesigned to match `design_sample.png`: a dark header, numbered form steps, and cards. The Plotly charts are styled to match too: fonts, colors, gridlines and legend. It also works on phones.
- Linked drop-downs: Item follows Category, and City follows State.
- A message appears under each invalid field. There are also success messages, a confirmation before deleting, and buttons that can't be double-clicked.
- When the chosen date has no data, the bar chart offers a "Show [latest date]" button.

**Data quality and validation**
- The server checks every field:
  - Date: a real date, not in the future.
  - Item: must belong to the Category. City: must belong to the State.
  - Price: a number above 0 and at most `MAX_PRICE`, rounded to the cent.
- Every problem is reported at once.
- `migrate.py` cleaned the existing rows: one date format, prices rounded to the cent, and "Los Angelos" corrected to "Los Angeles".

**American business formatting**
- Prices in the `VITE_CURRENCY` currency ($4.66), right-aligned in the table.
- Dates as "Jun 29, 2022", and times in the viewer's own time zone.

**Safety**
- Database queries use parameters, and column names are checked against a fixed list, so input can never become SQL.
- `delete_matching` refuses a call with no filter, which would match every row. It also refuses negative counts, because SQLite reads `LIMIT -1` as "no limit".
- Every error comes back as a clear JSON message; internal details stay in the server log.
- Every delete is recorded in the server log.

**Extensibility**
- Categories, items, states and cities live in `server/options.json`, which the server checks at startup. See "Adding categories, items, states and cities" above.

**Performance**
- The table loads only the newest 200 rows, plus the total count. Measured with 75,000 rows, a reload dropped from 687 ms and 18 MB to 58 ms. The charts still use all the data.

**Bugs found and fixed**
- The form's default item didn't exist, so the Item drop-down started blank.
- Running the tests wiped `test.db`. They now use throwaway databases.
- Dates were stored in two formats, so date filters missed rows.
- `Observation.AddedOn` held the server's start time instead of being set when a row is saved.
- The warning for misspelled field names in `Observation(...)` could never fire. It does now.
- JavaScript shows "2022-06-29" as June 28 in US time zones. Dates are now formatted without that conversion.

**Tests**
- 43 server tests (`python -m unittest`) and 8 client tests (`npm test`).
- Many were double-checked by deliberately breaking the code and confirming a test fails.

**Documentation**
- `server/README.md`: endpoints, validation rules, the options file, data clean-up, the delete log, and performance.
- `client/README.md`: files, formatting and tests.

## Key decisions

| Decision | Why |
|---|---|
| The server does all counting, averaging and grouping; the browser only formats and draws | The task asks for it, and it keeps the data rules in one place |
| The server checks every field and reports all problems at once | Anyone can call the API without the page, so the server has to be the gatekeeper. Users fix everything in one go |
| Delete matches the form's Date, Category, Item, State and City, plus Price only if one is typed | These are the form's fields. Stored prices include cents, so matching on price only makes sense when asked for |
| "Most recent first" goes by when rows were added; unchecked means oldest first | All matching rows already share one date. Deleting must be predictable, so ties go by the order rows were added |
| A dot's **area** grows with the number of identical observations (same item, date and price) | People judge circles by area, and item + date + price is exactly one point on the chart |
| The bar chart follows the form's Date | The task asks for it. When that date has no data, it offers the latest date that has some (the sample data is from June 2022) |
| Prices are stored in dollars, rounded to the cent | Prices are money, and it makes "same price" meaningful for matching and dot sizes |
| `VITE_CURRENCY` changes only how prices look; nothing is converted | The task asks for display, and stored prices are already in that currency |
| Dates are built from their text; "Added On" is stored in UTC and shown in local time | Reading a plain date in JavaScript shifts it a day earlier in the Americas |
| Options live in `server/options.json`, and a city name may appear in only one state | Adding a category or city is a data change, not a code change. The charts group by city name, so two cities with one name would be merged |
| The table shows the newest 200 rows | Each reload stays fast as data grows. The total is still shown, and the charts still use everything |
| Button labels follow the design: "Add observation" and "Delete matching" | These are the task's Save Observation and Delete Matching Observations buttons |

## Notes for reviewers

- **Tested with Docker** (Option A, Python 3.12 as in `server/Dockerfile`). Run the tests with `docker compose exec server python -m unittest` and `docker compose exec client npm test`.
- **Docker on Windows:** the client's dev server may not notice file edits inside the container. Run `docker compose restart client`, then refresh.
- **`test.db`** holds the original sample data (June 2022), cleaned by `migrate.py`.
- **Known, and left as is:**
  - `npm audit` reports a security advisory in Vite 8.3.2, the version the project came with (fixed in 8.3.5). It affects only the development server.
  - Flask's debug mode and the Vite dev server are for local development, not production.
  - The fonts load from Google Fonts. Without internet, the page uses system fonts.
  - Renaming an option in `options.json` doesn't rename rows already saved. `migrate.py` shows how to do that.
- **Possible next steps:**
  - Flag prices that are far from the usual for an item and state.
  - Undo after a delete.
  - Filters and CSV export for the table.
  - Logins, so the delete log can record who deleted.

## Disclosures

I used **Claude Code** (Anthropic's AI coding assistant, Claude Opus 5.5 model) throughout this project:

- **Understanding:** it read the codebase and the requirements with me, explained the architecture, and found issues in the starting code, such as the mixed date formats and the invalid default item.
- **Planning:** we wrote a step-by-step plan, and a separate Claude review checked it. Its corrections were applied.
- **Building:** Claude wrote the code one step at a time. Where there were options, I made the decisions from choices it laid out, for example the options file, the button labels and which enhancements to add. Each change was explained to me in plain language before moving on.
- **Design:** I made the page design, `design_sample.png`, with **Claude Design**. Claude Code then built it in the existing Vue components and CSS, and styled the Plotly charts to match.
- **Checking:** Claude ran the tests and deliberately broke the code to confirm the tests catch it. It also measured performance and took browser screenshots to compare the page with `design_sample.png`.

**Configuration:** `CLAUDE.md` at the project root holds the guidelines and project rules Claude Code followed. There is no `.claude/` folder, and there are no API keys or secrets in the project.
