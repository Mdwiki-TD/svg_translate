from app import create_app

if __name__ == "__main__":
    # Optional: run with uvicorn if available; otherwise, fallback to Flask dev server
    try:
        import uvicorn

        uvicorn.run("webapp:create_asgi_app", host="127.0.0.1", port=8200, factory=True)
    except ImportError:
        print("Uvicorn not installed")

    except Exception:
        app = create_app()
        app.run(host="127.0.0.1", port=8200, debug=True)
