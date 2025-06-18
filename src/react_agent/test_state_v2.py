"""Test minimale per capire il flusso di dati"""

import asyncio
from react_agent.gaia_runner_v2 import CleanGAIARunner

async def minimal_debug():
    runner = CleanGAIARunner()
    
    # Test con dati molto semplici e visibili
    result = await runner.solve_question(
        question="What is 2 + 2?",
        task_id="TEST123",
        file_name="test.txt"
    )
    
    print(f"\n📊 FINAL RESULT:")
    print(f"  - Task ID in result: '{result.task_id}'")
    print(f"  - Expected: 'TEST123'")
    print(f"  - Match: {result.task_id == 'TEST123'}")

if __name__ == "__main__":
    asyncio.run(minimal_debug())