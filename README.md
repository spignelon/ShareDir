# ShareDir

ShareDir is a simple and convenient Python-based tool that allows you to share files and directories over LAN or the internet using a single command. Whether you're looking to stream movies from your laptop to your phone, share files between devices connected to the same WiFi network, or host a directory from your VPS, ShareDir makes it easy with an embedded HTTP server and passphrase protection. The tool generates a shareable URL, including a secure passphrase, that can be shared across devices. You can even access it using a QR code for a seamless connection.

## Features

- **Simple File and Directory Sharing:** Share files and entire directories over LAN or internet with just one command.
- **QR Code for Quick Access:** The tool generates a QR code, making it easy to access the shareable URL from any device.
- **Passphrase Protection:** Each session is protected with a generated passphrase to prevent unauthorized access.
- **Blacklist:** IPs with excessive failed login attempts are blacklisted for a set duration to prevent against bruteforcing and dictionary attacks.
- **Dark Mode Interface:** Built-in support for dark mode in the web interface for comfortable browsing.
- **LAN and Internet Access:** Share files within your local network or use a public IP address from a VPS to share across the internet.

## Installation

1. Clone this repository or download the script directly:
   ```bash
   git clone https://github.com/spignelon/ShareDir.git
   cd ShareDir
   ```

2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

ShareDir allows you to share a file or directory over LAN or internet using a single command. Below are the usage instructions.

### Basic Usage

```bash
python sharedir.py /path/to/file/or/directory
```

This will start a local HTTP server that serves the specified file or directory. The server will display a shareable URL and a QR code for quick access.

### Options

- `path` (required): The path to the file or directory you wish to share.
- `--passphrase-length` or `-p` (optional): Specify the number of words in the passphrase. Default is 4.

### Example

To share a directory named `movies` with a passphrase of 6 words:

```bash
python sharedir.py ~/movies -p 6
```

This will output something like:

```
Generated passphrase: grape-apple-banana-orange-kiwi-lemon
Access URL: http://192.168.1.100:44447/?passphrase=grape-apple-banana-orange-kiwi-lemon
```

You can access this URL from any device connected to the same network, or scan the displayed QR code with your phone.

### Accessing Files

Once the server is running, navigate to the provided URL in a web browser, or use the QR code. You'll be prompted to enter the passphrase in the URL parameters. For example:

```
http://192.168.1.100:44447/?passphrase=grape-apple-banana-orange-kiwi-lemon
```

From here, you can browse and download files directly from the web interface.

### Sharing Over the Internet

If you're on a VPS with a public IP, it will automatically generate the QR Code and the URL using your VPS's public IP. Share this URL with any device on the internet to access the shared directory.

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE). See the [LICENSE](LICENSE) file for details. <br>
[![GNU AGPLv3.0 Image](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html)
