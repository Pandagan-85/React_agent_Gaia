"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

from typing import Any, Callable, List, Optional, cast

from langchain_tavily import TavilySearch  # type: ignore[import-not-found]

from react_agent.configuration import Configuration

import aiohttp
import asyncio
import tempfile
import os
from pathlib import Path
import sys
import subprocess
import pandas as pd
import mimetypes
import base64
from PIL import Image


async def search(query: str, fallback_queries: bool = True) -> Optional[dict[str, Any]]:
    """Search con fallback automatico per query che non trovano risultati"""

    configuration = Configuration.from_context()
    wrapped = TavilySearch(max_results=configuration.max_search_results)

    # Prova la query originale
    result = await wrapped.ainvoke({"query": query})

    # Se non trova risultati E fallback_queries è True, prova alternative
    if fallback_queries and (not result or not result.get('results')):
        # Query alternative semplici
        alternative_queries = [
            # Rimuovi virgolette se presenti
            query.replace('"', ''),
            # Rimuovi parole comuni che potrebbero non essere nel testo
            ' '.join([word for word in query.split() if word.lower()
                     not in ['the', 'a', 'an', 'of', 'in', 'on']]),
            # Prendi solo le parole chiave principali
            ' '.join(query.split()[:4]) if len(query.split()) > 4 else query
        ]

        for alt_query in alternative_queries:
            if alt_query != query:  # Evita di ripetere la stessa query
                result = await wrapped.ainvoke({"query": alt_query})
                if result and result.get('results'):
                    break

    return result


async def extract_text_from_url(url: str) -> str:
    """Estrae tutto il testo da una URL - tool generico e semplice"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Errore nell'accesso alla pagina: {response.status}"

                content = await response.text()

                # Parse HTML semplice
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')

                # Rimuovi script e style
                for script in soup(["script", "style"]):
                    script.decompose()

                # Estrai tutto il testo
                text = soup.get_text()

                # Pulisci il testo
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip()
                          for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                # Limita a 50k caratteri per evitare overflow
                return text[:50000]

    except Exception as e:
        return f"Errore nell'estrazione del testo: {str(e)}"


async def download_gaia_file(task_id: str) -> Optional[str]:
    """Download file associato a una domanda GAIA."""
    try:
        url = f"https://agents-course-unit4-scoring.hf.space/files/{task_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # Usa asyncio.to_thread per operazioni I/O sincrone
                    temp_dir = await asyncio.to_thread(tempfile.mkdtemp)  # ✅

                    content_disposition = response.headers.get(
                        'content-disposition', '')
                    filename = content_disposition.split(
                        'filename=')[-1].strip('"') if 'filename=' in content_disposition else f"{task_id}_file"

                    file_path = os.path.join(temp_dir, filename)
                    content = await response.read()

                    # Wrap file operations in asyncio.to_thread
                    # ✅
                    await asyncio.to_thread(_write_file, file_path, content)

                    return file_path
        return None
    except Exception as e:
        return f"Errore nel download: {str(e)}"

# Helper function per scrivere file


def _write_file(file_path: str, content: bytes) -> None:
    """Helper sincrono per scrivere file."""
    with open(file_path, 'wb') as f:
        f.write(content)

# Tool per Python REPL


async def python_repl(code: str) -> str:
    """Esegue codice Python e restituisce il risultato."""
    try:
        # Crea un ambiente isolato per l'esecuzione
        local_vars = {}
        global_vars = {
            '__builtins__': __builtins__,
            'pd': None,  # pandas sarà importato se necessario
        }

        # Importa pandas se il codice lo richiede
        if 'pd.' in code or 'pandas' in code:
            import pandas as pd
            global_vars['pd'] = pd

        # Esegui il codice
        exec(code, global_vars, local_vars)

        # Cerca variabili di output comuni con priorità
        output_vars = ['final_answer', 'result', 'answer', 'output', 'total']

        for var_name in output_vars:
            if var_name in local_vars:
                return str(local_vars[var_name])

        # Se non trova variabili specifiche, cerca l'ultima espressione valutata
        # Riesegui l'ultima linea per catturare il valore di ritorno
        lines = code.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            if last_line and not last_line.startswith('#'):
                try:
                    # Se l'ultima linea è una variabile o espressione, valutala
                    last_result = eval(last_line, global_vars, local_vars)
                    if last_result is not None:
                        return str(last_result)
                except:
                    pass

        # Se tutto fallisce, mostra le variabili disponibili
        available_vars = [
            k for k in local_vars.keys() if not k.startswith('_')]
        if available_vars:
            return f"Codice eseguito. Variabili disponibili: {available_vars}. Valori: {[f'{k}={local_vars[k]}' for k in available_vars[:3]]}"
        else:
            return "Codice eseguito con successo"

    except Exception as e:
        return f"Errore nell'esecuzione: {str(e)}"


async def read_spreadsheet(file_path: str, sheet_name: Optional[str] = None) -> str:
    """Legge file Excel o CSV e restituisce informazioni strutturate."""
    try:
        # Rileva il tipo di file usando la nostra funzione
        file_type = detect_file_type(file_path)
        file_extension = Path(file_path).suffix.lower()

        # Wrap le operazioni pandas in asyncio.to_thread
        if file_extension == '.csv' or file_type == 'text/csv':
            df = await asyncio.to_thread(pd.read_csv, file_path)  # ✅
            sheets_info = ""
        elif file_extension in ['.xlsx', '.xls'] or 'spreadsheet' in file_type:
            # Per Excel, mostra prima i fogli disponibili
            excel_file = await asyncio.to_thread(pd.ExcelFile, file_path)  # ✅
            sheets_info = f"Fogli disponibili: {excel_file.sheet_names}\n"

            # Leggi il foglio specificato o il primo
            if sheet_name:
                # ✅
                df = await asyncio.to_thread(pd.read_excel, file_path, sheet_name=sheet_name)
            else:
                # ✅
                df = await asyncio.to_thread(pd.read_excel, file_path, sheet_name=excel_file.sheet_names[0])
                sheets_info += f"Leggendo foglio: {excel_file.sheet_names[0]}\n"
        else:
            return f"Tipo di file non supportato: {file_extension} (tipo rilevato: {file_type})"

        # Il resto rimane uguale (queste operazioni sono in memoria, non I/O)
        analysis = []
        analysis.append(f"File: {Path(file_path).name}")
        if sheets_info:
            analysis.append(sheets_info)

        analysis.append(
            f"Dimensioni: {df.shape[0]} righe x {df.shape[1]} colonne")
        analysis.append(f"Colonne: {list(df.columns)}")

        # Mostra tipi di dati
        data_types = df.dtypes.to_dict()
        analysis.append(f"Tipi di dati: {data_types}")

        # Mostra prime righe
        analysis.append("\nPrime 5 righe:")
        analysis.append(df.head().to_string())

        # Statistiche per colonne numeriche
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            analysis.append(
                f"\nStatistiche colonne numeriche: {list(numeric_cols)}")
            analysis.append(df[numeric_cols].describe().to_string())

        # Valori mancanti
        missing = df.isnull().sum()
        if missing.sum() > 0:
            analysis.append(
                f"\nValori mancanti: {missing[missing > 0].to_dict()}")

        return "\n".join(analysis)

    except Exception as e:
        return f"Errore nella lettura del file: {str(e)}"


async def analyze_spreadsheet_data(file_path: str, query: str, sheet_name: Optional[str] = None) -> str:
    """Analizza dati di un spreadsheet basandosi su una query specifica."""
    try:
        # Leggi il file con asyncio.to_thread
        file_extension = Path(file_path).suffix.lower()

        if file_extension == '.csv':
            df = await asyncio.to_thread(pd.read_csv, file_path)  # ✅
        elif file_extension in ['.xlsx', '.xls']:
            if sheet_name:
                # ✅
                df = await asyncio.to_thread(pd.read_excel, file_path, sheet_name=sheet_name)
            else:
                df = await asyncio.to_thread(pd.read_excel, file_path)  # ✅
        else:
            return f"Tipo di file non supportato: {file_extension}"

        # Genera codice Python per l'analisi basato sulla query
        analysis_code = f"""
# Dataset caricato con {df.shape[0]} righe e {df.shape[1]} colonne
# Colonne disponibili: {list(df.columns)}

# Query: {query}

# Analisi automatica
import pandas as pd
import numpy as np

df = pd.DataFrame({df.to_dict()})

# Operazioni comuni basate sulla query
if any(word in query.lower() for word in ['somma', 'totale', 'sum', 'total']):
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        result = df[numeric_cols].sum().to_dict()
        print("Somme per colonne numeriche:", result)

if any(word in query.lower() for word in ['media', 'average', 'mean']):
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        result = df[numeric_cols].mean().to_dict()
        print("Medie per colonne numeriche:", result)

if any(word in query.lower() for word in ['conteggio', 'count', 'numero']):
    result = len(df)
    print(f"Numero totale di righe: {{result}}")

if any(word in query.lower() for word in ['massimo', 'max', 'minimo', 'min']):
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        max_vals = df[numeric_cols].max().to_dict()
        min_vals = df[numeric_cols].min().to_dict()
        print("Valori massimi:", max_vals)
        print("Valori minimi:", min_vals)

# Mostra struttura generale
print("\\nInfo generali sul dataset:")
print(f"Dimensioni: {{df.shape}}")
print(f"Colonne: {{list(df.columns)}}")
"""

        # Esegui l'analisi
        return await python_repl(analysis_code)

    except Exception as e:
        return f"Errore nell'analisi: {str(e)}"


# audio analysis tools
async def transcribe_audio(file_path: str, query: Optional[str] = None) -> str:
    """Trascrive file audio usando OpenAI Whisper API"""
    try:
        import openai

        # Verifica che sia un file audio
        file_type = detect_file_type(file_path)
        if not file_type.startswith('audio/'):
            return f"Il file non è audio: {file_type}"

        # Trascrivi usando Whisper
        with open(file_path, "rb") as audio_file:
            transcript = await asyncio.to_thread(
                openai.audio.transcriptions.create,
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        # Se c'è una query specifica, fornisci contesto
        if query:
            result = f"Trascrizione audio:\n{transcript}\n\nRisposta alla domanda '{query}':\n"
            result += f"[Analizza il testo sopra per rispondere]"
            return result

        return f"Trascrizione completa:\n{transcript}"

    except Exception as e:
        return f"Errore nella trascrizione audio: {str(e)}"


# video analysis tools
async def analyze_youtube_video(video_url: str, query: Optional[str] = None) -> str:
    """Analizza video YouTube con approccio ibrido ottimizzato"""
    try:
        print(f"🎥 Analizzando video YouTube: {video_url}")

        # STEP 1: Prova prima i sottotitoli (gratuito)
        transcript = await get_youtube_transcript(video_url)
        if not transcript.startswith("Errore"):
            print("✅ Sottotitoli trovati - usando trascrizione gratuita")
            if query:
                return f"Trascrizione YouTube:\n{transcript}\n\nAnalisi per: '{query}'\n[Analizza il testo sopra per rispondere alla domanda]"
            return f"Trascrizione YouTube completa:\n{transcript}"

        # STEP 2: Solo se fallisce, usa Whisper (a pagamento)
        print("⚠️ Sottotitoli non disponibili, scaricando audio per Whisper...")
        audio_file = await download_youtube_audio(video_url)
        if audio_file and not audio_file.startswith("Errore"):
            result = await transcribe_audio(audio_file, query)
            # Cleanup file temporaneo
            try:
                os.remove(audio_file)
            except:
                pass
            return result

        return "Errore: Impossibile ottenere contenuto audio dal video YouTube"

    except Exception as e:
        return f"Errore nell'analisi del video YouTube: {str(e)}"


async def get_youtube_transcript(video_url: str) -> str:
    """Ottiene sottotitoli esistenti da YouTube - GRATUITO"""
    try:
        def _get_transcript_sync(video_id: str) -> str:
            """Helper sincrono per YouTubeTranscriptApi"""
            from youtube_transcript_api import YouTubeTranscriptApi

            # Prova diverse lingue
            try:
                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=['en'])
            except:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=['it'])
                except:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Combina tutto il testo
            return ' '.join([entry['text'] for entry in transcript])

        import re

        # Estrai video ID da vari formati URL
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]

        video_id = None
        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                video_id = match.group(1)
                break

        if not video_id:
            return "Errore: Impossibile estrarre video ID dall'URL"

        # ✅ Usa asyncio.to_thread per la chiamata bloccante
        text = await asyncio.to_thread(_get_transcript_sync, video_id)
        return text

    except Exception as e:
        return f"Errore sottotitoli: {str(e)}"


async def download_youtube_audio(video_url: str) -> str:
    """Scarica solo l'audio da YouTube per Whisper - versione semplificata"""
    try:
        def _download_audio_sync(video_url: str, temp_dir: str) -> str:
            """Helper sincrono per yt-dlp"""
            import yt_dlp

            # Scarica direttamente in formato audio
            output_path = os.path.join(temp_dir, "audio.%(ext)s")

            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                'outtmpl': output_path,
                'noplaylist': True,
                'quiet': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

                # Trova il file scaricato
                for file in os.listdir(temp_dir):
                    if file.startswith('audio.'):
                        file_path = os.path.join(temp_dir, file)
                        print(
                            f"📁 File scaricato: {file} (tipo: {detect_file_type(file_path)})")
                        return file_path

                return None

        # Crea directory temporanea
        temp_dir = await asyncio.to_thread(tempfile.mkdtemp)

        # ✅ Usa asyncio.to_thread per la chiamata bloccante
        audio_file = await asyncio.to_thread(_download_audio_sync, video_url, temp_dir)

        return audio_file if audio_file else "Errore: Download audio fallito"

    except Exception as e:
        return f"Errore download audio: {str(e)}"

# Image analysis tools


async def analyze_image(file_path: str, query: str) -> str:
    """Analizza un'immagine usando AI vision e risponde a una query specifica.

    Args:
        file_path: Percorso del file immagine
        query: Domanda specifica sull'immagine

    Returns:
        Risposta basata sull'analisi dell'immagine
    """
    try:
        # Controlla che sia effettivamente un'immagine
        file_type = detect_file_type(file_path)
        if not file_type.startswith('image/'):
            return f"Il file non è un'immagine: {file_type}"

        # Leggi e codifica l'immagine
        def encode_image(image_path: str) -> str:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        # Usa asyncio.to_thread per operazioni I/O
        base64_image = await asyncio.to_thread(encode_image, file_path)

        # Configura il client (OpenAI o Anthropic)
        configuration = Configuration.from_context()

        # Opzione 1: OpenAI GPT-4 Vision
        if "openai" in configuration.model.lower():
            import openai

            response = await asyncio.to_thread(
                openai.chat.completions.create,
                model="gpt-4o",  # o gpt-4-vision-preview
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Analizza questa immagine e rispondi alla domanda: {query}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            return response.choices[0].message.content

        # Opzione 2: Anthropic Claude 3
        elif "anthropic" in configuration.model.lower():
            import anthropic

            client = anthropic.Anthropic()

            # Rileva il tipo di immagine per il media_type
            image_format = Path(file_path).suffix.lower().replace('.', '')
            if image_format in ['jpg', 'jpeg']:
                media_type = "image/jpeg"
            elif image_format == 'png':
                media_type = "image/png"
            elif image_format == 'gif':
                media_type = "image/gif"
            else:
                media_type = "image/jpeg"  # fallback

            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-3-sonnet-20240229",  # o claude-3-opus-20240229
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"Analizza questa immagine e rispondi alla domanda: {query}"
                            }
                        ],
                    }
                ],
            )

            return response.content[0].text

        else:
            return "Modello non supportato per l'analisi delle immagini. Usa OpenAI o Anthropic."

    except Exception as e:
        return f"Errore nell'analisi dell'immagine: {str(e)}"


async def describe_image(file_path: str) -> str:
    """Descrive il contenuto di un'immagine in modo generale.

    Args:
        file_path: Percorso del file immagine

    Returns:
        Descrizione dettagliata dell'immagine
    """
    return await analyze_image(file_path, "Descrivi dettagliatamente tutto quello che vedi in questa immagine, inclusi oggetti, persone, testo, colori, e qualsiasi dettaglio rilevante.")
# - fetch data from GAIA


async def fetch_gaia_task(task_id: str) -> str:
    """Recupera una specifica task GAIA."""
    try:
        url = "https://agents-course-unit4-scoring.hf.space/questions"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Errore nel fetch delle domande: {response.status}"

                questions = await response.json()

        # Trova la task
        task = None
        for q in questions:
            if q["task_id"] == task_id:
                task = q
                break

        if not task:
            return f"Task ID {task_id} non trovata."

        # Formatta il prompt - SOLO info specifiche della task
        prompt_parts = []
        prompt_parts.append("=== GAIA TASK ===")
        prompt_parts.append(f"Task ID: {task['task_id']}")
        prompt_parts.append(f"Level: {task['Level']}")
        prompt_parts.append(f"Question: {task['question']}")

        if task.get('file_name') and task['file_name'].strip():
            prompt_parts.append(f"\nFile allegato: {task['file_name']}")
            prompt_parts.append(
                "NOTA: Usa il tool 'download_gaia_file' per scaricare il file se necessario.")
        else:
            prompt_parts.append("\nNessun file allegato.")

        # Le istruzioni generali sono già nel SYSTEM_PROMPT!
        # Non serve ripeterle qui

        return "\n".join(prompt_parts)

    except Exception as e:
        return f"Errore nel fetch della task: {str(e)}"


async def list_gaia_tasks(level: Optional[str] = None, limit: int = 10) -> str:
    """Lista le task GAIA disponibili."""
    try:
        url = "https://agents-course-unit4-scoring.hf.space/questions"

        async with aiohttp.ClientSession() as session:  # ✅
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Errore nel fetch delle domande: {response.status}"

                questions = await response.json()

        # Resto del codice rimane uguale...
        if level:
            questions = [q for q in questions if str(
                q.get('Level')) == str(level)]

        questions = questions[:limit]

        output = []
        output.append(f"=== GAIA TASKS (Prime {len(questions)}) ===")

        for i, task in enumerate(questions, 1):
            has_file = "📎" if task.get(
                'file_name') and task['file_name'].strip() else "📄"
            output.append(
                f"{i}. {has_file} Level {task['Level']} - {task['task_id']}")
            output.append(f"   {task['question'][:100]}...")
            if task.get('file_name') and task['file_name'].strip():
                output.append(f"   File: {task['file_name']}")
            output.append("")

        output.append(
            "Per caricare una task specifica usa: fetch_gaia_task('task_id')")
        return "\n".join(output)

    except Exception as e:
        return f"Errore nel fetch delle task: {str(e)}"


def detect_file_type(file_path: str) -> str:
    """Rileva il tipo di file usando mimetypes invece di magic"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type

    # Fallback basato sull'estensione
    ext = os.path.splitext(file_path)[1].lower()
    type_map = {
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        '.txt': 'text/plain',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.webm': 'audio/webm',
        '.aac': 'audio/aac',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.py': 'text/x-python',
        '.zip': 'application/zip'
    }
    return type_map.get(ext, 'application/octet-stream')


async def analyze_file(file_path: str, query: Optional[str] = None) -> str:
    """Analizza automaticamente un file basandosi sul suo tipo."""
    try:
        file_type = detect_file_type(file_path)
        file_extension = Path(file_path).suffix.lower()

        supported_audio = ['.mp3', '.wav', '.m4a', '.aac', '.flac']
        if file_extension in supported_audio or file_type.startswith('audio/'):
            return await transcribe_audio(file_path, query)

        # ✅ GESTIONE MEDIA NON SUPPORTATI

        unsupported_video = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']

        if file_extension in unsupported_video:
            return f"ERROR: Video file analysis not supported. This agent cannot process video files ({file_extension}). Video analysis tools are not available."

        # Spreadsheet
        if file_extension in ['.csv', '.xlsx', '.xls'] or 'spreadsheet' in file_type or 'csv' in file_type:
            if query:
                return await analyze_spreadsheet_data(file_path, query)
            else:
                return await read_spreadsheet(file_path)

        # Immagini
        elif file_type.startswith('image/'):
            if query:
                return await analyze_image(file_path, query)
            else:
                return await describe_image(file_path)

        elif file_type == 'application/pdf':
            return f"PDF file detected: {Path(file_path).name}\nPDF analysis tool not yet implemented."

        else:
            return f"File type not supported: {file_extension} (type: {file_type})"

    except Exception as e:
        return f"Error analyzing file: {str(e)}"

TOOLS: List[Callable[..., Any]] = [search, download_gaia_file,
                                   python_repl, read_spreadsheet, analyze_spreadsheet_data, fetch_gaia_task, list_gaia_tasks, analyze_file, analyze_image, describe_image, extract_text_from_url, transcribe_audio, analyze_youtube_video, get_youtube_transcript]
