import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Translate the URL path to a local file system path
        path = self.translate_path(self.path)
        
        # If the file doesn't exist, and it doesn't look like an API or static asset,
        # fallback to index.html for React Router to handle
        if not os.path.exists(path) and not os.path.isfile(path):
            self.path = '/'
            
        return super().do_GET()

print(f"====================================================")
print(f"[INFO] SIEM Frontend is running at http://localhost:{PORT}")
print(f"====================================================")

with socketserver.TCPServer(("0.0.0.0", PORT), SPAHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down frontend server.")
