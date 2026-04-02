#!/usr/bin/env python3
"""Ventana nativa del simulador Flightmind (pywebview)."""
import os

import webview

_html_dir = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(_html_dir, "index.html")
url = "file://" + os.path.abspath(html_path)

window = webview.create_window(
    "Flightmind Simulator",
    url,
    width=1200,
    height=800,
    resizable=True,
)
webview.start()
