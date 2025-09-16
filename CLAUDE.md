# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a simple Flask web dashboard application that serves a single-page interface. The project structure is minimal with core Flask functionality and frontend assets for styling and charting.

## Architecture

**Backend (Flask 3.1.2)**
- `app.py` - Main Flask application with single route serving the dashboard
- Runs on port 5001 by default with debug mode enabled
- Uses Flask's built-in template engine with templates in `templates/` directory

**Frontend Assets**
- `static/css/tailwind.min.css` - Tailwind CSS v3.4.1 for styling
- `static/js/chart.min.js` - Chart.js library for data visualizations
- `templates/index.html` - Main dashboard template (currently empty)

**Python Environment**
- Uses Python 3.11.6 with a virtual environment in `.venv/`
- Flask is the only main dependency

## Development Commands

**Setup Environment:**
```bash
source .venv/bin/activate
```

**Run Development Server:**
```bash
python app.py
```
The application runs on http://127.0.0.1:5001 by default.

**Alternative Run Command:**
```bash
python -c "from app import app; app.run(debug=True, port=5002)"
```

## Key Development Notes

- The application uses Flask's debug mode for automatic reloading during development
- Static files (CSS, JS) are served from the `static/` directory
- Templates are served from the `templates/` directory following Flask conventions
- The main dashboard route renders `index.html` template
- The project appears to be in early development stage with empty template file