#!/usr/bin/env python3
"""
StockBot CLI - Main entry point
Command-line interface for StockBot trading analysis.
"""
import click
from rich.console import Console

from src.utils.logging_config import setup_logging

# Initialize rich console for beautiful output
console = Console()

# Disclaimer text
DISCLAIMER = """
[bold yellow]⚠️  DISCLAIMER[/bold yellow]

This is educational software for analysis purposes only.
It does NOT execute trades automatically. All recommendations are for
informational purposes only and are not financial advice.

Users are solely responsible for their own trading decisions.
Use of Robinhood's unofficial API may result in account restrictions.
Past performance does not guarantee future results.
"""


@click.group()
@click.version_option(version="0.1.0", prog_name="StockBot")
@click.option('--verbose', '-v', is_flag=True, default=False, help='Enable verbose logging (show INFO/DEBUG messages)')
@click.pass_context
def cli(ctx, verbose):
    """
    StockBot - AI-powered stock options analysis tool.

    Analyzes your portfolio for covered call opportunities using
    real-time data from Robinhood and Google Gemini LLM.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    # Initialize logging - quiet by default, verbose with -v flag
    setup_logging(log_level="DEBUG" if verbose else None)


@cli.command()
@click.option('--username', '-u', help='Robinhood username')
@click.option('--password', '-p', help='Robinhood password')
@click.option('--mfa-code', '-m', help='2FA/MFA code (optional - you will be prompted if needed)')
@click.option('--store/--no-store', default=True, help='Store session for future use')
@click.option('--sms', is_flag=True, default=True, help='Prefer SMS/email verification instead of app push (default: True)')
def login(username, password, mfa_code, store, sms):
    """
    Login to Robinhood and store session.

    If 2FA/MFA is enabled on your account, you will be prompted interactively:
      - First, enter your username and password
      - Then, if MFA is required, you'll see: "Please type in the MFA code: "
      - Enter your 6-digit code from your authenticator app

    By default, SMS verification is preferred over app push notification.
    Use --no-sms to use app push notification instead.
    """
    from src.cli.commands import login_command
    login_command(username, password, mfa_code, store, sms)


@cli.command()
def logout():
    """Logout from Robinhood and clear session."""
    from src.cli.commands import logout_command
    logout_command()


@cli.command()
@click.option('--show-eligible-only', '-e', is_flag=True, help='Show only positions eligible for covered calls (100+ shares)')
def portfolio(show_eligible_only):
    """View your current portfolio and positions."""
    from src.cli.commands import portfolio_command
    portfolio_command(show_eligible_only)


@cli.command()
@click.argument('symbols', nargs=-1, required=True)
@click.option('--expiration', '-exp', help='Specific expiration date (YYYY-MM-DD)')
@click.option('--min-days', type=int, default=7, help='Minimum days to expiration (default: 7)')
@click.option('--max-days', type=int, default=45, help='Maximum days to expiration (default: 45)')
@click.option('--simple', '-s', is_flag=True, default=False, help='Simplified output with fewer columns')
def cc(symbols, expiration, min_days, max_days, simple):
    """
    Screen covered call options for one or more symbols.

    Screens for OTM call options above the current stock price.
    Useful for selling calls against shares you own to collect premium.

    SYMBOLS: Stock ticker symbols (e.g., AAPL MSFT TSLA NVDA)

    Examples:

        stockbot cc AAPL

        stockbot cc AAPL --simple

        stockbot cc AAPL TSLA NVDA MSFT GOOGL

        stockbot cc AAPL TSLA --min-days 14 --max-days 30
    """
    from src.cli.commands import options_command
    options_command(symbols, expiration, min_days, max_days, simple)


@cli.command()
@click.argument('symbols', nargs=-1, required=True)
@click.option('--expiration', '-exp', help='Specific expiration date (YYYY-MM-DD)')
@click.option('--min-days', type=int, default=7, help='Minimum days to expiration (default: 7)')
@click.option('--max-days', type=int, default=45, help='Maximum days to expiration (default: 45)')
def csp(symbols, expiration, min_days, max_days):
    """
    Screen cash-secured put options for one or more symbols.

    Screens for OTM put options below the current stock price.
    Useful for selling puts to collect premium while being willing
    to buy the stock at a lower price.

    SYMBOLS: Stock ticker symbols (e.g., AAPL MSFT TSLA NVDA)

    Examples:

        stockbot csp AAPL

        stockbot csp AAPL TSLA NVDA MSFT GOOGL

        stockbot csp AAPL TSLA --min-days 14 --max-days 30
    """
    from src.cli.commands import puts_command
    puts_command(symbols, expiration, min_days, max_days)


@cli.command()
@click.argument('symbol')
def quote(symbol):
    """
    Get current stock quote.

    SYMBOL: Stock ticker symbol (e.g., AAPL, MSFT)
    """
    from src.cli.commands import quote_command
    quote_command(symbol)


@cli.command()
def status():
    """Check authentication and configuration status."""
    from src.cli.commands import status_command
    status_command()


@cli.command()
def disclaimer():
    """Display important disclaimer and risk information."""
    console.print(DISCLAIMER)


@cli.command()
def config():
    """View and manage configuration settings."""
    from src.cli.commands import config_command
    config_command()


def main():
    """Main CLI entry point."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise


if __name__ == "__main__":
    main()
