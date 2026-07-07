#!/usr/bin/env python3
"""AWS SSM Parameter Store secrets management CLI for Scryfall MCP Server.

This script provides an interactive interface for managing secrets required
for Remote MCP deployment on AWS Lambda.

Usage:
    python scripts/manage_secrets.py set --stage dev
    python scripts/manage_secrets.py get --stage dev --key JWT_SECRET_KEY
    python scripts/manage_secrets.py list --stage dev
    python scripts/manage_secrets.py delete --stage dev --key JWT_SECRET_KEY
"""

from __future__ import annotations

import secrets
import sys
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("Error: boto3 is required. Install with: uv pip install boto3")
    sys.exit(1)

app = typer.Typer(
    help="Manage AWS SSM Parameter Store secrets for Scryfall MCP Server",
    no_args_is_help=True,
)
console = Console()

# Secret key definitions
SECRET_KEYS = {
    "JWT_SECRET_KEY": {
        "type": "SecureString",
        "description": "JWT signature verification key (256-bit)",
        "generate": True,
    },
    "OAUTH_ISSUER_URL": {
        "type": "String",
        "description": "OAuth 2.1 issuer URL (e.g., https://auth.example.com)",
        "generate": False,
    },
    "SCRYFALL_MCP_USER_AGENT": {
        "type": "String",
        "description": "User-Agent for Scryfall API (AppName/Version contact)",
        "generate": False,
    },
}


def get_ssm_client() -> Any:
    """Get AWS SSM client.

    Returns
    -------
    Any
        AWS Systems Manager client (boto3.client type)

    Raises
    ------
    RuntimeError
        If AWS credentials are not configured
    """
    try:
        return boto3.client("ssm")
    except Exception as error:
        console.print(f"[red]Error: Failed to initialize AWS SSM client: {error}[/red]")
        console.print("\nPlease configure AWS credentials:")
        console.print("  export AWS_ACCESS_KEY_ID=xxx")
        console.print("  export AWS_SECRET_ACCESS_KEY=xxx")
        console.print("  export AWS_DEFAULT_REGION=us-east-1")
        raise RuntimeError("AWS credentials not configured") from error


def get_parameter_name(stage: str, key: str) -> str:
    """Generate SSM parameter name.

    Parameters
    ----------
    stage : str
        Deployment stage (dev, staging, production)
    key : str
        Secret key name

    Returns
    -------
    str
        Full SSM parameter name (e.g., /scryfall-mcp/dev/JWT_SECRET_KEY)
    """
    return f"/scryfall-mcp/{stage}/{key}"


def generate_jwt_secret() -> str:
    """Generate a secure 256-bit JWT secret key.

    Returns
    -------
    str
        Base64-encoded 256-bit secret key
    """
    return secrets.token_urlsafe(32)


def _check_parameter_exists(ssm: Any, param_name: str) -> bool:
    """Check if SSM parameter exists.

    Parameters
    ----------
    ssm : Any
        AWS SSM client
    param_name : str
        Full SSM parameter name

    Returns
    -------
    bool
        True if parameter exists, False otherwise
    """
    try:
        ssm.get_parameter(Name=param_name, WithDecryption=True)
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ParameterNotFound":
            return False
        raise


def _prompt_for_secret_value(key: str, config: dict[str, Any]) -> str:
    """Prompt user for secret value or generate if applicable.

    Parameters
    ----------
    key : str
        Secret key name
    config : dict[str, Any]
        Secret configuration from SECRET_KEYS

    Returns
    -------
    str
        Secret value (prompted or generated)
    """
    if config["generate"]:
        use_generated = typer.confirm(f"Generate secure {key}?", default=True)
        if use_generated:
            secret_value = generate_jwt_secret()
            console.print(
                f"[green]Generated: {key}[/green] (length: {len(secret_value)})"
            )
            return secret_value
        return typer.prompt(f"{key} ({config['description']})", hide_input=True)
    return typer.prompt(f"{key} ({config['description']})")


def _put_parameter(
    ssm: Any, param_name: str, value: str, param_type: str, description: str
) -> None:
    """Put parameter to AWS SSM Parameter Store.

    Parameters
    ----------
    ssm : Any
        AWS SSM client
    param_name : str
        Full SSM parameter name
    value : str
        Secret value
    param_type : str
        SSM parameter type (String or SecureString)
    description : str
        Parameter description

    Raises
    ------
    typer.Exit
        If parameter creation fails
    """
    try:
        ssm.put_parameter(
            Name=param_name,
            Value=value,
            Type=param_type,
            Overwrite=True,
            Description=description,
        )
        console.print(f"[green]✓ Set: {param_name}[/green]")
    except (BotoCoreError, ClientError) as error:
        console.print(f"[red]✗ Failed to set {param_name}: {error}[/red]")
        raise typer.Exit(code=1) from error


def _set_all_secrets(ssm: Any, stage: str) -> None:
    """Set all secrets interactively.

    Parameters
    ----------
    ssm : Any
        AWS SSM client
    stage : str
        Deployment stage
    """
    for secret_key, config in SECRET_KEYS.items():
        param_name = get_parameter_name(stage, secret_key)

        # Check if parameter already exists
        if _check_parameter_exists(ssm, param_name):
            overwrite = typer.confirm(f"'{secret_key}' already exists. Overwrite?")
            if not overwrite:
                console.print(f"[yellow]Skipped: {secret_key}[/yellow]")
                continue

        # Get secret value
        secret_value = _prompt_for_secret_value(secret_key, config)

        # Put parameter
        _put_parameter(
            ssm, param_name, secret_value, config["type"], config["description"]
        )


def _set_single_secret(ssm: Any, stage: str, key: str, value: str | None) -> None:
    """Set a single secret.

    Parameters
    ----------
    ssm : Any
        AWS SSM client
    stage : str
        Deployment stage
    key : str
        Secret key name
    value : str | None
        Secret value (if None, will prompt)

    Raises
    ------
    typer.Exit
        If key is unknown
    """
    if key not in SECRET_KEYS:
        console.print(f"[red]Error: Unknown key '{key}'[/red]")
        console.print(f"Available keys: {', '.join(SECRET_KEYS.keys())}")
        raise typer.Exit(code=1)

    config = SECRET_KEYS[key]
    param_name = get_parameter_name(stage, key)

    # Get value
    if value is None:
        value = _prompt_for_secret_value(key, config)

    # Put parameter
    _put_parameter(ssm, param_name, value, config["type"], config["description"])


@app.command()
def set(
    stage: Annotated[
        str,
        typer.Option(
            "--stage",
            "-s",
            help="Deployment stage (dev, staging, production)",
        ),
    ] = "dev",
    key: Annotated[
        str | None,
        typer.Option(
            "--key",
            "-k",
            help="Specific key to set (if not provided, interactive mode)",
        ),
    ] = None,
    value: Annotated[
        str | None,
        typer.Option(
            "--value",
            "-v",
            help="Secret value (if not provided, will prompt)",
        ),
    ] = None,
) -> None:
    """Set secrets in AWS SSM Parameter Store.

    Parameters
    ----------
    stage : str
        Deployment stage (dev, staging, production)
    key : str | None
        Specific key to set (if None, interactive mode for all keys)
    value : str | None
        Secret value (if None, will prompt for input)
    """
    ssm = get_ssm_client()

    # Interactive mode: set all secrets
    if key is None:
        console.print(f"[bold cyan]Setting secrets for stage: {stage}[/bold cyan]\n")
        _set_all_secrets(ssm, stage)
        console.print("\n[bold green]Secrets configuration complete![/bold green]")
        return

    # Single key mode
    _set_single_secret(ssm, stage, key, value)


def _display_parameter_info(param: dict[str, Any], show_value: bool) -> None:
    """Display parameter information to console.

    Parameters
    ----------
    param : dict[str, Any]
        SSM parameter response data
    show_value : bool
        If True, show decrypted value
    """
    console.print(f"[bold]Parameter:[/bold] {param['Name']}")
    console.print(f"[bold]Type:[/bold] {param['Type']}")
    console.print(f"[bold]Last Modified:[/bold] {param['LastModifiedDate']}")

    if show_value:
        console.print(f"[bold]Value:[/bold] {param['Value']}")
    else:
        console.print("[yellow]Value: <hidden> (use --show-value to display)[/yellow]")


@app.command()
def get(
    stage: Annotated[
        str,
        typer.Option("--stage", "-s", help="Deployment stage"),
    ] = "dev",
    key: Annotated[
        str,
        typer.Option("--key", "-k", help="Secret key to retrieve"),
    ] = ...,
    show_value: Annotated[
        bool,
        typer.Option(
            "--show-value",
            help="Show decrypted value (WARNING: prints to console)",
        ),
    ] = False,
) -> None:
    """Get a secret from AWS SSM Parameter Store.

    Parameters
    ----------
    stage : str
        Deployment stage
    key : str
        Secret key to retrieve
    show_value : bool
        If True, show decrypted value in console (default: False)
    """
    if key not in SECRET_KEYS:
        console.print(f"[red]Error: Unknown key '{key}'[/red]")
        console.print(f"Available keys: {', '.join(SECRET_KEYS.keys())}")
        raise typer.Exit(code=1)

    ssm = get_ssm_client()
    param_name = get_parameter_name(stage, key)

    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        _display_parameter_info(response["Parameter"], show_value)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ParameterNotFound":
            console.print(f"[red]Error: Parameter '{param_name}' not found[/red]")
        else:
            console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1) from error


@app.command()
def list(
    stage: Annotated[
        str,
        typer.Option("--stage", "-s", help="Deployment stage"),
    ] = "dev",
) -> None:
    """List all secrets for a stage.

    Parameters
    ----------
    stage : str
        Deployment stage
    """
    ssm = get_ssm_client()
    path = f"/scryfall-mcp/{stage}/"

    try:
        response = ssm.get_parameters_by_path(Path=path, WithDecryption=False)

        if not response["Parameters"]:
            console.print(f"[yellow]No parameters found for stage '{stage}'[/yellow]")
            return

        table = Table(title=f"Secrets for stage: {stage}")
        table.add_column("Key", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Last Modified", style="yellow")

        for param in response["Parameters"]:
            key = param["Name"].split("/")[-1]
            table.add_row(
                key,
                param["Type"],
                str(param["LastModifiedDate"]),
            )

        console.print(table)

    except (BotoCoreError, ClientError) as error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1) from error


@app.command()
def delete(
    stage: Annotated[
        str,
        typer.Option("--stage", "-s", help="Deployment stage"),
    ] = "dev",
    key: Annotated[
        str,
        typer.Option("--key", "-k", help="Secret key to delete"),
    ] = ...,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Delete a secret from AWS SSM Parameter Store.

    Parameters
    ----------
    stage : str
        Deployment stage
    key : str
        Secret key to delete
    force : bool
        If True, skip confirmation prompt (default: False)
    """
    if key not in SECRET_KEYS:
        console.print(f"[red]Error: Unknown key '{key}'[/red]")
        console.print(f"Available keys: {', '.join(SECRET_KEYS.keys())}")
        raise typer.Exit(code=1)

    ssm = get_ssm_client()
    param_name = get_parameter_name(stage, key)

    if not force:
        confirm = typer.confirm(
            f"Delete parameter '{param_name}'? This cannot be undone."
        )
        if not confirm:
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        ssm.delete_parameter(Name=param_name)
        console.print(f"[green]✓ Deleted: {param_name}[/green]")
    except ClientError as error:
        if error.response["Error"]["Code"] == "ParameterNotFound":
            console.print(f"[red]Error: Parameter '{param_name}' not found[/red]")
        else:
            console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
