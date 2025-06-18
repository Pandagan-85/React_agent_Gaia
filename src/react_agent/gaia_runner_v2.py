"""GAIA Runner con API pulita"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List

from react_agent.graph_v2 import tracked_graph
from react_agent.state_v2 import GAIAInputState, GAIAOutputState


class CleanGAIARunner:
    """🎯 API pulita per eseguire task GAIA"""
    
    def __init__(self):
        self.graph = tracked_graph
    
    async def solve_question(self, question: str, task_id: str = "", file_name: str = "") -> GAIAOutputState:
        """Risolve una singola domanda GAIA"""

        print(f"\n🔧 [RUNNER] Input ricevuto:")
        print(f"  - question: '{question[:50]}...'")
        print(f"  - task_id: '{task_id}' (len: {len(task_id)})")
        print(f"  - file_name: '{file_name}' (len: {len(file_name)})")
        
        # Prepara messaggio con contesto
        enhanced_question = self._enhance_question(question, task_id, file_name)
        
        # Timing
        start_time = datetime.now()

        # ✅ Crea DIRETTAMENTE GAIAInternalState invece di dict
        from react_agent.state_v2 import GAIAInternalState
        
        internal_state = GAIAInternalState(
            messages=[("user", enhanced_question)],
            task_id=task_id,
            has_file=bool(file_name),
            file_name=file_name,
            start_time=start_time
        )

        print(f"\n🔧 [RUNNER] GAIAInternalState creato:")
        print(f"  - task_id: '{internal_state.task_id}'")
        print(f"  - has_file: {internal_state.has_file}")
        print(f"  - file_name: '{internal_state.file_name}'")
        
        try:
            # ✅ Passa l'oggetto stato direttamente
            result = await self.graph.ainvoke(internal_state)
            print(f"\n🔧 [RUNNER] Graph completato, result keys: {list(result.keys())}")
            
            # Gestisci output
            if "clean_output" in result:
                final_result = result["clean_output"]
                print(f"\n🔧 [RUNNER] Using clean_output")
            else:
                print(f"\n🔧 [RUNNER] Using fallback_output")
                final_result = self._fallback_output(result, task_id, start_time)
            
            # Debug del risultato finale
            print(f"\n🔧 [RUNNER] Final result task_id: '{final_result.task_id}'")
            return final_result
                
        except Exception as e:
            print(f"\n🔧 [RUNNER] Error occurred: {e}")
            return self._error_output(str(e), task_id, start_time)
    
    def _enhance_question(self, question: str, task_id: str, file_name: str) -> str:
        """Enhancer la domanda con contesto file se necessario"""
        enhanced = question
        
        if file_name:
            enhanced += f"\n\n=== ATTACHED FILE ===\n"
            enhanced += f"File: {file_name}\n"
            enhanced += f"Task ID: {task_id}\n"
            enhanced += f"Use download_gaia_file('{task_id}') to access this file.\n"
        
        return enhanced
    
    def _fallback_output(
        self, 
        result: Dict[str, Any], 
        task_id: str, 
        start_time: datetime
    ) -> GAIAOutputState:
        """Fallback se non abbiamo clean_output"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        final_answer = ""
        if "messages" in result and result["messages"]:
            content = result["messages"][-1].content
            if "FINAL ANSWER:" in content:
                final_answer = content.split("FINAL ANSWER:")[-1].strip()
            else:
                final_answer = content
        
        return GAIAOutputState(
            messages=result.get("messages", []),
            final_answer=final_answer,
            task_id=task_id,
            submitted_answer=final_answer,
            processing_time=processing_time,
            confidence=0.5  # Default
        )
    
    def _error_output(
        self, 
        error_msg: str, 
        task_id: str, 
        start_time: datetime
    ) -> GAIAOutputState:
        """Output in caso di errore"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return GAIAOutputState(
            final_answer=f"ERROR: {error_msg}",
            task_id=task_id,
            submitted_answer="ERROR",
            processing_time=processing_time,
            confidence=0.0,
            errors_encountered=1
        )