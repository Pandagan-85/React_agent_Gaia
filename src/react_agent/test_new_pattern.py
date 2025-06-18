"""Test del nuovo pattern Input → Internal → Output"""

import asyncio
from gaia_runner_v2 import CleanGAIARunner


async def test_clean_api():
    """Test dell'API pulita"""

    runner = CleanGAIARunner()

    # Test question semplice
    result = await runner.solve_question(
        question="What is 2 + 2?",
        task_id="math-001"
    )

    print("=== TEST RESULTS ===")
    print(f"✅ Final Answer: {result.final_answer}")
    print(f"✅ Confidence: {result.confidence}")
    print(f"✅ Processing Time: {result.processing_time:.2f}s")
    print(f"✅ Tools Used: {result.tools_used}")
    print(f"✅ Steps Taken: {result.steps_taken}")
    print(f"✅ Task ID: {result.task_id}")

    print("\n=== REASONING TRACE ===")
    print(result.reasoning_trace)

    # Verifica che l'API sia pulita
    print(f"\n=== CLEAN API CHECK ===")
    print(f"Type: {type(result)}")
    print(f"Fields: {result.__dataclass_fields__.keys()}")

if __name__ == "__main__":
    asyncio.run(test_clean_api())
