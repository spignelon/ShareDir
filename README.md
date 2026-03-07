# ShareDir

**ShareDir** is a Python tool to share files and directories over LAN or the internet with a single command. It runs a production-ready HTTP server (Waitress) with passphrase protection, QR code access, file uploads, and a modern web interface.

## Features

- Share files and directories with one command
- QR code generation (terminal + in-browser)
- Passphrase protection with brute-force blacklisting
- Production-ready server (Waitress) with configurable workers
- File upload support (optional)
- Directory ZIP download
- File metadata display (size, modified date, MIME type via magic bytes)
- Client-side search/filter
- Dark mode
- Download buttons for files and directories

## Installation

### Via pip

```bash
pip install sharedir
```

### Via git

```bash
git clone https://github.com/spignelon/ShareDir.git
cd ShareDir
pip install -r requirements.txt
```

**Note:** `python-magic` requires `libmagic`. Install it with:
- Debian/Ubuntu: `sudo apt install libmagic1`
- macOS: `brew install libmagic`
- Windows: `pip install python-magic-bin`

## Usage

```bash
sharedir /path/to/share
```

### Options

| Flag | Description |
|------|-------------|
| `-p N`, `--passphrase-length N` | Number of words in passphrase (default: 4) |
| `--no-passphrase` | Disable passphrase protection |
| `-P PORT`, `--port PORT` | Server port (default: 44447) |
| `-w N`, `--workers N` | Number of server workers (default: 3) |
| `--upload` | Enable file uploads via web interface |
| `--expire DURATION` | Auto-shutdown after duration (e.g. `30m`, `2h`, `1d`) |

### Examples

```bash
# Share a directory with 6-word passphrase on port 8080
sharedir ~/movies -p 6 -P 8080

# Share without passphrase, with uploads enabled
sharedir ~/public --no-passphrase --upload

# Run with more workers for heavy traffic
sharedir ~/files -w 8
```

Output:
```
Generated passphrase: grape-apple-banana-orange-kiwi-lemon
Access URL: http://192.168.1.100:8080/?passphrase=grape-apple-banana-orange-kiwi-lemon
Starting server on 0.0.0.0:8080 with 6 workers...
```

Requires Python >= 3.10.

## License

[![GNU AGPLv3.0](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html) <br>
[GNU AGPLv3.0](LICENSE)
