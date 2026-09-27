# cli.py — command-line interface for PulseETL

import sys
import argparse

def cmd_init_db(args):
    from db.connection import init_db
    from pipeline.load import seed_cities
    from config import CITIES
    init_db()
    seed_cities(CITIES)

def cmd_run(args):
    from pipeline.orchestrator import run_pipeline
    result = run_pipeline()
    sys.exit(0 if result["status"] == "success" else 1)

def cmd_backfill(args):
    from pipeline.orchestrator import run_backfill
    result = run_backfill(days=args.days)
    sys.exit(0 if result["status"] == "success" else 1)

def cmd_serve(args):
    import threading
    import uvicorn
    from pipeline.scheduler import build_scheduler

    # Start background scheduler
    scheduler = build_scheduler()
    scheduler.start()
    print(f"Scheduler started — pipeline runs every {__import__('config').SCHEDULE_INTERVAL_HOURS}h")

    # Start FastAPI
    from config import API_HOST, API_PORT
    print(f"API →  http://localhost:{API_PORT}")
    print(f"Docs → http://localhost:{API_PORT}/docs")
    print(f"Dashboard → http://localhost:{API_PORT}/dashboard\n")

    try:
        uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=False)
    finally:
        scheduler.shutdown()


def main():
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="PulseETL — weather intelligence pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init-db
    p_init = sub.add_parser("init-db", help="Create database schema and seed cities")
    p_init.set_defaults(func=cmd_init_db)

    # run
    p_run = sub.add_parser("run", help="Run one extract→transform→load cycle")
    p_run.set_defaults(func=cmd_run)

    # backfill
    p_back = sub.add_parser("backfill", help="Load historical data via archive API")
    p_back.add_argument("--days", type=int, default=30, help="Number of days to backfill (default: 30)")
    p_back.set_defaults(func=cmd_backfill)

    # serve
    p_serve = sub.add_parser("serve", help="Start API server + background scheduler")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
