"""Graph con nuovo sistema di stato"""

from langgraph.prebuilt import ToolNode
from datetime import UTC, datetime
from typing import Dict, Any, List, Literal, cast

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode


from react_agent.configuration import Configuration
from react_agent.state_v2 import GAIAInputState, GAIAInternalState, GAIAOutputState
from react_agent.tools import TOOLS
from react_agent.utils import load_chat_model

# 🧠 Model Node con tracking avanzato


async def call_model_with_tracking(state: GAIAInternalState) -> Dict[str, Any]:
    """Model node che traccia reasoning steps"""

    print(f"\n🔧 [GRAPH] State ricevuto nel model:")
    print(f"  - task_id: '{state.task_id}' (len: {len(state.task_id)})")
    print(f"  - has_file: {state.has_file}")
    print(f"  - file_name: '{state.file_name}' (len: {len(state.file_name)})")
    print(f"  - tools_used: {state.tools_used}")
    print(f"  - reasoning_steps: {len(state.reasoning_steps)}")
    print(f"  - messages count: {len(state.messages)}")
    
    if state.task_id:
        print("  ✅ Task ID is populated")
    else:
        print("  ❌ Task ID is empty - data not passed correctly!")

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model).bind_tools(TOOLS)

    # System prompt con contesto
    system_message = configuration.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    # Aggiungi contesto se abbiamo metadati
    if state.task_id:
        context_info = f"\n\n=== CURRENT TASK CONTEXT ===\n"
        context_info += f"Task ID: {state.task_id}\n"
        context_info += f"Has File: {state.has_file}\n"
        context_info += f"Tools Used: {', '.join(state.tools_used)}\n"
        context_info += f"Current Step: {state.current_step}\n"
        system_message += context_info

    # Get model response
    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_message},
            *state.messages
        ])
    )

    # Handle last step
    if state.is_last_step and response.tool_calls:
        return {
            "messages": [response],
            "error_count": state.error_count + 1
        }

    # Extract reasoning step
    new_reasoning = extract_reasoning_step(response.content or "")
    
    # Aggiungi reasoning step
    updated_reasoning = state.reasoning_steps.copy()
    if new_reasoning and len(new_reasoning) > 10:
        updated_reasoning.append(new_reasoning)
        print(f"🔧 [GRAPH] Added reasoning step: {new_reasoning[:50]}...")

    # Update current step
    current_step = "reasoning" if not response.tool_calls else f"using_tools({len(response.tool_calls)})"

    # ✅ CRITICAL: Return TUTTO lo stato, non solo i campi modificati
    return {
        # Campi aggiornati
        "messages": [response],
        "reasoning_steps": updated_reasoning,
        "current_step": current_step,
        
        # ✅ PRESERVA tutti i metadati esistenti
        "task_id": state.task_id,
        "has_file": state.has_file,
        "file_name": state.file_name,
        "tools_used": state.tools_used,
        "reasoning_steps": updated_reasoning,
        "current_step": current_step,
        "start_time": state.start_time,
        "difficulty_level": state.difficulty_level,
        "confidence": state.confidence,
        "error_count": state.error_count
    }


def extract_reasoning_step(content: str) -> str:
    """Estrae il reasoning step dal contenuto - versione migliorata"""
    if not content:
        return ""

    # ✅ Cerca pattern più specifici di reasoning
    reasoning_patterns = [
        r"I need to (.+)",
        r"Let me (.+)",
        r"First, I will (.+)",
        r"To (.+), I should (.+)",
        r"I'll (.+)",
        r"My approach is to (.+)"
    ]
    
    import re
    
    # Prova pattern specifici
    for pattern in reasoning_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            return f"Reasoning: {matches[0][:100]}"
    
    # Fallback: cerca linee che iniziano con parole chiave di reasoning
    lines = content.split('\n')
    reasoning_lines = []

    for line in lines:
        line = line.strip()
        if any(line.lower().startswith(marker) for marker in [
            'i need', 'let me', 'first', 'to answer', 'i should', 'i will', 'my plan'
        ]):
            reasoning_lines.append(line)

    if reasoning_lines:
        return ' '.join(reasoning_lines)[:150]
    
    # Ultimo fallback: primi 100 caratteri se contiene parole chiave
    if any(keyword in content.lower() for keyword in ['think', 'reason', 'analyze', 'consider', 'need to']):
        return content[:100] + "..."
    
    return ""


# 🔄 Routing con tracking
def route_model_output_tracked(state: GAIAInternalState) -> Literal["prepare_output", "tools"]:
    last_message = state.messages[-1]

    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage, got {type(last_message).__name__}")

    if not last_message.tool_calls:
        return "prepare_output"  # ✅ Va al nodo di output

    return "tools"


# 🛠️ Tool Node con tracking


class TrackedToolNode(ToolNode):
    """ToolNode che traccia quali tool vengono usati"""

    def __init__(self, tools):
        super().__init__(tools)

    async def invoke(self, input, config, **kwargs):
        """Override invoke per tracciare i tools usati"""
        print(f"\n🔧 [TRACKED_TOOLS] Starting tool execution...")
        
        # ✅ Estrai tool names PRIMA dell'esecuzione
        tool_names = []
        if hasattr(input, 'messages') and input.messages:
            last_message = input.messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                tool_names = [call.get('name', 'unknown_tool') for call in last_message.tool_calls]
                print(f"🔧 [TRACKED_TOOLS] About to execute: {tool_names}")
        
        # Esegui i tool normalmente
        result = await super().invoke(input, config, **kwargs)
        
        # ✅ Aggiorna lo stato con i tools eseguiti
        if tool_names:
            current_tools = getattr(input, 'tools_used', [])
            updated_tools = list(set(current_tools + tool_names))  # Evita duplicati
            
            # ✅ CRITICAL: Aggiungi al result invece di sovrascrivere
            if isinstance(result, dict):
                result['tools_used'] = updated_tools
            else:
                # Se result non è dict, creane uno
                result = {
                    'messages': result.messages if hasattr(result, 'messages') else [],
                    'tools_used': updated_tools
                }
            
            print(f"🔧 [TRACKED_TOOLS] Updated tools_used: {updated_tools}")
        
        return result


# 📊 Output Processing Node
def prepare_clean_output(state: GAIAInternalState) -> Dict[str, Any]:
    """Node finale che prepara output pulito"""

    print(f"\n🔧 [OUTPUT] Preparing final output:")
    print(f"  - task_id: '{state.task_id}'")
    print(f"  - messages count: {len(state.messages)}")

    # ✅ Estrai tools_used dai messaggi invece di tracciare manualmente
    tools_used = extract_tools_from_messages(state.messages)
    
    # ✅ Estrai reasoning dai messaggi AI
    reasoning_steps = extract_reasoning_from_messages(state.messages)
    
    print(f"  - tools_used (extracted): {tools_used}")
    print(f"  - reasoning_steps (extracted): {len(reasoning_steps)}")

    # Calcola processing time
    processing_time = 0.0
    if state.start_time:
        processing_time = (datetime.now() - state.start_time).total_seconds()

    # Estrai final answer
    final_answer = ""
    submitted_answer = ""

    if state.messages:
        last_content = state.messages[-1].content
        if "FINAL ANSWER:" in last_content:
            final_answer = last_content.split("FINAL ANSWER:")[-1].strip()
            submitted_answer = final_answer
        else:
            final_answer = last_content

    # Prepara reasoning trace dai messaggi estratti
    reasoning_trace = "\n".join([
        f"Step {i+1}: {step}"
        for i, step in enumerate(reasoning_steps)
    ])

    # Calcola confidence
    confidence = calculate_confidence_from_execution(state, tools_used, reasoning_steps)

    output = GAIAOutputState(
        messages=state.messages,
        final_answer=final_answer,
        task_id=state.task_id, 
        submitted_answer=submitted_answer,
        reasoning_trace=reasoning_trace,
        confidence=confidence,
        tools_used=tools_used,  # ✅ Dai messaggi
        processing_time=processing_time,
        steps_taken=len(reasoning_steps),
        errors_encountered=state.error_count
    )
    
    print(f"\n🔧 [OUTPUT] Final GAIAOutputState:")
    print(f"  - task_id: '{output.task_id}'")
    print(f"  - tools_used: {output.tools_used}")
    print(f"  - confidence: {output.confidence}")

    return {"clean_output": output}


def extract_tools_from_messages(messages) -> List[str]:
    """Estrae i tools usati dai messaggi"""
    tools_used = []
    
    for message in messages:
        # Cerca tool calls nei messaggi AI
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.get('name', 'unknown')
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
    
    print(f"🔧 [EXTRACT] Found tools in messages: {tools_used}")
    return tools_used


def extract_reasoning_from_messages(messages) -> List[str]:
    """Estrae reasoning steps dai messaggi AI"""
    reasoning_steps = []
    
    for message in messages:
        if hasattr(message, 'content') and message.content:
            # Cerca pattern di reasoning nel contenuto
            content = str(message.content)
            
            # Pattern di reasoning
            reasoning_patterns = [
                r"I need to (.+)",
                r"Let me (.+)",
                r"First, I will (.+)",
                r"To answer this, I (.+)",
                r"I'll (.+)",
                r"My approach (.+)"
            ]
            
            import re
            for pattern in reasoning_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    reasoning_step = f"Reasoning: {match[:100]}"
                    if reasoning_step not in reasoning_steps:
                        reasoning_steps.append(reasoning_step)
    
    print(f"🔧 [EXTRACT] Found reasoning steps: {len(reasoning_steps)}")
    return reasoning_steps


def calculate_confidence_from_execution(state: GAIAInternalState, tools_used: List[str], reasoning_steps: List[str]) -> float:
    """Calcola confidence basato sull'esecuzione effettiva"""
    base_confidence = 0.5

    # Boost se abbiamo una final answer chiara
    if state.messages and "FINAL ANSWER:" in str(state.messages[-1].content):
        base_confidence += 0.3

    # Boost se abbiamo usato tools appropriati
    if tools_used:
        base_confidence += min(len(tools_used) * 0.1, 0.3)

    # Boost se abbiamo reasoning steps
    if reasoning_steps:
        base_confidence += min(len(reasoning_steps) * 0.05, 0.2)

    # Penalizza errori
    base_confidence -= (state.error_count * 0.1)

    return max(0.0, min(1.0, base_confidence))


# 🏗️ Build Graph
def create_tracked_graph():
    builder = StateGraph(
        GAIAInternalState,
        # input=GAIAInputState,
        config_schema=Configuration
    )

    # Add nodes
    builder.add_node("call_model", call_model_with_tracking)
    builder.add_node("tools", TrackedToolNode(TOOLS))
    builder.add_node("prepare_output", prepare_clean_output)

    # ⚠️ Fix gli edges:
    builder.add_edge("__start__", "call_model")
    builder.add_conditional_edges(
        "call_model",
        route_model_output_tracked,
        # ✅ Aggiungi mapping esplicito:
        {
            "tools": "tools",
            "prepare_output": "prepare_output"
        }
    )
    builder.add_edge("tools", "call_model")
    builder.add_edge("prepare_output", "__end__")  # ✅ Questo era mancante?

    return builder.compile(name="TrackedGAIA-Agent")


# Create the graph instance
tracked_graph = create_tracked_graph()
