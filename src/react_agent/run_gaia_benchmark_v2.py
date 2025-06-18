"""Script per eseguire il benchmark GAIA con la V2"""

import asyncio
import aiohttp
from react_agent.gaia_runner_v2 import CleanGAIARunner

from dotenv import load_dotenv 

# ✅ Carica .env all'inizio
load_dotenv()


async def fetch_all_questions():
    """Fetch tutte le domande GAIA"""
    url = "https://agents-course-unit4-scoring.hf.space/questions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Errore nel fetch: {response.status}")
            return await response.json()

async def submit_answers(answers, username="pandagan"):
    """Submit risposte all'API GAIA"""
    url = "https://agents-course-unit4-scoring.hf.space/submit"
    payload = {
        "username": username,
        "agent_code": "react_agent_v2",
        "answers": answers
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"Submit failed: {response.status}"}

async def run_gaia_benchmark_v2(username="pandagan", max_questions=5):
    """Esegui benchmark GAIA con sistema V2"""
    
    print("🚀 Starting GAIA Benchmark V2...")
    
    # 1. Setup
    runner = CleanGAIARunner()
    questions = await fetch_all_questions()
    
    if max_questions:
        questions = questions[:max_questions]
    
    print(f"📊 Processing {len(questions)} questions with V2 system")
    
    # 2. Process each question
    answers = []
    total_processing_time = 0
    
    for i, question in enumerate(questions, 1):
        print(f"\n🔍 Question {i}/{len(questions)}: {question['task_id']}")
        print(f"❓ {question['question'][:100]}...")
        
        # 3. Solve with V2 system
        result = await runner.solve_question(
            question=question['question'],
            task_id=question['task_id'],
            file_name=question.get('file_name', '')
        )
        
        # 4. Extract data from structured output
        print(f"✅ Answer: {result.final_answer}")
        print(f"⏱️  Time: {result.processing_time:.2f}s")
        print(f"🎯 Confidence: {result.confidence:.2f}")
        print(f"🔧 Tools: {', '.join(result.tools_used)}")
        
        total_processing_time += result.processing_time
        
        # 5. Add to submission
        answers.append({
            "task_id": question["task_id"],
            "submitted_answer": result.submitted_answer
        })
        
        # Rate limiting
        if i < len(questions):
            print("⏱️ Waiting 5 seconds...")
            await asyncio.sleep(5)
    
    # 6. Submit results
    print(f"\n📤 Submitting {len(answers)} answers...")
    submission_result = await submit_answers(answers, username)
    
    # 7. Final summary
    avg_time = total_processing_time / len(questions)
    
    print(f"\n🎉 GAIA Benchmark V2 Complete!")
    print(f"📊 Results: {submission_result}")
    print(f"⏱️ Average processing time: {avg_time:.2f}s")
    
    return submission_result

if __name__ == "__main__":
    result = asyncio.run(run_gaia_benchmark_v2(
        username="pandagan",
        max_questions=20  # Per testing
    ))
    print(f"Final result: {result}")