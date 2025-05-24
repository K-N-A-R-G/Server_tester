# main_visual_interface.py
import multiprocessing
import server_client_maker as scm
import threading
import tkinter as tk

from db_utils import get_from_base
from query_loader import get_query
from graf_matplotlib_tkinter import draw_metric_grouped_by_server, make_table,\
 plot_line_multi_metric
from query_loader import get_query, list_templates
from db_utils import get_from_base


def choose_template():
    'Select template from list extracted from JSON'
    templates = list_templates()
    print("\nAviable query templates:")
    for i, (name, desc) in enumerate(templates.items(), start=1):
        print(f"{i}. {name} – {desc}")
    print("0. Default query (basic_stats)\nq - exit to previous menu")
    while True:
        selection = input("Select : ").strip()
        try:
            if selection in 'Qq':
                return None
            elif selection == '0':
                name = 'basic_stats'
            else:
                index = int(selection) - 1
                name = list(templates.keys())[index]
        except Exception:
            print("Wrong choise.")
            continue

        if not name:
            continue
        return name


def extract_metric_from_query(query: str) -> str | None:
    import re
    # Пример: SELECT ..., AVG(t_response) AS avg_response ...
    match = re.search(r'AVG\((\w+)\)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def close_windows():
    for win in root.winfo_children():
        if isinstance(win, tk.Toplevel):
            win.destroy()
    root.quit()


def main():
    while True:
        print("\n--- Аналитический интерфейс ---")
        print("1. Запустить новый тест (сервер + клиенты)")
        print("2. Show table by SQL query")
        print("3. Make graph")
        print('4. Reserved for diagram/histogram')
        print("0. Выйти")
        choice = input("Ваш выбор:\n ").strip()

        if choice == '1':
            scm.run_test_suite()
        elif choice == '2':
            threading.Thread(target=make_table, args=(choose_template(),),
             daemon=True).start()
        elif choice == '3':  # график
            mode = input("Choose aggregation type:\n"
             "1. Median\n"
             "2. 90th percentile\n"
             "3. 99th percentile\n"
             "Any other = Average\n> ").strip()
            mode = mode.lower()
            if mode == '1':
                mode = 'median'
            elif mode == '2':
                mode = 'p90'
            elif mode == '3':
                mode = 'p99'
            else:
                mode = 'avg'
            multiprocessing.Process(target=plot_line_multi_metric,
             args=(mode,), daemon=True).start()
        elif choice == '0':
            for win in root.winfo_children():
                if isinstance(win, tk.Toplevel):
                    win.destroy()
            root.after(0, close_windows)
            break
        else:
            print("Неверный ввод")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    threading.Thread(target=main, daemon=True).start()
    root.mainloop()
