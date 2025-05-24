# graf_matplotlib_tkinter.py

import matplotlib.pyplot as plt
import numpy as np
import sqlite3
import tkinter as tk

from db_utils import get_from_base
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,\
 NavigationToolbar2Tk
from matplotlib.ticker import MaxNLocator
from query_loader import get_query
from tkinter import ttk, TclError


def make_table(query_name: str = 'basic_stats') -> None:

    # Создание таблицы
    # Получаем названия и строки
    title_, query, custom_headers = get_query(query_name)
    columns, rows = get_from_base(query)
    if not query:
        print(f"Query '{query_name}' not found.")
        return
    headers = custom_headers if custom_headers and\
     len(custom_headers) == len(columns) else columns
    # Настройка GUI
    root = tk.Toplevel()
    root.title(title_)
    tree = ttk.Treeview(root, columns=columns, show="headings")
    tree.pack(fill=tk.BOTH, expand=True)

    for col in columns:
        tree.heading(col, text=col, anchor="center")
        tree.column(col, anchor="center")

    def insert_rows(index=0):
        try:
            for _ in range(50):  # вставлять по 50 строк за раз
                if index >= len(rows):
                    return
                tree.insert("", "end", values=rows[index])
                index += 1
            root.after(1, insert_rows, index)
        except TclError:
            print("Окно было закрыто до завершения вставки")

    root.after(0, insert_rows)
    # Запуск интерфейса
    # root.mainloop()


def draw_metric_grouped_by_server(metric: str, title: str) -> None:
    conn = sqlite3.connect("statistics.sqlite")
    cur = conn.cursor()

    query = f'''
        SELECT server_type, clients_total, AVG({metric})
        FROM test
        WHERE {metric} IS NOT NULL
        GROUP BY server_type, clients_total
        ORDER BY server_type, clients_total
    '''
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    server_data: dict[str, list[tuple[int, float]]] = {}

    for server_type, clients_total, avg_value in rows:
        server_data.setdefault(server_type, []).append((clients_total, avg_value))

    plt.figure(figsize=(10, 6))
    for server_type, points in server_data.items():
        x = [p[0] for p in points]
        y = [p[1] for p in points]
        plt.plot(x, y, marker='o', label=server_type)

    plt.title(title)
    plt.xlabel("Количество клиентов")
    plt.ylabel(metric)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_line_multi_metric(mode='avg'):
    title_, query, headers_ = get_query('raw_stats')
    columns, rows = get_from_base(query)

    if len(columns) < 3:
        print("Minimum 3 columns required: group, x, [y1, y2...]")
        return

    data = {}
    for row in rows:
        group = row[0]
        x = row[1]
        metrics = row[2:]
        data.setdefault(group, []).append((x, metrics))

    win = tk.Tk()
    win.title(title_)
    fig, ax = plt.subplots(figsize=(8, 5))

    for group, points in data.items():
        grouped: dict[int, list[tuple[float, ...]]] = {}

        # Creating X axis by clients_total
        for x_val, metric_tuple in points:
            grouped.setdefault(x_val, []).append(metric_tuple)

        # Building agregation on each X point
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

    # for group, points in data.items():
        # p_sort = sorted(points)
        # x_vals = [pt[0] for pt in p_sort]
        # for x in range(len(headers_[2:])):
            # y_vals = [pt[1][x] for pt in p_sort]
            # ax.plot(x_vals, y_vals, marker='o', label=f"{group}")

    ax.set_xticks(list(range(64, 4097, 64)))
    ax.set_title(title_)
    ax.set_xlabel(headers_[1])
    ax.set_ylabel(headers_[2])
    ax.grid(True)
    ax.legend()
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # zoom, scroll, save
    toolbar = NavigationToolbar2Tk(canvas, win)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    # Button
    btn_close = tk.Button(win, text="Close", command=win.destroy)
    btn_close.pack(pady=5)
    win.mainloop()
