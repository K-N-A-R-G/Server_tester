# graph_matplotlib_tkinter.py

import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk

from db_utils import get_from_base
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,\
 NavigationToolbar2Tk
from query_loader import get_query
from tkinter import ttk, TclError


def make_table(query_name: str | None) -> None:
    """
    Create a Tkinter window displaying a table with query results.

    Args:
        query_name (str): Name of the SQL query template to execute.
                          Defaults to 'basic_stats'.

    Behavior:
        - Retrieves SQL query and metadata from templates.
        - Executes the query and fetches columns and rows.
        - Opens a new Tkinter Toplevel window with a Treeview widget.
        - Displays the results with headers centered.
        - Inserts rows incrementally in batches of 50 to keep UI responsive.
        - Handles window closure gracefully if user closes before all rows loaded.
    """
    # Fetch title, query text, and optional custom headers for the template
    title_, query, custom_headers = get_query(query_name)
    # Execute query and retrieve columns and rows from database
    columns, rows = get_from_base(query)

    if not query:
        print(f"Query '{query_name}' not found.")
        return
    print('Processing...\n')
    # Use custom headers if provided and length matches columns,
    # otherwise use columns
    headers = custom_headers if custom_headers and\
     len(custom_headers) == len(columns) else columns

    # Create a new top-level window for the table
    root = tk.Toplevel()
    root.title(title_)
    tree = ttk.Treeview(root, columns=columns, show="headings")
    tree.pack(fill=tk.BOTH, expand=True)

    # Configure columns: set heading text and center alignment
    for col, head in zip(columns, headers):
        tree.heading(col, text=head, anchor="center")
        tree.column(col, anchor="center")

    def insert_rows(index=0):
        """
        Insert rows into the Treeview widget incrementally in batches.

        Args:
            index (int): Starting index of rows to insert.
        """
        try:
            for _ in range(50):  # Insert 50 rows per call to avoid freezing UI
                if index >= len(rows):
                    return
                tree.insert("", "end", values=rows[index])
                index += 1
            # Schedule next batch insertion after 1 millisecond
            root.after(1, insert_rows, index)
        except TclError:
            print("\033[3;31mWinow closed manually before table complete")

    # Start inserting rows after the window is ready
    root.after(0, insert_rows)


def plot_line_multi_metric(mode='avg'):
    """
    Plot line charts with multiple metrics aggregated by groups.

    Parameters:
        mode (str): Aggregation mode for Y values.
            - 'avg' (default): mean
            - 'median': median
            - 'pNN': percentile, where NN is an integer (e.g., 'p90' for 90th percentile)

    This function fetches data from the database, groups it by the first column,
    aggregates metrics by X values, and plots the results using matplotlib embedded in a Tkinter window.
    The X-axis supports horizontal scrolling.

    The expected data format has at least three columns:
    - group identifier (str or int)
    - x-axis value (numeric)
    - one or more numeric metrics to aggregate and plot
    """
    title_, query, headers_ = get_query('raw_stats')
    columns, rows = get_from_base(query)

    if len(columns) < 3:
        print("Minimum 3 columns required: group, x, [y1, y2...]")
        return
    print('Processing...\n')

    # Organize data by group: {group: [(x, (metric1, metric2, ...)), ...]}
    data = {}
    for row in rows:
        group = row[0]
        x = row[1]
        metrics = row[2:]
        data.setdefault(group, []).append((x, metrics))

    # Create the main Tkinter window
    win = tk.Tk()
    win.title(title_)

    # X-axis limits and ticks setup
    limits = (64, 4097, 64)
    num_ticks = (limits[1] - limits[0]) // limits[2]
    max_label_len = len(str(limits[1]))
    scale = 0.14
    fig_width = num_ticks * max_label_len * scale

    # Create matplotlib figure and axes
    fig, ax = plt.subplots(figsize=(fig_width, 5))

    # Plot each group's aggregated metrics
    for group, points in data.items():
        grouped: dict[int, list[tuple[float, ...]]] = {}

        # Creating X axis by clients_total
        for x_val, metric_tuple in points:
            grouped.setdefault(x_val, []).append(metric_tuple)

        # For each metric column, calculate aggregation per X and plot
        for i, metric_name in enumerate(headers_[2:]):
            x_vals = []
            y_vals = []

            for x, metric_list in sorted(grouped.items()):
                vals = [m[i] for m in metric_list]
                if not vals:
                    continue
                if mode == 'median':
                    y = np.median(vals)
                elif mode.startswith('p') and mode[1:].isdigit():
                    y = np.percentile(vals, int(mode[1:]))
                else:
                    y = np.mean(vals)

                x_vals.append(x)
                y_vals.append(y)

        ax.plot(x_vals, y_vals, marker='o', label=f"{group} – {metric_name}")

    # Set X-axis ticks and limits to avoid empty space before first tick
    ax.set_xticks(list(range(64, 4097, 64)))
    ax.set_title(title_)
    ax.set_xlabel(headers_[1])
    ax.set_ylabel(headers_[2])
    ax.set_xlim(60, 4096)
    ax.grid(True)
    ax.legend()
    fig.tight_layout()

    # Setup Tkinter Canvas with horizontal scrollbar for scrolling the plot
    canvas_frame = tk.Frame(win)
    canvas_frame.pack(fill=tk.BOTH, expand=True)

    x_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
    x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    plot_canvas = tk.Canvas(canvas_frame, xscrollcommand=x_scrollbar.set)
    plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    x_scrollbar.config(command=plot_canvas.xview)

    # Embed matplotlib figure into Tkinter Canvas
    figure_canvas = FigureCanvasTkAgg(fig, master=plot_canvas)
    figure_widget = figure_canvas.get_tk_widget()

    plot_canvas.create_window((0, 0), window=figure_widget, anchor='nw')

    # Adjust scrollable region
    figure_widget.update_idletasks()
    plot_canvas.config(scrollregion=plot_canvas.bbox("all"))

    # zoom, scroll, save
    toolbar = NavigationToolbar2Tk(figure_canvas, win)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    # Close button
    btn_close = tk.Button(win, text="Close", command=win.destroy)
    btn_close.pack(pady=5)
    win.mainloop()


def group_summary_by_server(
    rows: list[tuple[str, int, int, int]]
) -> dict[str, list[tuple[int, int, int]]]:
    """
    Группирует строки вида:
        (server_type, clients_total, full_success, half_success)
    в словарь:
        { server_type: [(clients_total, full, half), ...] }

    Args:
        rows: результат SQL-запроса client_success_summary

    Returns:
        dict[str, list[tuple[int, int, int]]]
    """
    result = {}
    for server, total, full, half in rows:
        result.setdefault(server, []).append((total, full, half))
    return result



def show_client_success_diagram(server_type: str,
 wave_data:list[tuple[int, int, int]]) -> None:
    """
    Display a stacked bar chart (success distribution) per clients_total
    for a given server.

    Each bar shows counts of:
    - full_success (2 successful exchanges)
    - half_success (1 success)
    - fail (calculated as total - full - half)

    Args:
        server_type: Server type, criterium of filtering (used as window title)
        wave_data: List of (clients_total, full_success, half_success)
    """
    wave_data.sort(key=lambda x: x[0])  # Sort by clients_total

    # Prepare data
    labels = []
    full = []
    half = []
    fail = []

    for total, full_ok, half_ok in wave_data:
        fail_count = total - full_ok - half_ok
        labels.append(str(total))
        full.append(full_ok)
        half.append(half_ok)
        fail.append(fail_count)

    x = list(range(len(labels)))

    # Auto figure width
    max_label_len = len(str(wave_data[-1][0]))
    scale = 0.14
    fig_width = max(6, len(labels) * max_label_len * scale)

    # Create main window
    win = tk.Tk()
    win.title(f"Client Success Diagram – {server_type}")

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(fig_width, 5))
    ax.bar(x, fail, label="Fail (0)", color="red")
    ax.bar(x, half, bottom=fail, label="Partial (1)", color="gold")
    ax.bar(x, full, bottom=[f + h for f, h in zip(fail, half)], label="Success (2)", color="green")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45)
    ax.set_xlabel("Clients per wave")
    ax.set_ylabel("Number of clients")
    ax.set_title(f"Client Success Distribution – {server_type}")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()

    # Scrollable canvas
    canvas_frame = tk.Frame(win)
    canvas_frame.pack(fill=tk.BOTH, expand=True)

    x_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
    x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    plot_canvas = tk.Canvas(canvas_frame, xscrollcommand=x_scrollbar.set)
    plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    x_scrollbar.config(command=plot_canvas.xview)

    # Embed figure
    figure_canvas = FigureCanvasTkAgg(fig, master=plot_canvas)
    figure_widget = figure_canvas.get_tk_widget()
    plot_canvas.create_window((0, 0), window=figure_widget, anchor='nw')

    figure_widget.update_idletasks()
    plot_canvas.config(scrollregion=plot_canvas.bbox("all"))

    # Toolbar
    toolbar = NavigationToolbar2Tk(figure_canvas, win)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    # Close button
    btn_close = tk.Button(win, text="Close", command=win.destroy)
    btn_close.pack(pady=5)

    win.mainloop()


def prepare_max_wave_summary() -> dict[str, tuple[int, str | None]]:
    """
    Prepare a summary of max clients_total reached by each server_type,
    along with a possible fatal error message from server_log.

    Returns:
        dict: {server_type: (max_clients_total, error_message_or_None)}
    """
    try:
        # Get query for max wave
        title1, query1, _ = get_query("server_max_wave")
        columns1, rows1 = get_from_base(query1)
    except Exception as ex:
        print("Error while reading max wave:", ex)
        return {}

    try:
        # Get all fatal errors
        query2 = "SELECT server_type, message FROM server_log"
        columns2, rows2 = get_from_base(query2)
        errors = {row[0]: row[1] for row in rows2}
    except Exception as ex:
        print("Error while reading server_log:", ex)
        errors = {}

    try:
        summary = {}
        for row in rows1:
            server_type = row[0]
            max_clients = row[1]
            error_msg = errors.get(server_type)
            summary[server_type] = (max_clients, error_msg)
        return summary
    except Exception as ex:
        print("Error while building summary:", ex)
        return {}


def plot_max_clients_per_server() -> None:
    """
    Display a bar chart showing the highest clients_total each server processed before failing or completing.

    Parameters:
        summary (dict): Mapping of server_type to a tuple:
            - max_clients (int): the last wave reached by the server
            - error_message (str or None): reason of failure, or None if not failed
    """
    summary: dict[str, tuple[int, str | None]] = prepare_max_wave_summary()

    # Sort by value descending
    items = sorted(summary.items(), key=lambda x: x[1][0], reverse=True)
    labels = [srv for srv, _ in items]
    values = [info[0] for _, info in items]
    messages = [info[1][:40] + '...' if info[1]\
     else f'{chr(10003)} OK' for _, info in items]

    # Auto figure width
    max_label_len = max(map(len, labels))
    scale = 0.15
    fig_width = max(6, len(labels) * max_label_len * scale)

    win = tk.Tk()
    win.title("Max Clients per Server")

    fig, ax = plt.subplots(figsize=(fig_width, 5))
    bars = ax.bar(labels, values, color='skyblue')

    ax.set_ylabel("Clients total")
    ax.set_title("Wave on which each server stopped or completed")
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Add labels above bars
    for bar, msg in zip(bars, messages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 20, msg,
                ha='center', va='bottom', fontsize=8, rotation=45)

    fig.tight_layout()

    # Embed in scrollable canvas
    canvas_frame = tk.Frame(win)
    canvas_frame.pack(fill=tk.BOTH, expand=True)

    x_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
    x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    plot_canvas = tk.Canvas(canvas_frame, xscrollcommand=x_scrollbar.set)
    plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    x_scrollbar.config(command=plot_canvas.xview)

    figure_canvas = FigureCanvasTkAgg(fig, master=plot_canvas)
    figure_widget = figure_canvas.get_tk_widget()
    plot_canvas.create_window((0, 0), window=figure_widget, anchor='nw')

    figure_widget.update_idletasks()
    plot_canvas.config(scrollregion=plot_canvas.bbox("all"))

    toolbar = NavigationToolbar2Tk(figure_canvas, win)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    btn_close = tk.Button(win, text="Close", command=win.destroy)
    btn_close.pack(pady=5)

    ax.set_ylim(0, max(values) * 1.15)

    win.mainloop()


def plot_avg_response_per_server(mode: str = 'mean') -> None:
    """
    Display a bar chart comparing average response time per server_type.

    Parameters:
        mode (str): Aggregation method for time values.
            - 'mean': average
            - 'median': median
            - 'pNN': percentile (e.g., 'p90', 'p99')
    """
    try:
        title_, query, headers_ = get_query('raw_stats')
        columns, rows = get_from_base(query)
    except Exception as ex:
        print("Error fetching data:", ex)
        return

    try:
        # Group response times by server_type
        data: dict[str, list[float]] = {}
        for row in rows:
            server_type = row[0]
            t_response = row[3]
            if t_response is not None:
                data.setdefault(server_type, []).append(t_response)

        # Aggregate according to mode
        summary: dict[str, float] = {}
        for srv, values in data.items():
            if not values:
                continue
            if mode == 'median':
                summary[srv] = float(np.median(values))
            elif mode.startswith('p') and mode[1:].isdigit():
                summary[srv] = float(np.percentile(values, int(mode[1:])))
            else:
                summary[srv] = float(np.mean(values))

        # Prepare data
        labels = list(summary.keys())
        values = list(summary.values())
        max_label_len = max(map(len, labels))
        scale = 0.14
        fig_width = max(6, len(labels) * max_label_len * scale)

        # Create window
        win = tk.Tk()
        win.title(f"Average response time per server ({mode})")

        fig, ax = plt.subplots(figsize=(fig_width, 5))
        bars = ax.bar(labels, values, color='mediumseagreen')
        ax.set_ylabel("Response time (seconds)")
        ax.set_title(f"Server response time aggregated by {mode}")
        ax.grid(axis='y', linestyle='--', alpha=0.5)

        # Label each bar
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + height * 0.03,
                    f"{val:.6f}", ha='center', va='bottom', fontsize=8)

        ax.set_ylim(0, max(values) * 1.15)
        fig.tight_layout()

        # Scrollable canvas
        canvas_frame = tk.Frame(win)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        x_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        plot_canvas = tk.Canvas(canvas_frame, xscrollcommand=x_scrollbar.set)
        plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        x_scrollbar.config(command=plot_canvas.xview)

        figure_canvas = FigureCanvasTkAgg(fig, master=plot_canvas)
        figure_widget = figure_canvas.get_tk_widget()
        plot_canvas.create_window((0, 0), window=figure_widget, anchor='nw')

        figure_widget.update_idletasks()
        plot_canvas.config(scrollregion=plot_canvas.bbox("all"))

        toolbar = NavigationToolbar2Tk(figure_canvas, win)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_close = tk.Button(win, text="Close", command=win.destroy)
        btn_close.pack(pady=5)

        win.mainloop()

    except Exception as ex:
        print("Error during visualization:", ex)
