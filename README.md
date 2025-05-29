# Server-Client Benchmarking and Visualization Suite

This project provides tools for running server-client performance tests, collecting statistical data into PostgreSQL, and visualizing results interactively via Tkinter and Matplotlib.

---

## Overview

The suite includes:

- Automated testing of server and clients with different communication modes.
- Storage and retrieval of test statistics using SQL queries.
- Interactive interfaces to view raw data tables and graphical plots.
- Support for various aggregation metrics (average, median, percentiles).

---

## Modules

### main_visual_interface.py

Main interactive console interface.
Allows running test suites, selecting SQL query templates, viewing results as tables, and generating graphical plots.

### graph_matplotlib_tkinter.py

Functions to plot graphs using Matplotlib embedded in Tkinter windows.
Includes scrollbars for navigating wide data ranges and interactive toolbar for zooming and saving.

### db_utils.py

Database helper functions for executing SQL queries and fetching results from PostgreSQL.

### query_loader.py

Manages SQL query templates stored in a JSON file.
Supports listing, loading, and editing templates interactively.

### server_client_maker.py

Contains logic for launching and controlling server and client processes used in benchmarks.

---

## Usage

1. Run the main interface by executing `main_visual_interface.py`.

2. Choose from the menu options to:
   - Run server-client test suite to collect new data.
   - Display data tables from SQL queries.
   - Plot graphs based on aggregated metrics (average, median, percentiles).

3. Customize SQL queries by editing JSON templates to tailor data views.

---

## Requirements

- Python 3.13+
- PostgreSQL server accessible with proper credentials
- Required Python packages (install via Poetry or pip):
  - tkinter
  - matplotlib
  - numpy
  - psycopg2 (or equivalent PostgreSQL driver)

---

## Development Notes

- Tables are loaded incrementally in batches to keep UI responsive.
- Graphs support horizontal scrolling to accommodate large X-axis ranges.
- Aggregation modes can be extended by modifying plotting functions.

---

## License

*(Add license info here)*

---

## Contact

For questions or contributions, please contact Knarg.
