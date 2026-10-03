import os
import webbrowser

base_dir = os.path.dirname(os.path.abspath(__file__))

html_file = os.path.join(base_dir, "../frontend/html/index.html")

webbrowser.open("file://" + html_file)

print("DOWNLOADING 100% RAM AND OPTIMIZING")