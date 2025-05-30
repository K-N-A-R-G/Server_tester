# main_visual_interface.py
import multiprocessing
import server_client_maker as scm
import threading
import time
import tkinter as tk

from db_utils import get_from_base
from graph_matplotlib_tkinter import make_table, plot_line_multi_metric,\
 show_client_success_diagram, group_summary_by_server,\
 plot_max_clients_per_server, plot_avg_response_per_server
from query_loader import choose_template, get_query
from typing import Any


def close_windows():
    """
    Close all Tkinter Toplevel windows and exit the main loop.
    """
    for win in root.winfo_children():
        if isinstance(win, tk.Toplevel):
            win.destroy()
    root.quit()


def main():
    """
    Main interactive console interface loop.
    Presents options to run tests, show SQL tables, and plot graphs.
    Starts relevant tasks in threads or separate processes to avoid blocking.
    """
    while True:
        print("\n--- Analitical interface ---")
        print("1. Run test (server + clients)")
        print("2. Show table by SQL query")
        print("3. Make graph")
        print('4. Show diagram')
        print("0. Exit program")
        choice = input("You choice:\n ").strip()

        if choice == '1':
            scm.run_test_suite()
        elif choice == '2':
            # Run table display in a daemon thread
            threading.Thread(target=make_table,
             args=(choose_template(),),
             daemon=True).start()
            time.sleep(2)
        elif choice == '3':
            # Select aggregation mode for plotting
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
            # Run plotting in a separate process to avoid blocking
            multiprocessing.Process(target=plot_line_multi_metric,
             args=(mode,), daemon=True).start()
            time.sleep(2)
        elif choice == '4':
            while True:
                dia_type = input('Select type of diagram:\
\n 1. Server lifetime summary - Show maximum wave (clients_total) reached by\
 each server, with error if any.\
\n 2.Client success distribution (per server) - Select a server and display\
 the ratio of fully/partially/failed connections across all waves\
\n 3. Average server response time - Show average/median/percentile (pNN)\
 response times per server type\n')
                if dia_type:
                    if dia_type == '1':
                        try:
                            multiprocessing.Process(
                             target=plot_max_clients_per_server,
                             daemon=True).start()
                        except Exception as ex:
                            raise
                    elif dia_type == '2':
                        _, query, headers_ =\
                         get_query('client_success_summary')
                        raw_summary: list[tuple[str, int, int, int]] =\
                         get_from_base(query)[1]
                        server_groups = group_summary_by_server(raw_summary)

                        for c, x in enumerate(server_groups.keys(), start=1):
                            print(f'{c}. {x}')
                        srv_type = input('\nNumber? ')
                        if srv_type:
                            try:
                                group_data =\
                                 server_groups[list(server_groups)[int(srv_type) - 1]]
                                multiprocessing.Process(
                                 target=show_client_success_diagram,
                                 args=(list(server_groups)[int(srv_type) - 1],
                                 group_data),
                                 daemon=True).start()
                            except Exception as ex:
                                raise
                    elif dia_type == '3':
                        # Select aggregation mode for diagram
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
                        # Run plotting in a separate process to avoid blocking
                        multiprocessing.Process(
                         target=plot_avg_response_per_server,
                         args=(mode,), daemon=True).start()
                        time.sleep(2)
                    else:
                        print('Cancelled')
                        break
        elif choice == '0':
            # Close all additional windows and quit main loop
            for win in root.winfo_children():
                if isinstance(win, tk.Toplevel):
                    win.destroy()
            root.after(0, close_windows)
            break
        else:
            print("Incorrect input")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main Tk window
    threading.Thread(target=main, daemon=True).start()
    root.mainloop()
