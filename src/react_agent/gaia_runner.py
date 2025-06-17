"""Orchestrazione per il benchmark GAIA"""

import aiohttp
import asyncio
from typing import List, Dict, Any
from react_agent.graph import graph
import json
from datetime import datetime

from dotenv import load_dotenv
import os


# DEBUG: Verifica che il graph sia importato correttamente
print(f"🔧 DEBUG: Graph imported: {graph}")
print(f"🔧 DEBUG: Graph type: {type(graph)}")


async def fetch_all_questions() -> List[Dict[str, Any]]:
    """Fetch tutte le domande GAIA"""
    url = "https://agents-course-unit4-scoring.hf.space/questions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Errore nel fetch: {response.status}")
            return await response.json()


async def solve_gaia_question(question: Dict[str, Any]) -> str:
    """Risolve una singola domanda GAIA usando il graph esistente"""
    print(f"🔧 DEBUG: Starting to solve question...")
    print(f"🔧 DEBUG: Task ID: {question['task_id']}")
    print(f"🔧 DEBUG: Question text: {question['question'][:100]}...")

    # Verifica se c'è un file allegato
    has_file = question.get('file_name') and question['file_name'].strip()
    print(f"🔧 DEBUG: Has attached file: {has_file}")
    if has_file:
        print(f"🔧 DEBUG: File name: {question['file_name']}")

    # Prova a caricare esplicitamente il .env
    load_dotenv()
    print(
        f"🔧 DEBUG: After load_dotenv - OPENAI_API_KEY: {'OPENAI_API_KEY' in os.environ}")

    # Costruisci il messaggio completo per l'agente
    question_text = question["question"]

    # Se c'è un file, aggiungi le istruzioni specifiche
    if has_file:
        question_text += f"\n\n=== ATTACHED FILE INFORMATION ===\n"
        question_text += f"File: {question['file_name']}\n"
        question_text += f"Task ID: {question['task_id']}\n"
        question_text += f"INSTRUCTIONS:\n"
        question_text += f"1. First use download_gaia_file('{question['task_id']}') to download this file\n"
        question_text += f"2. Then analyze the downloaded file using the appropriate tool\n"
        question_text += f"3. Answer the question based on the file content\n"

        print(f"🔧 DEBUG: Enhanced question with file instructions")

    try:
        print(f"🔧 DEBUG: Invoking graph...")

        result = await graph.ainvoke({
            # ← Ora usa question_text invece di question["question"]
            "messages": [("user", question_text)]
        })

        print(f"🔧 DEBUG: Graph completed!")
        print(f"🔧 DEBUG: Result type: {type(result)}")
        print(
            f"🔧 DEBUG: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")

        if "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            print(f"🔧 DEBUG: Response preview: {response[:200]}...")
            return response
        else:
            print(f"🔧 DEBUG: No messages in result!")
            return "ERROR: No messages in graph result"

    except Exception as e:
        print(f"🔧 DEBUG: Exception occurred: {str(e)}")
        print(f"🔧 DEBUG: Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return f"Errore nella risoluzione: {str(e)}"


def is_valid_answer(response: str) -> bool:
    """Verifica se la risposta contiene FINAL ANSWER"""
    return "FINAL ANSWER:" in response.upper()


def extract_final_answer(response: str) -> str:
    """Estrae solo la parte dopo FINAL ANSWER:"""
    if "FINAL ANSWER:" in response.upper():
        # Trova la posizione di "FINAL ANSWER:" (case insensitive)
        pos = response.upper().find("FINAL ANSWER:")
        return response[pos + len("FINAL ANSWER:"):].strip()
    return response.strip()


async def submit_answers(answers: List[Dict[str, str]], username: str = "your_username") -> Dict[str, Any]:
    """Submit delle risposte all'API GAIA"""
    url = "https://agents-course-unit4-scoring.hf.space/submit"
    payload = {
        "username": username,
        "agent_code": "react_agent_v1",
        "answers": answers
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"Submit failed: {response.status}"}


async def run_all_gaia_tasks(username: str = "your_username", max_questions: int = None) -> Dict[str, Any]:
    """Risolve automaticamente tutte (o alcune) task GAIA"""

    print("🚀 Starting GAIA benchmark run...")

    # 1. Fetch tutte le domande
    print("📥 Fetching questions...")
    questions = await fetch_all_questions()

    if max_questions:
        questions = questions[:max_questions]
        print(f"🎯 Processing first {max_questions} questions")
    else:
        print(f"📊 Processing all {len(questions)} questions")

    answers = []

    for i, question in enumerate(questions, 1):
        print(f"\n🔍 Question {i}/{len(questions)}: {question['task_id']}")
        print(f"❓ {question['question'][:100]}...")

        # 2. Risolvi ogni domanda
        response = await solve_gaia_question(question)

        # ✅  DELAY PER LIMITI DI RATE
        if i < len(questions):  # Non aspettare dopo l'ultima domanda
            print("⏱️ Waiting 5 seconds to avoid rate limit...")
            await asyncio.sleep(5)  # 5 secondi tra domande

        # 3. Verifica se la risposta è valida
        if is_valid_answer(response):
            final_answer = extract_final_answer(response)
            print(f"✅ Answer: {final_answer}")
        else:
            print(f"⚠️  No FINAL ANSWER found, using full response")
            final_answer = response.strip()

        answers.append({
            "task_id": question["task_id"],
            "submitted_answer": final_answer
        })

    # 4. Submit tutte le risposte
    print(f"\n📤 Submitting {len(answers)} answers...")
    result = await submit_answers(answers, username)

    print("✅ Completed GAIA benchmark!")
    return result
