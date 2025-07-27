# Gmail Email Classification System 🤖📧

An intelligent email classification system that automatically organizes your Gmail inbox using DeepSeek AI. The system analyzes email content and conversation threads to apply appropriate labels, helping you stay organized and productive.

## ✨ Features

- **🤖 AI-Powered Classification**: Uses DeepSeek AI for intelligent email categorization
- **🧵 Thread-Aware Analysis**: Analyzes entire conversation threads for context-aware classification
- **🎨 Colorful Gmail Labels**: Creates visually appealing labels with Gmail-approved colors
- **⚡ Real-time Processing**: Classify new emails as they arrive
- **📊 Batch Processing**: Classify all existing emails in your inbox
- **🔍 Smart Categories**: Organizes emails into actionable categories
- **📝 Detailed Logging**: Comprehensive logging for debugging and monitoring

## 📋 Email Categories

The system classifies emails into six smart categories:

| Label | Description | Use Case |
|-------|-------------|----------|
| 📋 **To Do** | Others are asking YOU to take action | Tasks assigned to you, requests requiring your response |
| ⏳ **Awaiting Reply** | YOU are waiting for others to respond | Follow-ups, questions you've asked, pending responses |
| 📄 **FYI** | Information-only, no action required | Newsletters, updates, announcements |
| ✅ **Done** | Completed conversations | Resolved issues, delivered work, closed topics |
| 🗑️ **Junk** | Promotional or low-value emails | Spam, marketing emails, automated messages |
| 📚 **History** | Old emails (configurable threshold) | Archived conversations, aged emails |

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Gmail account with API access
- DeepSeek API account

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd gmail-email-classification

# Run the automated setup script
python scripts/install_setup.py
```

The setup script will:
- Install all Python dependencies
- Create configuration files
- Set up directory structure
- Test system compatibility

### 2. Configuration

#### Get Gmail API Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API
4. Create OAuth 2.0 Client ID credentials
5. Download as `credentials.json` and place in project root

#### Get DeepSeek API Key
1. Sign up at [DeepSeek](https://platform.deepseek.com/)
2. Generate an API key
3. Add to your `.env` file

#### Configure Environment
Edit the `.env` file with your settings:

```env
# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Gmail API Configuration  
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# Classification Settings
HISTORY_DAYS=10
DEFAULT_MODEL=deepseek-chat

# Optional: Custom label names (comma-separated)
CUSTOM_LABELS=To Do,Awaiting Reply,FYI,Done,SPAM,History

# Debug mode
DEBUG=False
VERBOSE_LOGGING=False
```

### 3. Initial Setup

```bash
# Test your configuration
python scripts/test_connection.py

# Set up labels and classify existing emails
python gmail_setup_agent.py
```

### 4. Real-time Classification

```bash
# Classify the latest email
python gmail_realtime_agent.py

# Classify a specific email by ID
python gmail_realtime_agent.py <message_id>

# Classify multiple recent emails
python gmail_realtime_agent.py --count 10
```

## 📁 Project Structure

```
gmail-email-classification/
├── 📄 README.md                 # This file
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env.example             # Environment template
├── 📄 .gitignore               # Git ignore rules
├── 📄 config.py                # Configuration management
├── 📄 gmail_auth.py            # Gmail API authentication
├── 📄 utils.py                 # Utility functions
├── 📄 gmail_setup_agent.py     # Initial setup and batch processing
├── 📄 gmail_realtime_agent.py  # Real-time email classification
├── 📄 debug_script.py          # Debugging tools
├── 📄 test_deepseek.py         # DeepSeek integration test
└── 📁 scripts/
    ├── 📄 install_setup.py     # Automated installation
    └── 📄 test_connection.py   # Connection testing
```

## 🛠️ Usage Examples

### Batch Classification
```bash
# Classify all emails in inbox (up to 500)
python gmail_setup_agent.py

# The agent will:
# 1. Create colorful Gmail labels
# 2. Analyze each email with DeepSeek AI
# 3. Apply appropriate labels
# 4. Provide detailed statistics
```

### Real-time Classification
```bash
# Classify the most recent email
python gmail_realtime_agent.py

# Classify last 5 emails
python gmail_realtime_agent.py --count 5

# Classify specific email
python gmail_realtime_agent.py 1234567890abcdef

# Enable debug mode
python gmail_realtime_agent.py --debug
```

### Debugging
```bash
# Test classification logic
python debug_script.py

# Test system connectivity
python scripts/test_connection.py

# Test DeepSeek integration
python test_deepseek.py
```

## 🧠 How It Works

### 1. Thread-Aware Analysis
The system analyzes entire email conversations, not just individual messages:

```
Thread Example:
1. Client: "Please provide documents A, B, C"
2. You: "Here are A, B. Could you help with date for C?"
3. Client: "Date should be March 26. Please provide updated C"
4. You: "Please find the attached document. Thanks"

→ Email #4 = ✅ Done (conversation complete)
```

### 2. Smart Classification Logic
- **📋 To Do**: Others requesting action from you
- **⏳ Awaiting Reply**: You waiting for others' responses
- **✅ Done**: Completed conversations with final deliverables
- **📄 FYI**: Information sharing, no action required


## ⚙️ Configuration Options

### Custom Labels
Define your own labels in `.env`:
```env
CUSTOM_LABELS=Urgent,Project A,Clients,Personal,Archive
```

### History Threshold
Set how many days before emails are auto-classified as History:
```env
HISTORY_DAYS=7  # 1 week
HISTORY_DAYS=30 # 1 month
```

### Debug Mode
Enable detailed logging:
```env
DEBUG=True
VERBOSE_LOGGING=True
```

## 🎨 Label Colors

The system uses Gmail's official color palette:

- 📋 **To Do**: Orange (`#ffad47`)
- ⏳ **Awaiting Reply**: Blue (`#4a86e8`)
- 📄 **FYI**: Light Blue (`#6d9eeb`)
- ✅ **Done**: Green (`#16a766`)
- 🗑️ **Junk**: Red (`#cc3a21`)
- 📚 **History**: Gray (`#cccccc`)

## 🔧 Troubleshooting

### Common Issues

**Gmail Authentication Failed**
```bash
# Delete existing token and re-authenticate
rm token.json
python scripts/test_connection.py
```

**DeepSeek API Errors**
```bash
# Verify API key in .env file
python test_deepseek.py
```

**Import Errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**No Emails Classified**
```bash
# Check debug output
python gmail_realtime_agent.py --debug
```

### Debug Mode

Enable comprehensive logging by setting `DEBUG=True` in `.env`:

```bash
# Test single email with full debug output
python debug_script.py
```

This will show:
- Email content extraction
- AI classification reasoning
- Label application process
- Detailed error messages
--
