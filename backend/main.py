"""WSD Backend startup"""

import argparse

from backend.core.bootstrap import create_application
from backend.core.collector_agent import CollectorAgent

def main():
    parser = argparse.ArgumentParser(description="Wise Storage Director")

    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--data-dir",default=None)

    args = parser.parse_args()
    # Initialize the app
    app, core = create_application(demo_mode=args.demo, data_dir=args.data_dir)

    collector = None

    try:
        # Start CORE with linux agent in real mode, start ealier to avoid empty result
        core.start()

        # Start periodic collection only in Real Mode
        if not args.demo:
            collector = CollectorAgent(core, interval_seconds=1)
            collector.start()

        # Start HTTP Server, send msg
        app.run(
            host=args.bind,
            port=args.port,
            debug=False,
            use_reloader=False
        )

    except KeyboardInterrupt:
        print("WSD terminated with Crtl+C event")

    finally:
        # Stop colletion
        if collector is not None:
            collector.stop()

        core.close()

if __name__ == "__main__":
    main()