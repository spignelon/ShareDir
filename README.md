# ShareDir

**ShareDir** is a simple and convenient Python-based tool that allows you to share files and directories over LAN or the internet using a single command. Whether you're looking to stream movies from your laptop to your phone, share files between devices connected to the same WiFi network, or host a directory from your VPS, ShareDir makes it easy with an embedded HTTP server and passphrase protection.

The tool generates a shareable URL, including a secure passphrase, that can be shared across devices. You can scan the auto generaed QR code for easy file and folder sharing.

## Features

- **Simple File and Directory Sharing**: Share files and entire directories over LAN or the internet with just one command.
- **QR Code for Quick Access**: The tool generates a QR code, making it easy to access the shareable URL from any device.
- **Passphrase Protection**: Each session is protected with a generated passphrase to prevent unauthorized access.
- **Blacklist**: IPs with excessive failed login attempts are blacklisted for a set duration to prevent bruteforcing or dictionary attacks.
- **Dark Mode Interface**: Built-in support for dark mode in the web interface for comfortable browsing.
- **LAN and Internet Access**: Share files within your local network or use a public IP address from a VPS to share across the internet.

## Installation

There are two ways to install **ShareDir**: via `pip` or cloning the repository directly from GitHub.

### Option 1: Install via `pip`

The easiest way to install **ShareDir** is by using `pip`. You can install the tool with the following command:

```bash
pip install sharedir
```

### Option 2: Install via `git clone`

You can also install **ShareDir** by cloning the repository from GitHub and manually installing the dependencies:

1. Clone the repository:

   ```bash
   git clone https://github.com/spignelon/ShareDir.git
   cd ShareDir
   ```

2. Install the dependencies using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

**ShareDir** allows you to share a file or directory over LAN or the internet using a single command. Below are the usage instructions for both installation methods.

### Basic Usage

After installation, you can share a file or directory by running the following command:

```bash
sharedir /path/to/file/or/directory
```

This command will start a local HTTP server that serves the specified file or directory. The server will display a shareable URL and a QR code for quick access.

### Options

- **path (required)**: The path to the file or directory you wish to share.
- **--passphrase-length or -p (optional)**: Specify the number of words in the passphrase (default is 4).

### Example

To share a directory named `movies` with a passphrase of 6 words:

```bash
sharedir ~/movies -p 6
```
OR
```bash
python sharedir/sharedir.py ~/movies -p 6
```

This will output something like:

```bash
Generated passphrase: grape-apple-banana-orange-kiwi-lemon
Access URL: http://192.168.1.100:44447/?passphrase=grape-apple-banana-orange-kiwi-lemon
```

You can access this URL from any device connected to the same network, or scan the displayed QR code with your phone.

### Accessing Files

Once the server is running, navigate to the provided URL in a web browser or use the QR code. You'll be prompted to enter the passphrase in the URL parameters. For example:

```
http://192.168.1.100:44447/?passphrase=grape-apple-banana-orange-kiwi-lemon
```

From here, you can browse and download files directly from the web interface.

### Sharing Over the Internet

If you're on a VPS with a public IP, the tool will automatically generate a QR code and the URL using your VPS's public IP. Share this URL with to device on the internet to access the shared directory or file.

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE). See the [LICENSE](LICENSE) file for details. <br>
[![GNU AGPLv3.0 Image](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html)
