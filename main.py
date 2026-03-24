import uiautomator2 as u2
import threading
import time
import datetime
import os
from abdinstall import ADBAutoInstaller, ensure_adb

# os.geteuid = lambda: 0
from pynput import keyboard
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
installer = ADBAutoInstaller()
check_abd = installer.check_adb()

import os
import sys

def restart_program():
    """Zamyka obecny program i uruchamia go ponownie."""
    python = sys.executable
    os.execl(python, python, *sys.argv)


if not check_abd:
    if not installer.run():
        exit(1)
    restart_program()
# Funkcja pobierająca listę podłączonych telefonów z ADB
@ensure_adb
def get_connected_devices():
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]
    devices = [line.split('\t')[0] for line in lines if line.endswith('\tdevice')]
    return devices


DEVICES = {}
serials = get_connected_devices()

for index, serial in enumerate(serials):
    klawisz = str(index + 1)
    DEVICES[klawisz] = serial
    subprocess.run(['python', '-m', 'uiautomator2', 'init', '--serial', serial])

if not DEVICES:
    print("❌ Nie wykryto żadnych telefonów! Upewnij się, że są podłączone i mają włączone debugowanie USB.")
    exit()

# Słownik przechowujący statusy
PHONE_STATUSES = {}
STATUS_LOCK = threading.Lock()
STOP_PROGRAM = threading.Event()


def init_statuses():
    with STATUS_LOCK:
        for key in DEVICES.keys():
            PHONE_STATUSES[key] = {
                "status": "oczekuje",
                "serial": DEVICES[key][:20]
            }


init_statuses()


def update_status(key, status):
    with STATUS_LOCK:
        if key in PHONE_STATUSES:
            PHONE_STATUSES[key]["status"] = status


class PhoneWorker:
    def __init__(self, key, serial):
        self.key = key
        self.serial = serial
        self.d = u2.connect(serial)
        self.is_busy = False
        self.lock = threading.Lock()

    def start_sequence(self):
        if self.is_busy:
            return
        threading.Thread(target=self._run_sequence, daemon=True).start()
    def check_date(self,date):
        cur_date = datetime.datetime.now()
        print(cur_date.year, cur_date.month, cur_date.day)

        if date!="Data zakupu":
            print(date)
            print("ok")
            ddate = datetime.datetime.strptime(date, "%d-%m-%Y")
            print(ddate.year, ddate.month, ddate.day)
            if cur_date.year == ddate.year and cur_date.month == ddate.month:
                return True
        return False

    def _run_sequence(self):
        with self.lock:
            self.is_busy = True
            max_attempts = 3
            success = False

            for attempt in range(1, max_attempts + 1):
                update_status(self.key, f"próba {attempt}")

                try:
                    self.d(resourceId="pl.primesoft.mrreceipt:id/main_fab").click()
                    self.d(resourceId="pl.primesoft.mrreceipt:id/efab_option_1").click()
                    self.d(resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/capture_button").click()

                    found_screen = False
                    for _ in range(20):
                        if self.d(
                                resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/save_document_button").exists:
                            self.d(
                                resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/save_document_button").click()
                            found_screen = True
                            break

                        if self.d(
                                resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/confirm_crop_button").exists:
                            self.d(
                                resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/confirm_crop_button").click()
                            self.d(
                                resourceId="com.google.android.gms.optional_mlkit_docscan_ui:id/save_document_button").click()
                            found_screen = True
                            break

                        time.sleep(0.2)

                    if not found_screen:
                        continue

                    date = self.d(resourceId="pl.primesoft.mrreceipt:id/purchase_date_text_input_layout").child(
                        className="android.widget.EditText").get_text()
                    price = self.d(resourceId="pl.primesoft.mrreceipt:id/price_value_layout").child(
                        className="android.widget.EditText").get_text()

                    is_loaded = (price != "Kwota") and self.check_date(date)
                    print(is_loaded)

                    if is_loaded:
                        self.d(resourceId="pl.primesoft.mrreceipt:id/action_accept").click()
                        update_status(self.key, "ok")
                        success = True
                        break
                    else:
                        # time.sleep(2)
                        self.d(description="Przejdź wyżej").click()
                        self.d(resourceId="android:id/button2").click()

                except Exception as e:
                    pass

            if not success:
                update_status(self.key, "błąd")

            # time.sleep(1)
            # if not success:
            #     time.sleep(2)

            # update_status(self.key, "oczekuje")
            self.is_busy = False


# Inicjalizacja workerów
workers = {}
for key, serial in DEVICES.items():
    try:
        workers[key] = PhoneWorker(key, serial)
    except Exception as e:
        print(f"Nie udało się połączyć z urządzeniem {key}: {e}")


class StatusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📱 AutoParagon - Status Telefonów")
        self.root.geometry("500x400")
        self.root.configure(bg='#2b2b2b')

        # Nagłówek
        header = tk.Label(root, text="STATUS TELEFONÓW", font=('Arial', 16, 'bold'),
                          bg='#2b2b2b', fg='white')
        header.pack(pady=10)

        # Instrukcja
        instrukcja = tk.Label(root, text="Klawisze: 1,2,3... = telefon | a = wszystkie | ESC = wyjście",
                              font=('Arial', 10), bg='#2b2b2b', fg='#aaaaaa')
        instrukcja.pack(pady=5)

        # Ramka z tabelą
        frame = tk.Frame(root, bg='#2b2b2b')
        frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        # Treeview (tabela)
        columns = ('klawisz', 'serial', 'status')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)

        self.tree.heading('klawisz', text='Klawisz')
        self.tree.heading('serial', text='Serial')
        self.tree.heading('status', text='Status')

        self.tree.column('klawisz', width=80, anchor='center')
        self.tree.column('serial', width=200, anchor='w')
        self.tree.column('status', width=150, anchor='center')

        # Styl
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview", background='#3b3b3b', foreground='white',
                        fieldbackground='#3b3b3b', rowheight=30)
        style.configure("Treeview.Heading", background='#4b4b4b', foreground='white')

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Inicjalne wypełnienie
        self.update_table()

        # Start odświeżania
        self.refresh_loop()

        # Obsługa klawiatury
        self.setup_keyboard()

    def get_status_color(self, status):
        colors = {
            "oczekuje": "#ffffff",
            "próba 1": "#ffff00",
            "próba 2": "#ffff00",
            "próba 3": "#ffa500",
            "błąd": "#ff4444",
            "ok": "#00ff00"
        }
        return colors.get(status, "#ffffff")

    def update_table(self):
        # Wyczyść tabelę
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Dodaj wiersze
        with STATUS_LOCK:
            for key in sorted(PHONE_STATUSES.keys()):
                data = PHONE_STATUSES[key]
                status = data["status"]

                emoji = {
                    "oczekuje": "⏳",
                    "próba 1": "🔄",
                    "próba 2": "🔄",
                    "próba 3": "🔄",
                    "błąd": "❌",
                    "ok": "✅"
                }.get(status, "⏳")

                item = self.tree.insert('', tk.END, values=(
                    f"[{key}]",
                    data["serial"],
                    f"{emoji} {status}"
                ))

                # Kolorowanie wiersza
                color = self.get_status_color(status)
                self.tree.tag_configure(status, background='#3b3b3b', foreground=color)
                self.tree.item(item, tags=(status,))

    def refresh_loop(self):
        self.update_table()
        self.root.after(250, self.refresh_loop)  # Odświeżaj co 250ms

    def setup_keyboard(self):
        """Bindowanie klawiszy bezpośrednio w tkinter (działa pod Windows)"""

        # Bind klawiszy numerycznych
        for key in workers.keys():
            self.root.bind(f"<Key-{key}>", lambda event, k=key: self.on_key_press(k))
            # Dla klawisza 'a' lub 'A'
        self.root.bind("<Key-a>", lambda event: self.on_key_press('a'))
        self.root.bind("<Key-A>", lambda event: self.on_key_press('a'))

        # ESC - wyjście
        self.root.bind("<Escape>", lambda event: self.on_exit())

        # Fokus na okno aby klawisze działały od razu
        self.root.focus_set()

    def on_key_press(self, key):
        """Obsługa naciśnięcia klawisza"""
        if key in workers:
            workers[key].start_sequence()
        elif key == 'a':
            for w in workers.values():
                w.start_sequence()
        return "break"  # Zapobiega dalszemu przetwarzaniu
    def on_exit(self):
        """Wyjście z programu"""
        if messagebox.askokcancel("Wyjście", "Czy na pewno chcesz zamknąć program?"):
            self.root.quit()


# Uruchomienie
if __name__ == "__main__":
    root = tk.Tk()
    app = StatusGUI(root)
    root.mainloop()
    print("👋 Program zakończony.")