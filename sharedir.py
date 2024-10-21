import os
import socket
import qrcode
from flask import (
    Flask,
    send_file,
    send_from_directory,
    request,
    abort,
    jsonify,
    render_template_string,
)
import diceware
from argparse import ArgumentParser, Namespace
from time import time

# Dictionary to store failed attempts
failed_attempts = {}
blacklist = {}

# Thresholds
MAX_FAILED_ATTEMPTS = 10
TIME_WINDOW = 60  # 1 minute
BLACKLIST_DURATION = 4 * 60 * 60  # 4 hours in seconds


def generate_passphrase(num_words):
    # Create an options object
    options = Namespace()
    options.num = num_words
    options.delimiter = "-"
    options.specials = False
    options.caps = False
    options.randomsource = "system"
    options.infile = None
    options.wordlist = ["en"]

    # Generate the passphrase
    passphrase = diceware.get_passphrase(options)
    return passphrase


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external IP address to get the LAN IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# checking if IP is blacklisted and removing old entries
def is_blacklisted(ip):
    if ip in blacklist:
        if time() < blacklist[ip]:
            return True
        else:
            del blacklist[ip]
    return False


def log_failed_attempt(ip):
    # Log failed attempt with a timestamp
    now = time()
    if ip not in failed_attempts:
        failed_attempts[ip] = []

    # Removing old entries
    failed_attempts[ip] = [
        attempt for attempt in failed_attempts[ip] if now - attempt < TIME_WINDOW
    ]

    # Add current attempt
    failed_attempts[ip].append(now)

    # Check if it exceeds the max allowed attempts
    if len(failed_attempts[ip]) >= MAX_FAILED_ATTEMPTS:
        blacklist[ip] = now + BLACKLIST_DURATION
        del failed_attempts[ip]

def create_http_server(path, passphrase):
    app = Flask(__name__)
    is_file = os.path.isfile(path)

    @app.route("/", defaults={"req_path": ""})
    @app.route("/<path:req_path>")
    def dir_listing(req_path):
        ip = request.remote_addr

        if is_blacklisted(ip):
            print(f"IP {ip} is blacklisted.")
            return jsonify({
                "error": "Too many failed attempts. You are blacklisted for 4 hours."
            }), 403

        if request.args.get("passphrase") != passphrase:
            if request.args.get("passphrase") is not None:
                log_failed_attempt(ip)
                print(
                    "Incorrect passphrase. The correct passphrase is:",
                    passphrase,
                    "AND NOT",
                    request.args.get("passphrase"),
                )
            abort(403)

        if is_file:
            # Serve the single file
            if req_path and req_path != os.path.basename(path):
                return jsonify({"error": "Path not found"}), 404
            return send_file(path)
        else:
            # Serve the directory listing
            abs_path = os.path.join(path, req_path)
            if not os.path.exists(abs_path):
                return jsonify({"error": "Path not found"}), 404
            if os.path.isfile(abs_path):
                return send_from_directory(path, req_path)

        # Split files and directories into separate lists
        items = os.listdir(abs_path)
        directories = sorted([
            item for item in items if os.path.isdir(os.path.join(abs_path, item))
        ])
        files = sorted([
            item for item in items if os.path.isfile(os.path.join(abs_path, item))
        ])

        return render_template_string(
            """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Directory Listing</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                    transition: background-color 0.3s, color 0.3s;
                }
                h1 {
                    background-color: #3498db;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                }
                ul {
                    list-style-type: none;
                    padding-left: 0;
                }
                li {
                    margin: 10px 0;
                    font-size: 18px;
                }
                .file {
                    color: #2980b9;
                }
                .folder {
                    color: #27ae60;
                    font-weight: bold;
                }
                .icon {
                    margin-right: 10px;
                }
                a {
                    text-decoration: none;
                    color: #2980b9; /* Default blue color for links */
                }
                a:hover {
                    text-decoration: underline;
                }
                .dark-mode {
                    background-color: #333;
                    color: #f4f4f4;
                }
                .dark-mode h1 {
                    background-color: #555;
                }
                .dark-mode a {
                    color: #1abc9c; /* Light blue-green for dark mode */
                }
                #dark-mode-toggle {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background-color: #000000;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    cursor: pointer;
                }
            </style>
        </head>
        <body>

            <!-- Dark Mode Toggle Button -->
            <button id="dark-mode-toggle">🌒</button>

            <!-- Header -->
            <h1>Directory listing {% if req_path %} for {{ req_path }} {% endif %}</h1>
        
            <!-- Directory Listing -->
            <ul>        
                <!-- Display directories first -->
                {% for directory in directories %}
                    <li>
                        <span class="icon">📁</span>
                        <a class="folder" href="{{ '/' + req_path + '/' + directory if req_path else '/' + directory }}?passphrase={{ passphrase }}">{{ directory }}</a>
                    </li>
                {% endfor %}
                
                <!-- Display files after directories -->
                {% for file in files %}
                    <li>
                        <span class="icon">📄</span>
                        <a class="file" href="{{ '/' + req_path + '/' + file if req_path else '/' + file }}?passphrase={{ passphrase }}">{{ file }}</a>
                    </li>
                {% endfor %}
            </ul>

            <!-- JavaScript for Dark Mode Toggle -->
            <script>
                const toggleButton = document.getElementById('dark-mode-toggle');
                const body = document.body;

                // Check if dark mode is already enabled in local storage
                if (localStorage.getItem('dark-mode') === 'enabled') {
                    body.classList.add('dark-mode');
                }

                // Toggle dark mode
                toggleButton.addEventListener('click', function() {
                    body.classList.toggle('dark-mode');

                    // Store the dark mode setting in local storage
                    if (body.classList.contains('dark-mode')) {
                        localStorage.setItem('dark-mode', 'enabled');
                    } else {
                        localStorage.removeItem('dark-mode');
                    }
                });
            </script>
        </body>
        </html>
        """,
            req_path=req_path,
            directories=directories,
            files=files,
            passphrase=passphrase,
        )

    return app


def display_qr_code(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # img = qr.make_image(fill="black", back_color="white")
    qr.print_ascii()


def main():
    parser = ArgumentParser(description="Share a directory or file over HTTP.")
    parser.add_argument(
        "path",
        help="Path to the directory or file to be shared (relative or absolute).",
    )
    parser.add_argument(
        "-p",
        "--passphrase-length",
        type=int,
        default=4,
        help="Number of words in the passphrase (default: 4).",
    )
    args = parser.parse_args()

    # Resolving absolute path
    shared_path = os.path.abspath(args.path)
    if not os.path.exists(shared_path):
        print(f"The provided path '{shared_path}' does not exist.")
        exit(1)

    passphrase = generate_passphrase(args.passphrase_length)
    print(f"Generated passphrase: {passphrase}")

    ip_address = get_lan_ip()  # Detect LAN IP address
    http_port = 44447
    url = f"http://{ip_address}:{http_port}/?passphrase={passphrase}"
    print(f"Access URL: {url}")

    # Display the QR codel
    display_qr_code(url)

    # Create and start the HTTP server
    http_server = create_http_server(shared_path, passphrase)
    http_server.run(host="0.0.0.0", port=http_port)


if __name__ == "__main__":
    main()
