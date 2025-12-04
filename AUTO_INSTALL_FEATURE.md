# Automatic Dependency Installation Feature

## Overview

The `start.sh` script now automatically installs missing dependencies when it starts, making setup much easier.

## Features

### 1. Automatic Installation ✅
- **Flask (Required)**: Automatically installed if missing
- **cryptography (Optional)**: Prompts to install for Zero Trust features
- **Ryu (Optional)**: Prompts to install for SDN features
- **Docker Python module (Optional)**: Prompts to install if Docker command exists

### 2. Smart Installation Logic ✅
- Uses virtual environment pip if venv exists
- Falls back to system pip if no venv
- Tries sudo if needed (for system-wide installs)
- Checks if package is already installed before installing

### 3. Requirements.txt Support ✅
- Offers to install all dependencies from `requirements.txt`
- Works with or without virtual environment
- Handles installation errors gracefully

## How It Works

### Required Dependencies
- **Flask**: Automatically installed if missing (script exits if installation fails)

### Optional Dependencies
- **cryptography**: Prompts "Install cryptography? [Y/n]"
- **Ryu**: Prompts "Install Ryu? [y/N]"
- **Docker**: Prompts "Install docker Python module? [Y/n]" (if Docker command exists)

### Batch Installation
- If no virtual environment is found, offers to install from `requirements.txt`
- Prompts "Install all dependencies from requirements.txt now? [Y/n]"

## Installation Flow

```
1. Check Python version ✅
2. Check virtual environment ✅
3. If no venv → Offer to install from requirements.txt
4. Check Flask (required) → Auto-install if missing
5. Check cryptography → Prompt to install
6. Check Ryu → Prompt to install
7. Check Docker → Prompt to install Python module
8. Continue with system startup
```

## Examples

### Example 1: First Run (No Dependencies)
```
📦 Checking dependencies...
  ⚠️  Flask not found (required)
     Installing flask...
     ✅ flask installed successfully
  ✅ Flask
  ⚠️  cryptography not found (optional, for certificates)
     Install cryptography? [Y/n]: y
     Installing cryptography...
     ✅ cryptography installed successfully
  ✅ cryptography
```

### Example 2: With Virtual Environment
```
✅ Virtual environment found
📦 Checking dependencies...
  ✅ Flask
  ⚠️  cryptography not found (optional, for certificates)
     Install cryptography? [Y/n]: y
     Installing cryptography...
     ✅ cryptography installed successfully
```

### Example 3: Batch Installation
```
⚠️  Virtual environment not found, using system Python
💡 Tip: You can install all dependencies from requirements.txt
Install all dependencies from requirements.txt now? [Y/n]: y
📦 Installing dependencies from requirements.txt...
✅ All dependencies installed successfully
```

## Benefits

1. **Easier Setup**: No need to manually install dependencies
2. **User-Friendly**: Clear prompts and progress messages
3. **Flexible**: Works with or without virtual environment
4. **Safe**: Checks before installing, handles errors gracefully
5. **Smart**: Uses appropriate pip (venv or system)

## Notes

- **Virtual Environment**: If venv exists, packages are installed in venv
- **System Installation**: If no venv, packages are installed system-wide (may require sudo)
- **Error Handling**: Script continues even if optional packages fail to install
- **Already Installed**: Script detects if packages are already installed

## Manual Installation

If automatic installation fails, you can still install manually:

```bash
# With virtual environment
./venv/bin/pip install -r requirements.txt

# System-wide
pip3 install -r requirements.txt

# Or with sudo
sudo pip3 install -r requirements.txt
```

## Troubleshooting

### Installation Fails
- Check internet connection
- Try manual installation: `pip install <package>`
- Check pip version: `pip --version`
- For system installs, may need sudo

### Virtual Environment Issues
- Create venv: `python3 -m venv venv`
- Activate: `source venv/bin/activate`
- Install: `pip install -r requirements.txt`

---

**The script now makes setup much easier by automatically handling dependencies!**

