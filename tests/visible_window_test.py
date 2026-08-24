import tkinter as tk
import sys

def run_visibility_test():
    print("[VISIBILITY TEST] Python GUI starting")
    
    root = tk.Tk()
    root.title("FB AutoViral - VISIBILITY TEST")
    root.geometry("500x500+100+100")
    
    label = tk.Label(
        root, 
        text="VISIBLE WINDOW TEST", 
        font=("Arial", 20, "bold"),
        fg="white",
        bg="blue",
        padx=20,
        pady=20
    )
    label.pack(expand=True)
    
    print("[VISIBILITY TEST] Window created")
    print("[VISIBILITY TEST] Waiting for manual close")
    
    root.mainloop()

if __name__ == "__main__":
    run_visibility_test()
