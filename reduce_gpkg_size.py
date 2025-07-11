import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox

def vacuum_geopackage(file_path):
    try:
        with sqlite3.connect(file_path) as conn:
            conn.execute("VACUUM")
        return True
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False

def select_and_vacuum_file():
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window

    file_path = filedialog.askopenfilename(
        title="Select a GeoPackage to Vacuum",
        filetypes=[("GeoPackage files", "*.gpkg")]
    )

    if not file_path:
        return  # User cancelled

    success = vacuum_geopackage(file_path)

    if success:
        messagebox.showinfo("Success", f"Vacuumed GeoPackage:\n{file_path}")
    else:
        messagebox.showerror("Error", f"Failed to vacuum:\n{file_path}")

if __name__ == "__main__":
    select_and_vacuum_file()