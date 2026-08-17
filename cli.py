import argparse
import sys
import uuid
from db import init_db
from pipeline import ResearchPipeline

def main():
    parser = argparse.ArgumentParser(description="Autonomous Research Agent - NVIDIA NIM & SQLite Evidence Store")
    parser.add_argument("--query", "-q", type=str, required=True, help="Research question or topic")
    parser.add_argument("--fast-model", type=str, default=None, help="Fast LLM model for triage & claim extraction")
    parser.add_argument("--strong-model", type=str, default=None, help="Strong LLM model for synthesis & contradiction analysis")
    parser.add_argument("--max-rounds", type=int, default=None, help="Max search loop rounds")
    parser.add_argument("--max-sources", type=int, default=None, help="Max unique sources to scrape")
    
    args = parser.parse_args()
    
    init_db()
    
    session_id = str(uuid.uuid4())
    config_override = {}
    if args.fast_model:
        config_override["fast_model"] = args.fast_model
    if args.strong_model:
        config_override["strong_model"] = args.strong_model
    if args.max_rounds:
        config_override["max_rounds"] = args.max_rounds
    if args.max_sources:
        config_override["max_sources"] = args.max_sources

    print("\n" + "="*70)
    print(" 🤖 AUTONOMOUS RESEARCH AGENT")
    print(f" Session ID: {session_id}")
    print(f" Query: {args.query}")
    print("="*70 + "\n")

    try:
        pipeline = ResearchPipeline(session_id=session_id, query=args.query, config_override=config_override)
        report_markdown = pipeline.run()

        print("\n" + "="*70)
        print(" 📄 FINAL SYNTHESIZED REPORT")
        print("="*70 + "\n")
        print(report_markdown)
        print("\n" + "="*70)
        print(f" Saved SQLite DB & HTML/MD report files for session {session_id}")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Research pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
