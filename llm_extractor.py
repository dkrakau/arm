import argparse
import csv
import json
import math
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Konfiguration - hier anpassen
# ---------------------------------------------------------------------------

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# Exakten Modell-Tag mit `ollama list` bzw. `ollama show qwen3.8:27b` pruefen
# (Hybrid-Architektur: Gated DeltaNet + Gated Attention, KV-Cache waechst
# dadurch vermutlich moderater mit der Kontextlaenge als bei einem klassischen
# dichten Transformer -- die MAX_CTX-Schaetzung unten ist entsprechend
# konservativ, kann bei Bedarf nach einem Testlauf hochgesetzt werden).
MODEL_NAME = "qwen3.8:27b"

# Wie viele Zeichen des Artikels an das Modell geschickt werden.
# Angepasst an die kompakte Artikelversion (max. 50.000 Zeichen).
MAX_CHARS = 50000

# Sicherheitsaufschlag für Prompt-Text + gewünschte Antwortlänge (in Tokens)
CTX_BUFFER_TOKENS = 1500
# Obergrenze für num_ctx. 50000 Zeichen ~= 14500 Tokens; zusammen mit
# System-/User-Prompt-Overhead und grosszuegiger Reserve fuer Denkschritt +
# Antwort (siehe OUTPUT_RESERVE_TOKENS) ergibt das ~22000-23000 Tokens
# Bedarf. Bei 24GB VRAM (RX 7900 XTX) und qwen3.8:27b (Q4_K_M, hybride
# Architektur mit sparsamem KV-Cache-Wachstum, native 262k Kontextlaenge)
# passt das komfortabel:
#   export OLLAMA_KV_CACHE_TYPE=q8_0
# VOR dem Start von `ollama serve` setzen -- reduziert den VRAM-Bedarf des
# Kontextfensters zusaetzlich. Ohne diese Einstellung ggf. reduzieren oder
# pruefen, ob `ollama ps` einen CPU-Anteil zeigt.
MAX_CTX = 28000

TIMEOUT = 600  # Sekunden pro Anfrage (lange Texte / große Modelle brauchen Zeit)

# WICHTIG: Dieser Wert wird NICHT mehr als API-Parameter "num_predict"
# gesendet (harte Obergrenze), sondern nur zur Berechnung von num_ctx
# verwendet (siehe estimate_num_ctx). Grund: qwen3.8:27b ist ein
# "Thinking"-Modell und verbraucht bei komplexen Extraktionen oft mehrere
# tausend Tokens allein fuer den <think>-Denkschritt. Ein hartes
# num_predict-Limit wuerde dieses Budget zuerst verbrauchen und die
# eigentliche JSON-Antwort abschneiden -> leeres content-Feld (bekannter,
# mehrfach dokumentierter Ollama-Bug bei Thinking-Modellen). Die
# Generierung wird stattdessen nur ueber den TIMEOUT (Wall-Clock) und
# num_ctx (Kontextfenster) begrenzt.
OUTPUT_RESERVE_TOKENS = 6000

# Feste Kategorien fuer research_field und paper_type. Anpassen/erweitern,
# falls dein Korpus weitere Faelle abdecken muss.
RESEARCH_FIELDS = [
    "Computer Science",
    "Medicine",
    "Biology",
    "Geology",
    "Physics",
    "Chemistry",
    "Mathematics",
    "Geography",
    "Engineering",
    "Social Sciences",
    "Economics",
    "Other",
]

PAPER_TYPES = [
    "Survey/Review",
    "System/Tool Paper",
    "Benchmark/Evaluation Paper",
    "Position/Vision Paper",
    "Case Study/Application Paper",
    "Other",
]

RELEVANCE_TYPES = ["high", "middle", "low"]

# JSON-Schema-Felder mit ihrem erwarteten Typ, fuer Validierung nach dem Parsen.
# "str" -> darf String ODER null sein. "list" -> muss eine Liste sein (ggf. leer).
SCHEMA = {
    "research_field": "str",  # fachliche Disziplin, siehe RESEARCH_FIELDS
    "paper_type": "str",  # Art des Papers, siehe PAPER_TYPES
    "relevance": "str",  # Relevanz des Papers: high, middle, low
    "relevance_reason": "str",  # 1-2 Saetze Begruendung der Relevanz-Einstufung
    "research_focus": "str",  # zentrales Thema/Problem/Fragestellung des Papers
    "method": "str",  # Ansatz/Methode, mit der das Problem geloest wurde
    "mentioned_systems": "list",
    "indexing_methods": "list",
    "application_domain": "str",  # Anwendungsbereich INNERHALB des Papers, z.B. NLP, Bildsuche
    "results_summary": "str",  # 3-5 Saetze: wie wurde das Problem geloest, was kam raus
    "limitations": "list",  # einzelne genannte Limitationen als Liste
    "research_gaps": "list",  # einzelne offene Fragen/Future Work als Liste
}

SYSTEM_PROMPT = """You are a meticulous research assistant helping to compile a survey paper on \
the current state of research on vector databases. Your most important task is to judge how \
relevant each paper is for this survey. The papers may be written in English or German and may \
come from many academic disciplines -- vector databases are applied as a tool across many fields \
(e.g. medicine, geology, biology), not only computer science.

Relevance criteria -- the only question is how much the paper is ABOUT vector databases \
themselves (including their core technology: vector indexing and similarity / nearest neighbor \
search). Judge the paper's actual subject, not how often keywords appear:
- "high": Vector databases are the MAIN SUBJECT of the paper. The paper proposes, improves, \
analyzes, benchmarks, or surveys vector databases or their core technology.
- "middle": Vector databases are a SUBSTANTIAL PART of the paper but not its main subject. The \
main subject is something else (e.g. an AI application, a RAG pipeline, a domain-specific \
system), but the paper examines or discusses the vector database in real depth, e.g. compares \
systems or index types, or reports measurements about it.
- "low": The paper is mainly about another topic, e.g. AI, large language models, machine \
learning, embeddings, or a domain application. Vector databases are only used as a tool or \
mentioned in passing, or not addressed at all.
A paper about AI, LLMs, or RAG is NOT relevant just because it uses a vector database. \
If you are torn between two levels, choose the lower one.

Rules you MUST follow:
1. Base every field STRICTLY on what is explicitly stated in the given text. Never use outside \
knowledge, never guess, never infer information the text does not state.
2. Always write the extracted content in English, regardless of the source language.
3. Keep system, tool, and method names in their original form (e.g. "HNSW", "FAISS", "Milvus") \
- never translate or rephrase these names.
4. For "research_field", choose EXACTLY ONE value from this list: {research_fields}.
5. For "paper_type", choose EXACTLY ONE value from this list: {paper_types}.
6. For "relevance", choose EXACTLY ONE value from this list: {relevance_types}, applying the \
relevance criteria above.
7. "relevance_reason" must be 1 to 2 sentences naming the specific aspect of the paper that \
justifies the chosen relevance level. It is never null.
8. List fields ("mentioned_systems", "indexing_methods", "limitations", "research_gaps") must \
always be a JSON array. Use an empty array [] if nothing relevant is found - never use null or \
the string "null" for a list field. Each list item should be a short, self-contained phrase \
(e.g. one limitation per item, not a merged paragraph).
9. Free-text string fields ("research_focus", "method", "application_domain") must be null (JSON \
null, not an empty string) if the text does not address that aspect at all, and should be kept \
to at most 3 short sentences.
10. "results_summary" is the one exception to rule 9's length limit: it must be 3 to 5 sentences \
describing how the paper's research focus was addressed and what the results were.
11. Output ONLY a single valid JSON object. No markdown fences, no commentary, no text before \
or after the JSON.
""".format(
    research_fields=", ".join(RESEARCH_FIELDS),
    paper_types=", ".join(PAPER_TYPES),
    relevance_types=", ".join(RELEVANCE_TYPES),
)

USER_PROMPT_TEMPLATE = """Extract the following information from the paper text below and \
respond with a JSON object using EXACTLY these keys:

{{
    "research_field": "the paper's academic discipline, one value from: __RESEARCH_FIELDS__",
    "paper_type": "the type of paper, one value from: __PAPER_TYPES__",
    "research_focus": "the central topic, problem, or research question the paper addresses (for surveys/reviews: the scope of what is covered)",
    "method": "the method/approach used to address the research focus",
    "mentioned_systems": ["concrete systems/tools named, e.g. FAISS, Milvus, Qdrant"],
    "indexing_methods": ["indexing methods named, e.g. HNSW, IVF, PQ, LSH"],
    "application_domain": "the domain vector search is applied to WITHIN the paper, e.g. NLP, image search, bioinformatics, geospatial data",
    "results_summary": "3-5 sentences: how the research focus was addressed and what the results/findings were",
    "limitations": ["each limitation explicitly mentioned by the authors, as a separate item"],
    "research_gaps": ["each open question/future work item explicitly named by the authors, as a separate item"],
    "relevance_reason": "1-2 sentences: which aspect of the paper justifies the relevance level",
    "relevance": "relevance for the survey according to the relevance criteria, one value from: __RELEVANCE_TYPES__"
}}

Paper text:
---
{text}
---
"""

# Feste Kategorienlisten in den Platzhalter-Text einsetzen (per .replace(),
# NICHT .format(), damit die JSON-Klammern {{ }} und der spaetere {text}-
# Platzhalter fuer build_messages() unangetastet bleiben).
USER_PROMPT_TEMPLATE = (
    USER_PROMPT_TEMPLATE.replace("__RESEARCH_FIELDS__", ", ".join(RESEARCH_FIELDS))
    .replace("__PAPER_TYPES__", ", ".join(PAPER_TYPES))
    .replace("__RELEVANCE_TYPES__", ", ".join(RELEVANCE_TYPES))
)


def build_messages(text: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
    ]


def estimate_num_ctx(messages: list) -> int:
    # Grobe Schaetzung: ~3.5 Zeichen/Token bei gemischt deutsch/englischem Text
    total_chars = sum(len(m["content"]) for m in messages)
    est_tokens = (
        math.ceil(total_chars / 3.5) + CTX_BUFFER_TOKENS + OUTPUT_RESERVE_TOKENS
    )
    return min(est_tokens, MAX_CTX)


def _request_ollama(messages: list, think: bool) -> dict:
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",  # zwingt (bei unterstuetzten Modellen) zu validem JSON
        "think": think,
        "options": {
            "temperature": 0.0,
            "num_ctx": estimate_num_ctx(messages),
            # KEIN num_predict-Limit setzen! Das war die tatsaechliche
            # Ursache fuer "Leere Antwort vom Modell erhalten": qwen3.8:27b
            # verbraucht als Thinking-Modell bei komplexen Extraktionen oft
            # mehrere tausend Tokens allein fuer den <think>-Denkschritt.
            # Ein hartes num_predict-Limit (wie zuvor 1500) wird dabei
            # komplett vom Denkschritt aufgebraucht, bevor die eigentliche
            # JSON-Antwort geschrieben wird -> content bleibt leer. Ohne
            # dieses Limit generiert das Modell, bis es fertig ist oder
            # num_ctx/TIMEOUT erreicht wird.
        },
    }
    resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["message"]


def call_ollama(messages: list) -> str:
    # 1. Versuch: think=True lassen (nicht False setzen) -- bekannter Bug in
    # der qwen35-Architekturfamilie, bei dem think=False dazu fuehrt, dass
    # "format": "json" ignoriert wird und Fliesstext statt JSON kommt.
    message = _request_ollama(messages, think=True)
    content = message.get("content", "")

    if not content.strip():
        # Fallback-Versuch: sollte trotz num_predict-Entfernung doch nochmal
        # eine leere Antwort kommen, mit think=False erneut versuchen. Damit
        # riskieren wir, dass "format": "json" nicht sauber greift (bekannter
        # Bug) -- der Regex-Fallback in parse_response() faengt das aber
        # i.d.R. ab, solange ein JSON-Objekt irgendwo im Text steht.
        message = _request_ollama(messages, think=False)
        content = message.get("content", "")

    if not content.strip():
        thinking_preview = (message.get("thinking") or "")[:200]
        raise RuntimeError(
            f"Leere Antwort vom Modell erhalten (auch nach Retry mit think=False). "
            f"Denkschritt-Vorschau: {thinking_preview!r}"
        )
    return content


def validate_and_clean(result: dict) -> dict:
    """Erzwingt die im SCHEMA definierten Typen, damit CSV/Auswertung nicht bricht."""
    cleaned = {}
    for key, kind in SCHEMA.items():
        val = result.get(key)
        if kind == "list":
            if not isinstance(val, list):
                val = [] if val in (None, "null", "") else [str(val)]
        else:  # "str"
            if isinstance(val, list):
                val = "; ".join(str(v) for v in val) if val else None
            elif val in ("", "null"):
                val = None
        cleaned[key] = val
    return cleaned


def parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Kein gueltiges JSON: {raw[:300]!r}")


def extract_work_id(path: Path) -> str:
    """Extrahiert die ID aus dem Dateinamen: alles vor dem ersten Punkt.
    z.B. 'W2026383861.compact.txt' -> 'W2026383861'."""
    return path.name.split(".")[0]


def process_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    truncated = text[:MAX_CHARS]
    messages = build_messages(truncated)
    raw = call_ollama(messages)
    result = parse_response(raw)
    result = validate_and_clean(result)

    # Zusaetzlich das vollstaendige, unveraenderte JSON sichern (z.B. fuer
    # spaetere erneute Auswertung), bevor Listen fuer die CSV zu Strings
    # zusammengefasst werden.
    result_json = json.dumps(result, ensure_ascii=False)

    for key, kind in SCHEMA.items():
        if kind == "list":
            result[key] = "; ".join(result[key]) if result[key] else ""

    result["work_id"] = extract_work_id(path)
    result["zeichen_gesamt"] = len(text)
    result["zeichen_verwendet"] = len(truncated)
    result["raw_json"] = result_json
    return result


def load_already_done(output_path: Path) -> set:
    if not output_path.exists():
        return set()
    done = set()
    with output_path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row.get("work_id"))
    return done


def main():
    parser = argparse.ArgumentParser(
        description="Kategorisiert Artikel-Volltexte via lokalem LLM (Ollama)."
    )
    parser.add_argument(
        "input_dir", type=Path, help="Ordner mit den .txt-Artikeldateien"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("kategorien.csv"), help="Ziel-CSV"
    )
    args = parser.parse_args()

    start_timestamp = time.time()
    start_time = datetime.fromtimestamp(
        start_timestamp, tz=ZoneInfo("Europe/Berlin")
    ).strftime("%Y-%m-%d_%H-%M-%S")
    print(f"Start time: {start_time}")

    files = sorted(args.input_dir.glob("*.txt"))
    if not files:
        sys.exit(f"Keine .txt-Dateien in {args.input_dir} gefunden.")

    fieldnames = (
        ["work_id"]
        + list(SCHEMA.keys())
        + ["zeichen_gesamt", "zeichen_verwendet", "raw_json"]
    )

    already_done = load_already_done(args.output)
    write_header = not args.output.exists()

    with args.output.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()

        todo = [p for p in files if extract_work_id(p) not in already_done]
        print(
            f"{len(files)} Dateien gefunden, {len(already_done)} bereits erledigt, {len(todo)} zu verarbeiten.\n"
        )

        for i, path in enumerate(todo, 1):
            print(f"[{i}/{len(todo)}] {path.name} ...", end=" ", flush=True)
            t0 = time.time()
            try:
                result = process_file(path)
                writer.writerow(result)
                f.flush()
                field = result.get("research_field") or "?"
                ptype = result.get("paper_type") or "?"
                print(f"-> {field} / {ptype}  ({time.time() - t0:.1f}s)")
            except Exception as e:
                print(f"FEHLER: {e}")
                writer.writerow(
                    {"work_id": extract_work_id(path), "research_focus": f"FEHLER: {e}"}
                )
                f.flush()

    print(f"\nFertig. Ergebnisse in: {args.output}")

    end_timestamp = time.time()
    end_time = datetime.fromtimestamp(
        end_timestamp, tz=ZoneInfo("Europe/Berlin")
    ).strftime("%Y-%m-%d_%H-%M-%S")
    print(f"Start time: {start_time}")
    print(f"End time:   {end_time}")
    print("Total minutes: %s" % ((end_timestamp - start_timestamp) / 60))


if __name__ == "__main__":
    main()

# py llm_extractor.py grobid/open_access/compact --output llm/llm_open_access_with_relevance.csv
# py llm_extractor.py grobid/not_open_access/compact --output llm/llm_not_open_access_with_relevance.csv
