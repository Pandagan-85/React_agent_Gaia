"""Script principale per eseguire il benchmark GAIA"""

from react_agent.gaia_runner import run_all_gaia_tasks
import asyncio
import os
import sys


async def main():
    """Entry point principale"""

    # Configurazione
    USERNAME = "pandagan"  # ← Cambia con il tuo username
    MAX_QUESTIONS = 20  # ← Per testing, usa None per tutte le domande

    try:
        result = await run_all_gaia_tasks(
            username=USERNAME,
            max_questions=MAX_QUESTIONS
        )

        print(f"\n🎉 Results: {result}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
