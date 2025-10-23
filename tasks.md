# Task 1

1. In `CopySvgTranslate/start_bot.py` (or a new module like `CopySvgTranslate/webapp.py`), create a `create_app()` function that initializes a Flask application and replace the direct `main()` call with an `if __name__ == "__main__":` guard.
2. Add a `/` route that serves a GET/POST form asking the user for a `title`, and store the value (e.g., in a session or queue).
3. Wrap the Flask app with `WsgiToAsgi` from `asgiref.wsgi` (or use an ASGI-compatible framework like Quart) to run it on an ASGI server such as `uvicorn`.
4. Provide a new `main()` function or a separate run script that initializes the app and starts the server (e.g., `uvicorn CopySvgTranslate.start_bot:create_asgi_app`).

---

# Task 2

1. Modify `one_title` in `CopySvgTranslate/start_bot.py` to structure the workflow into a list of dictionaries containing the stage name, status, and message.
2. Return the final results (e.g., uploaded files, number of files without paths, new translations) as a dictionary to be consumed by the web interface instead of relying on `print`.
3. Add structured error handling that returns messages which can be displayed to the user if any stage fails.
4. Update any other calls to `one_title` to work with the new return value (e.g., in the new route or in existing tests).

---

# Task 3

1. Add a `templates/` folder (inside the same package) containing an `index.html` file that uses Bootstrap 5.3 via CDN.
2. Design the page to include a title input form and a section that displays workflow stages using progress bars or cards based on the data returned by `one_title`.
3. Add a secondary API route (or use AJAX) to fetch the task status periodically, allowing the progress interface to update without a full page reload.
4. Test the layout on different screen sizes to ensure Bootstrap responsiveness.
