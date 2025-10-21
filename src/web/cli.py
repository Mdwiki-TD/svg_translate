"""Command-line helpers for SVG Translate web tasks."""

from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext


@click.command("purge-oauth-tokens")
@click.option(
    "--max-age-days",
    default=90,
    show_default=True,
    help="Retain credentials used within this many days.",
    type=int,
)
@with_appcontext
def purge_oauth_tokens(max_age_days: int) -> None:
    """Purge revoked or long-idle OAuth credentials from the store."""

    store = current_app.extensions.get("auth_user_store")
    if store is None:
        raise click.ClickException("OAuth user store is not configured")

    deleted = store.purge_stale(max_age_days=max_age_days)
    click.echo(f"Deleted {deleted} stale OAuth credential(s).")


def init_app(app) -> None:
    """Register CLI commands for the Flask application."""

    app.cli.add_command(purge_oauth_tokens)


__all__ = ["init_app", "purge_oauth_tokens"]
