# GAIA Benchmark AI Agent

A production-ready AI agent designed to tackle the GAIA benchmark, built for the Hugging Face AI Agents Course (Unit 4).

## About This Project

This agent was developed as part of the **Hugging Face AI Agents Course - Unit 4**, with the goal of building an AI system capable of scoring well on the challenging GAIA benchmark.

## What is GAIA?

GAIA (General AI Assistants) is a benchmark that evaluates AI systems on real-world assistant tasks that are:

- **Simple for humans** (92% success rate) but hard for AI (GPT-4: ~15%)
- **Multi-modal**: requiring text, image, audio, and video understanding
- **Tool-dependent**: needing web search, file analysis, and code execution
  – O**bjectively measurable**: with unambiguous factual answers

# What our agent does

## 🔍 Multi-modal Analysis:

- Audio transcription (MP3, WAV, M4A files) using OpenAI Whisper
- Image analysis and description using Vision models
- YouTube video content analysis (subtitles + audio extraction)
- Document processing (Excel, CSV, PDF, text files)

## 🌐 Web Intelligence:

- Web search and content extraction using Tavily
- Real-time information gathering from websites
- YouTube video analysis with transcript extraction
- Source verification and fact-checking

## 🧮 Data Processing:

- Python code execution for complex calculations
- Spreadsheet analysis and data manipulation
- Multi-step reasoning chains with state management
- File format detection and appropriate tool selection

## 🎯 GAIA-Specific Features:

- Automatic task difficulty assessment (Level 1-3)
- GAIA API integration for benchmark submission
- Autonomous execution without human guidance
- Proper answer formatting for benchmark evaluation
- Rate limiting and error handling for production use

# Architecture & Template

![Graph view in LangGraph studio UI](./static/studio_ui.png)

This agent is built using the **LangGraph ReAct Agent Template**, which provides a robust foundation for reasoning and action agents.

### Core LangGraph Components:

- **StateGraph**: Manages agent execution flow between reasoning and action
- **ToolNode**: Handles tool invocation and response processing
- **Configuration**: Flexible model and parameter settings
- **Message Handling**: Structured conversation state management

### ReAct Pattern Implementation:

1. **Reason**: Agent analyzes the task and plans next steps
2. **Act**: Agent executes chosen tools to gather information
3. **Observe**: Agent processes tool results and updates understanding
4. **Repeat**: Continue until task is complete with final answer

### Tool Ecosystem (15+ Specialized Tools):

| Category             | Tools                                                        | Purpose                                   |
| -------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| **Web & Search**     | `search`, `extract_text_from_url`                            | Information gathering and web browsing    |
| **Media Analysis**   | `transcribe_audio`, `analyze_youtube_video`, `analyze_image` | Audio/video/image processing              |
| **File Processing**  | `analyze_file`, `read_spreadsheet`, `download_gaia_file`     | Document analysis and file handling       |
| **Data Science**     | `python_repl`, `analyze_spreadsheet_data`                    | Calculations and data analysis            |
| **GAIA Integration** | `fetch_gaia_task`, `list_gaia_tasks`                         | Benchmark interaction and task management |

## Getting Started

Assuming you have already [installed LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download), to set up:

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd gaia-benchmark-agent

# Create .env file
cp .env.example .env
```

### 2. Configure API Keys

Add the following to your `.env` file:

```env
# Required for search functionality
TAVILY_API_KEY=your-tavily-api-key

# Choose your LLM provider
ANTHROPIC_API_KEY=your-anthropic-key
# OR
OPENAI_API_KEY=your-openai-key

# Optional: LangSmith for tracing
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=gaia-agent
```

### 3. Quick Start

#### Run GAIA Benchmark (Full Automation)

```bash
# Run first 5 questions for testing
python -m react_agent.run_gaia_benchmark

# Edit the script to change username and max_questions
```

#### Interactive Development

```bash
# Open in LangGraph Studio
langgraph dev

# Or run individual tasks
python -c "
from react_agent import run_all_gaia_tasks
import asyncio

async def test():
    result = await run_all_gaia_tasks(
        username='your_username',
        max_questions=3
    )
    print(result)

asyncio.run(test())
"
```

### 4. Model Configuration

The agent supports multiple LLM providers. Configure in LangGraph Studio or via environment:

```yaml
# Default configuration
model: anthropic/claude-3-5-sonnet-20240620
# Alternative options:
# model: openai/gpt-4o
# model: openai/gpt-4-turbo
```

## GAIA Performance & Results

### Benchmark Structure

- **Level 1**: Basic tasks (5-10 steps, 1-2 tools) - Target: >30%
- **Level 2**: Intermediate tasks (10-15 steps, multiple tools) - Target: >15%
- **Level 3**: Complex tasks (15+ steps, advanced reasoning) - Target: >5%

### Key Features for GAIA Success

- ✅ **Autonomous Operation**: No human guidance required during execution
- ✅ **Multi-modal Processing**: Handles text, audio, images, and video
- ✅ **Robust Error Handling**: Graceful failure recovery and retries
- ✅ **Proper Formatting**: GAIA-compliant answer format with "FINAL ANSWER:"
- ✅ **Rate Limiting**: API compliance with 5-second delays between questions
- ✅ **Tool Orchestration**: Intelligent tool selection and chaining

### Example GAIA Tasks Our Agent Can Handle:

- **Level 1**: "What was the enrollment count of the H. pylori clinical trial from Jan-May 2018 on NIH website?"
- **Level 2**: "Analyze this Excel file and calculate total food sales excluding drinks"
- **Level 3**: "Find the astronaut from NASA Group X who spent least time in space, excluding those with zero time"

## How to Customize

### 1. Add New Tools

Extend the agent's capabilities by adding tools in `src/react_agent/tools.py`:

```python
async def my_custom_tool(parameter: str) -> str:
    """Description of what this tool does."""
    # Your implementation here
    return result

# Add to TOOLS list
TOOLS.append(my_custom_tool)
```

### 2. Modify System Prompt

Update the agent's behavior in `src/react_agent/prompts.py`:

```python
SYSTEM_PROMPT = """
Your custom instructions here...
Remember to always end with: FINAL ANSWER: [answer]
"""
```

### 3. Adjust Model Settings

Configure different models in `src/react_agent/configuration.py` or via LangGraph Studio.

### 4. Custom GAIA Integration

Modify `src/react_agent/gaia_runner.py` to:

- Change submission parameters
- Add custom preprocessing
- Implement different execution strategies

## Development

### Local Development with Hot Reload

```bash
# Start LangGraph Studio for interactive development
langgraph dev

# Run tests
python -m pytest tests/

# Format code
make format

# Lint code
make lint
```

### Debugging Tips

- Use LangGraph Studio's state inspection to debug execution flow
- Check `src/react_agent/prompts.py` for GAIA-specific instructions
- Monitor tool execution in the studio's trace view
- Test individual tools with small examples before full GAIA runs

### Integration with LangSmith

For detailed tracing and collaboration:

1. Set `LANGSMITH_API_KEY` in `.env`
2. Set `LANGSMITH_TRACING=true`
3. View detailed execution traces in LangSmith dashboard

## Project Structure

```
src/react_agent/
├── __init__.py              # Main exports
├── graph.py                 # LangGraph state machine
├── tools.py                 # Tool implementations (15+ tools)
├── prompts.py               # GAIA-optimized system prompts
├── configuration.py         # Agent configuration
├── gaia_runner.py          # GAIA benchmark orchestration
├── run_gaia_benchmark.py   # CLI entry point
└── utils.py                # Helper functions

tests/
├── unit_tests/             # Unit tests
└── integration_tests/      # GAIA integration tests
```

## Template Credit & Architecture

This agent is built on the [LangGraph ReAct Agent Template](https://github.com/langchain-ai/react-agent), which provides:

- 🧠 **ReAct Pattern**: Iterative reasoning and acting loops
- 🛠️ **Tool Integration**: Seamless tool calling and response handling
- 📊 **State Management**: Robust conversation state tracking
- 🔄 **Error Handling**: Automatic retries and graceful failure modes
- 📈 **Scalability**: Production-ready architecture with LangGraph

The core logic, defined in `src/react_agent/graph.py`, demonstrates a flexible ReAct agent that iteratively reasons about user queries and executes actions, making it ideal for the complex, multi-step reasoning required by GAIA benchmark tasks.

---

**Course**: Hugging Face AI Agents Course - Unit 4  
**Objective**: Build production-ready agents capable of scoring on challenging benchmarks  
**Framework**: LangGraph + ReAct pattern for robust agent orchestration
