"""Nuovo sistema di stato con Input → Internal → Output"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence, List, Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated


@dataclass
class GAIAInputState:
    """🎯 INPUT: Interface pubblica - solo quello che l'utente fornisce"""
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )


@dataclass
class GAIAInternalState(GAIAInputState):
    """🔧 INTERNAL: Stato completo con tutti i metadati di esecuzione"""
    
    # LangGraph managed
    is_last_step: IsLastStep = field(default=False)
    
    # GAIA task metadata
    task_id: str = ""
    has_file: bool = False
    file_name: str = ""
    difficulty_level: int = 1
    
    # Execution tracking
    tools_used: List[str] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    
    # Results & analysis
    confidence: float = 0.0
    error_count: int = 0
    current_step: str = ""


@dataclass
class GAIAOutputState:
    """📤 OUTPUT: Risultato pulito per il consumer"""
    
    # Core results
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    final_answer: str = ""
    
    # GAIA-specific output
    task_id: str = ""
    submitted_answer: str = ""  # Formato GAIA-compliant
    
    # Execution summary
    reasoning_trace: str = ""
    confidence: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    
    # Debug info (optional)
    steps_taken: int = 0
    errors_encountered: int = 0