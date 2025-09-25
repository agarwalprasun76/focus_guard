"""
Simple test for Tkinter popup window.
This script tests whether Tkinter popups work properly on this system.
"""
import tkinter as tk
from tkinter import ttk
import time

def main():
    """Create a simple Tkinter popup window."""
    print("Creating Tkinter window...")
    
    # Create root window
    root = tk.Tk()
    root.title("FocusGuard Test Alert")
    root.geometry("400x200")
    
    # Position at bottom right of screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - 400 - 20
    y = screen_height - 200 - 60
    root.geometry(f"+{x}+{y}")
    
    # Configure window
    root.configure(bg="#e6f0ff")  # Light blue
    
    # Create frame for content
    frame = ttk.Frame(root, padding="20 20 20 20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Add title
    app_label = ttk.Label(
        frame, 
        text="Test Alert Window",
        font=("Arial", 12, "bold"),
        foreground="#0066cc"  # Dark blue
    )
    app_label.pack(anchor="w", pady=(0, 10))
    
    # Add message
    msg_label = ttk.Label(
        frame,
        text="If you can see this window, Tkinter is working correctly.\nThis confirms that popup alerts should work.",
        wraplength=340,
        justify="left"
    )
    msg_label.pack(anchor="w", pady=(0, 15))
    
    # Add dismiss button
    dismiss_btn = ttk.Button(
        frame,
        text="Dismiss",
        command=root.destroy
    )
    dismiss_btn.pack(side=tk.RIGHT, padx=5)
    
    print("Window created. You should see a popup.")
    print("The window will close automatically after 10 seconds.")
    
    # Auto-close after 10 seconds
    root.after(10000, root.destroy)
    
    # Start the Tkinter event loop
    root.mainloop()
    
    print("Window closed. Test complete.")

if __name__ == "__main__":
    main()
