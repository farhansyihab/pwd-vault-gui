import tkinter as tk
from tkinter import ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("pwd-vault")
        self.root.geometry("400x300")
        
        label = ttk.Label(root, text="Selamat datang di pwd-vault")
        label.pack(pady=20)
