import uvicorn
from flask import Flask, render_template, request, session
from asgiref.wsgi import WsgiToAsgi
from .start_bot import one_title
import secrets

def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)

    @app.route("/", methods=["GET", "POST"])
    def index():
        workflow = None
        if request.method == "POST":
            title = request.form.get("title")
            if title:
                workflow = one_title(title)
        return render_template("index.html", workflow=workflow)

    return app

def main():
    app = create_app()
    asgi_app = WsgiToAsgi(app)
    uvicorn.run(asgi_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()