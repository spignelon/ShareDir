import os
import socket
import qrcode
from flask import Flask, send_from_directory, request, abort, jsonify, render_template_string
import diceware
from argparse import Namespace

def generate_passphrase():
    # Create an options object
    options = Namespace()
    options.num = 4
    options.delimiter = '-'
    options.specials = False
    options.caps = False    
    options.randomsource = "system"
    options.infile = None
    options.wordlist = ['en']       

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

def create_http_server(directory, passphrase):
    app = Flask(__name__)

    @app.route('/', defaults={'req_path': ''})
    @app.route('/<path:req_path>')
    def dir_listing(req_path):
        if request.args.get('passphrase') != passphrase:
            if request.args.get('passphrase') is not None:
                print("Incorrect passphrase. The correct passphrase is:", passphrase, "AND NOT", request.args.get('passphrase'))
            abort(403)

        abs_path = os.path.join(directory, req_path)

        if not os.path.exists(abs_path):
            print(f"Path not found: {abs_path}")        
            return jsonify({"error": "Path not found"}), 404

        if os.path.isfile(abs_path):
            return send_from_directory(directory, req_path)

        # Split files and directories into separate lists
        items = os.listdir(abs_path)
        directories = sorted([item for item in items if os.path.isdir(os.path.join(abs_path, item))])
        files = sorted([item for item in items if os.path.isfile(os.path.join(abs_path, item))])

        return render_template_string("""
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
        """, req_path=req_path, directories=directories, files=files, passphrase=passphrase)

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

    img = qr.make_image(fill='black', back_color='white')
    qr.print_ascii()

if __name__ == "__main__":
    directory = input("Enter the directory to be served: ")

    if not os.path.isdir(directory):
        print("The provided path is not a directory.")
        exit(1)

    passphrase = generate_passphrase()
    print(f"Generated passphrase: {passphrase}")

    ip_address = get_lan_ip()  # Automatically detect LAN IP address
    http_port = 44447
    url = f"http://{ip_address}:{http_port}/?passphrase={passphrase}"
    print(f"Access URL: {url}")

    # Display the QR codel
    display_qr_code(url)

    # Create and start the HTTP server
    http_server = create_http_server(directory, passphrase)
    http_server.run(host="0.0.0.0", port=http_port)
