"""
CLI command implementations.
All command logic for the StockBot CLI.
"""
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from loguru import logger

from src.auth.robinhood_auth import get_robinhood_auth, RobinhoodAuthError
from src.auth.credentials_manager import get_credentials_manager
from src.data.portfolio_fetcher import get_portfolio_fetcher
from src.data.stock_fetcher import get_stock_fetcher
from src.data.options_fetcher import get_options_fetcher
from src.data.news_fetcher import get_news_fetcher
from src.data.robinhood_client import get_robinhood_client
from config.settings import get_settings

console = Console()


def login_command(username: Optional[str], password: Optional[str], mfa_code: Optional[str], store: bool, prefer_sms: bool = True):
    """
    Handle login command.

    Note: If MFA/2FA is required, you'll be prompted interactively.
    By default, SMS verification is preferred over app push.
    """
    try:
        console.print("\n[bold cyan]🔐 StockBot Login[/bold cyan]\n")

        auth = get_robinhood_auth()
        cred_manager = get_credentials_manager()

        # Try to restore existing session first
        if not username and not password:
            console.print("[yellow]Attempting to restore previous session...[/yellow]")
            if auth.login_with_stored_session():
                # Verify the session is actually valid
                if auth.verify_authentication():
                    console.print("[bold green]✓ Session restored successfully![/bold green]")
                    console.print(f"[green]Logged in as: {auth.username}[/green]\n")
                    return
                else:
                    console.print("[yellow]Stored session expired, need fresh login...[/yellow]")

        # Get credentials if not provided
        if not username:
            # Try stored credentials
            username = cred_manager.get_robinhood_username()
            if not username:
                username = Prompt.ask("[cyan]Robinhood username/email[/cyan]")

        if not password:
            # Try stored credentials
            password = cred_manager.get_robinhood_password()
            if not password:
                password = Prompt.ask("[cyan]Robinhood password[/cyan]", password=True)

        # Attempt login
        console.print("[yellow]Logging in to Robinhood...[/yellow]")
        if prefer_sms:
            console.print("[dim]SMS/email verification will be requested if needed...[/dim]\n")
        else:
            console.print("[dim]App push notification will be used for verification...[/dim]\n")

        success = auth.login(username, password, mfa_code, store, prefer_sms=prefer_sms)

        if success:
            console.print("\n[bold green]✓ Login successful![/bold green]")
            console.print(f"[green]Logged in as: {username}[/green]")

            # Offer to store credentials
            if store and Confirm.ask("\n[cyan]Store credentials securely in keyring?[/cyan]", default=True):
                cred_manager.store_robinhood_credentials(username, password)
                console.print("[green]✓ Credentials stored securely[/green]")

            console.print()
        else:
            console.print("[bold red]✗ Login failed[/bold red]\n")
            sys.exit(1)

    except RobinhoodAuthError as e:
        console.print(f"\n[bold red]✗ Login failed: {str(e)}[/bold red]\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Login command failed: {e}")
        console.print(f"\n[bold red]✗ Login failed: {str(e)}[/bold red]\n")
        sys.exit(1)


def logout_command():
    """Handle logout command."""
    try:
        console.print("\n[bold cyan]🔓 Logging out from Robinhood[/bold cyan]\n")

        auth = get_robinhood_auth()

        if Confirm.ask("[yellow]Are you sure you want to logout?[/yellow]", default=False):
            auth.logout()
            console.print("[bold green]✓ Logged out successfully[/bold green]\n")
        else:
            console.print("[yellow]Logout cancelled[/yellow]\n")

    except Exception as e:
        logger.error(f"Logout command failed: {e}")
        console.print(f"[bold red]✗ Logout failed: {str(e)}[/bold red]\n")
        sys.exit(1)


def portfolio_command(show_eligible_only: bool):
    """Handle portfolio command."""
    try:
        console.print("\n[bold cyan]📊 Your Portfolio[/bold cyan]\n")

        fetcher = get_portfolio_fetcher()

        # Fetch portfolio
        with console.status("[yellow]Fetching portfolio data...[/yellow]"):
            portfolio = fetcher.get_portfolio()

        # Display summary
        console.print(Panel.fit(
            f"[bold]Total Equity:[/bold] [green]${portfolio.equity:,.2f}[/green]\n"
            f"[bold]Cash:[/bold] ${portfolio.cash or 0:,.2f}\n"
            f"[bold]Buying Power:[/bold] ${portfolio.buying_power or 0:,.2f}\n"
            f"[bold]Total Positions:[/bold] {portfolio.position_count}",
            title="[bold cyan]Portfolio Summary[/bold cyan]",
            border_style="cyan"
        ))

        # Filter positions if requested
        positions = portfolio.covered_call_eligible_positions if show_eligible_only else portfolio.positions

        if not positions:
            if show_eligible_only:
                console.print("\n[yellow]No positions with 100+ shares found[/yellow]")
            else:
                console.print("\n[yellow]No positions in portfolio[/yellow]")
            return

        # Create positions table
        table = Table(title="\n📈 Positions" + (" (Covered Call Eligible)" if show_eligible_only else ""))

        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Shares", justify="right", style="white")
        table.add_column("Avg Cost", justify="right", style="white")
        table.add_column("Current", justify="right", style="white")
        table.add_column("Value", justify="right", style="white")
        table.add_column("P/L", justify="right")
        table.add_column("P/L %", justify="right")
        if not show_eligible_only:
            table.add_column("CC Eligible", justify="center")

        for pos in positions:
            # Calculate values
            current = pos.current_price or pos.average_buy_price
            value = pos.market_value or (pos.quantity * pos.average_buy_price)
            pl = pos.unrealized_pl or 0
            pl_percent = pos.percent_change or 0

            # Color code P/L
            pl_color = "green" if pl >= 0 else "red"
            pl_str = f"[{pl_color}]${abs(pl):,.2f}[/{pl_color}]"
            if pl >= 0:
                pl_str = f"[{pl_color}]+{pl_str}[/{pl_color}]"

            pl_percent_str = f"[{pl_color}]{pl_percent:+.2f}%[/{pl_color}]"

            row = [
                pos.symbol,
                f"{pos.quantity:.0f}",
                f"${pos.average_buy_price:.2f}",
                f"${current:.2f}",
                f"${value:,.2f}",
                pl_str,
                pl_percent_str
            ]

            if not show_eligible_only:
                row.append("✓" if pos.is_covered_call_eligible else "")

            table.add_row(*row)

        console.print(table)
        console.print()

        # Show covered call eligible count if not filtered
        if not show_eligible_only:
            eligible_count = len(portfolio.covered_call_eligible_positions)
            if eligible_count > 0:
                console.print(f"[cyan]💡 {eligible_count} position(s) eligible for covered calls (100+ shares)[/cyan]")
                console.print("[dim]Run with --show-eligible-only to see only these positions[/dim]\n")

    except Exception as e:
        logger.error(f"Portfolio command failed: {e}")
        console.print(f"[bold red]✗ Failed to fetch portfolio: {str(e)}[/bold red]\n")
        sys.exit(1)


def options_command(symbols: tuple, expiration: Optional[str], min_days: Optional[int], max_days: Optional[int]):
    """Handle options command for one or more symbols."""
    try:
        stock_fetcher = get_stock_fetcher()
        options_fetcher = get_options_fetcher()

        symbols_list = [s.upper() for s in symbols]
        console.print(f"\n[bold cyan]📋 Call Options for {', '.join(symbols_list)}[/bold cyan]\n")

        # Calculate HV30 for each symbol upfront
        console.print("[dim]Calculating historical volatility...[/dim]\n")
        hv30_cache = {}
        for symbol in symbols_list:
            try:
                hv30 = stock_fetcher.get_historical_volatility(symbol, days=30)
                hv30_cache[symbol] = hv30
                logger.info(f"{symbol} HV30: {hv30*100:.2f}%")
            except Exception as e:
                logger.warning(f"Could not calculate HV30 for {symbol}: {e}")
                hv30_cache[symbol] = None

        for symbol in symbols_list:
            try:
                console.print(f"[bold cyan]{'='*60}[/bold cyan]")
                console.print(f"[bold cyan]{symbol}[/bold cyan]")
                console.print(f"[bold cyan]{'='*60}[/bold cyan]")

                # Get current stock price
                with console.status(f"[yellow]Fetching {symbol} quote...[/yellow]"):
                    quote = stock_fetcher.get_quote(symbol)

                # Display current price and HV30
                hv30 = hv30_cache.get(symbol)
                if hv30:
                    console.print(f"[bold]Current Price:[/bold] [green]${quote.last_trade_price:.2f}[/green]  |  [bold]HV30:[/bold] [yellow]{hv30*100:.1f}%[/yellow]\n")
                else:
                    console.print(f"[bold]Current Price:[/bold] [green]${quote.last_trade_price:.2f}[/green]\n")

                # Get latest news (last 24 hours)
                try:
                    news_fetcher = get_news_fetcher()
                    with console.status(f"[yellow]Fetching {symbol} news...[/yellow]"):
                        news_articles = news_fetcher.get_news(symbol)

                    if news_articles:
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        news_lines = []
                        for article in news_articles:
                            # Format relative time
                            time_str = ""
                            if article.publish_time:
                                pub_time = article.publish_time
                                if pub_time.tzinfo is None:
                                    pub_time = pub_time.replace(tzinfo=timezone.utc)
                                delta = now - pub_time
                                hours = int(delta.total_seconds() / 3600)
                                if hours < 1:
                                    minutes = int(delta.total_seconds() / 60)
                                    time_str = f" [dim]({minutes}m ago)[/dim]"
                                else:
                                    time_str = f" [dim]({hours}h ago)[/dim]"

                            news_lines.append(
                                f"[cyan]•[/cyan] [dim][{article.publisher}][/dim] {article.title}{time_str}"
                            )
                            if article.summary:
                                news_lines.append(f"  [dim]{article.summary}[/dim]")

                        news_text = "\n".join(news_lines)
                        console.print(Panel(news_text, title="📰 Latest News (24h)", border_style="blue"))
                        console.print()
                    else:
                        console.print("[dim]No news in the last 24 hours[/dim]\n")
                except Exception as e:
                    logger.debug(f"Failed to fetch news for {symbol}: {e}")
                    pass

                # Get options
                with console.status(f"[yellow]Fetching {symbol} options chain...[/yellow]"):
                    if expiration:
                        options = options_fetcher.get_call_options(symbol, expiration)
                    else:
                        options = options_fetcher.get_covered_call_options(
                            symbol, quote.last_trade_price, min_days, max_days
                        )

                if not options:
                    console.print("[yellow]No options found with specified criteria[/yellow]\n")
                    continue

                # Create options table
                table = Table(title=f"Call Options for {symbol}")

                table.add_column("Strike", justify="right", style="cyan")
                table.add_column("Exp", style="white")
                table.add_column("DTE", justify="right", style="dim")
                table.add_column("Bid/Ask", justify="right", style="green")
                table.add_column("Last", justify="right", style="green")
                table.add_column("Delta", justify="right", style="white")
                table.add_column("Gamma", justify="right", style="white")
                table.add_column("Theta", justify="right", style="red")
                table.add_column("Vega", justify="right", style="white")
                table.add_column("IV", justify="right", style="yellow")
                table.add_column("HV30", justify="right", style="dim")
                table.add_column("IV/HV30", justify="right", style="bold")
                table.add_column("Assessment", style="green")
                table.add_column("Vol", justify="right", style="dim")
                table.add_column("OI", justify="right", style="dim")

                for opt in sorted(options, key=lambda x: (x.expiration_date, x.strike_price)):
                    volume = opt.volume or 0
                    oi = opt.open_interest or 0

                    # Format bid/ask
                    bid_ask = ""
                    if opt.bid_price and opt.ask_price:
                        bid_ask = f"${opt.bid_price:.2f}/${opt.ask_price:.2f}"

                    # Format last trade
                    last_trade = f"${opt.last_trade_price:.2f}" if opt.last_trade_price else ""

                    # Format Greeks
                    delta_str = f"{opt.delta:.3f}" if opt.delta else ""
                    gamma_str = f"{opt.gamma:.4f}" if opt.gamma else ""
                    theta_str = f"{opt.theta:.3f}" if opt.theta else ""
                    vega_str = f"{opt.vega:.3f}" if opt.vega else ""

                    # Format IV as percentage
                    iv_str = f"{opt.implied_volatility * 100:.1f}%" if opt.implied_volatility else ""

                    # Calculate IV/HV30 ratio and assessment
                    hv30 = hv30_cache.get(symbol)
                    iv = opt.implied_volatility

                    if iv and hv30:
                        hv30_str = f"{hv30 * 100:.1f}%"
                        iv_hv_ratio = iv / hv30

                        # Determine assessment for covered call sellers
                        # Higher IV = Better premium for sellers (selling overpriced options)
                        if iv_hv_ratio > 1.15:
                            assessment = "⭐⭐ Excellent"
                            ratio_style = "bold green"
                        elif iv_hv_ratio > 1.0:
                            assessment = "⭐ Good Deal"
                            ratio_style = "green"
                        elif iv_hv_ratio >= 0.85:
                            assessment = "Fair"
                            ratio_style = "yellow"
                        else:
                            assessment = "Poor Deal"
                            ratio_style = "red"

                        ratio_str = f"[{ratio_style}]{iv_hv_ratio:.2f}[/{ratio_style}]"
                    else:
                        hv30_str = f"{hv30 * 100:.1f}%" if hv30 else "N/A"
                        ratio_str = "N/A"
                        assessment = "N/A"

                    table.add_row(
                        f"${opt.strike_price:.2f}",
                        opt.expiration_date.strftime("%m-%d"),
                        str(opt.days_to_expiration),
                        bid_ask,
                        last_trade,
                        delta_str,
                        gamma_str,
                        theta_str,
                        vega_str,
                        iv_str,
                        hv30_str,
                        ratio_str,
                        assessment,
                        str(volume),
                        str(oi),
                    )

                console.print(table)
                console.print(f"[dim]Total options for {symbol}: {len(options)}[/dim]")

                # Add explanatory footer
                console.print("\n[dim]💡 IV/HV30 Ratio Guide (Covered Call Sellers):[/dim]")
                console.print("[dim]  • > 1.15: ⭐⭐ Excellent (Overpriced! Sell for high premium)[/dim]")
                console.print("[dim]  • 1.0-1.15: ⭐ Good Deal (IV above HV → Good premium)[/dim]")
                console.print("[dim]  • 0.85-1.0: Fair (IV near fair value)[/dim]")
                console.print("[dim]  • < 0.85: Poor Deal (Underpriced! Low premium)[/dim]\n")

            except Exception as e:
                logger.error(f"Failed to fetch options for {symbol}: {e}")
                console.print(f"[bold red]✗ Failed to fetch options for {symbol}: {str(e)}[/bold red]\n")
                continue

    except Exception as e:
        logger.error(f"Options command failed: {e}")
        console.print(f"[bold red]✗ Failed to fetch options: {str(e)}[/bold red]\n")
        sys.exit(1)


def quote_command(symbol: str):
    """Handle quote command."""
    try:
        symbol = symbol.upper()
        console.print(f"\n[bold cyan]💵 Quote for {symbol}[/bold cyan]\n")

        fetcher = get_stock_fetcher()

        with console.status(f"[yellow]Fetching quote...[/yellow]"):
            quote = fetcher.get_quote(symbol)

        # Display quote
        console.print(Panel.fit(
            f"[bold]Last Trade:[/bold] [green]${quote.last_trade_price:.2f}[/green]\n"
            f"[bold]Bid:[/bold] ${quote.bid_price:.2f} [dim]x[/dim] [bold]Ask:[/bold] ${quote.ask_price:.2f}\n"
            f"[bold]Previous Close:[/bold] ${quote.previous_close:.2f}\n"
            f"[bold]Volume:[/bold] {quote.volume:,}"
            if quote.bid_price and quote.ask_price and quote.previous_close and quote.volume
            else f"[bold]Last Trade:[/bold] [green]${quote.last_trade_price:.2f}[/green]",
            title=f"[bold cyan]{symbol}[/bold cyan]",
            border_style="cyan"
        ))

        console.print()

    except Exception as e:
        logger.error(f"Quote command failed: {e}")
        console.print(f"[bold red]✗ Failed to fetch quote: {str(e)}[/bold red]\n")
        sys.exit(1)


def status_command():
    """Handle status command."""
    try:
        console.print("\n[bold cyan]⚙️  StockBot Status[/bold cyan]\n")

        auth = get_robinhood_auth()
        cred_manager = get_credentials_manager()
        client = get_robinhood_client()
        settings = get_settings()

        # Authentication status
        auth_status = auth.get_authentication_status()

        auth_table = Table(title="Authentication")
        auth_table.add_column("Item", style="cyan")
        auth_table.add_column("Status", style="white")

        auth_table.add_row(
            "Robinhood Session",
            "[green]✓ Authenticated[/green]" if auth_status['is_authenticated'] else "[red]✗ Not authenticated[/red]"
        )
        auth_table.add_row("Username", auth_status['username'] or "[dim]Not set[/dim]")
        auth_table.add_row(
            "Stored Session",
            "[green]✓ Available[/green]" if auth_status['has_stored_session'] else "[dim]None[/dim]"
        )
        auth_table.add_row(
            "Stored Credentials",
            "[green]✓ Available[/green]" if auth_status['has_stored_credentials'] else "[dim]None[/dim]"
        )

        console.print(auth_table)

        # Rate limiter status
        rate_stats = client.get_rate_limiter_stats()

        rate_table = Table(title="\nRate Limiting")
        rate_table.add_column("Metric", style="cyan")
        rate_table.add_column("Value", style="white")

        rate_table.add_row(
            "Calls (last minute)",
            f"{rate_stats['calls_last_minute']}/{rate_stats['minute_limit']}"
        )
        rate_table.add_row(
            "Calls (last hour)",
            f"{rate_stats['calls_last_hour']}/{rate_stats['hour_limit']}"
        )
        rate_table.add_row("Failure Count", str(rate_stats['failure_count']))
        rate_table.add_row(
            "Circuit Breaker",
            "[red]OPEN[/red]" if rate_stats['circuit_open'] else "[green]CLOSED[/green]"
        )

        console.print(rate_table)

        # Credentials status
        cred_status = cred_manager.get_credentials_status()

        cred_table = Table(title="\nCredentials")
        cred_table.add_column("Type", style="cyan")
        cred_table.add_column("Status", style="white")

        cred_table.add_row(
            "Robinhood Username",
            "[green]✓ Set[/green]" if cred_status['robinhood_username'] else "[dim]Not set[/dim]"
        )
        cred_table.add_row(
            "Robinhood Password",
            "[green]✓ Set[/green]" if cred_status['robinhood_password'] else "[dim]Not set[/dim]"
        )
        cred_table.add_row(
            "Gemini API Key",
            "[green]✓ Set[/green]" if cred_status['gemini_api_key'] else "[yellow]Not set (required for analysis)[/yellow]"
        )

        console.print(cred_table)
        console.print()

    except Exception as e:
        logger.error(f"Status command failed: {e}")
        console.print(f"[bold red]✗ Failed to get status: {str(e)}[/bold red]\n")
        sys.exit(1)


def config_command():
    """Handle config command."""
    try:
        console.print("\n[bold cyan]⚙️  Configuration[/bold cyan]\n")

        settings = get_settings()

        # Strategy settings
        strategy_table = Table(title="Strategy Parameters")
        strategy_table.add_column("Setting", style="cyan")
        strategy_table.add_column("Value", style="white")

        strategy_table.add_row("Min Option Volume", str(settings.strategy.min_option_volume))
        strategy_table.add_row("Min Open Interest", str(settings.strategy.min_open_interest))
        strategy_table.add_row("Min Premium", f"${settings.strategy.min_premium:.2f}")
        strategy_table.add_row("Min Days to Expiration", str(settings.strategy.min_days_to_expiration))
        strategy_table.add_row("Max Days to Expiration", str(settings.strategy.max_days_to_expiration))
        strategy_table.add_row(
            "Strike Range",
            f"{settings.strategy.min_strike_percent:.1%} - {settings.strategy.max_strike_percent:.1%} OTM"
        )
        strategy_table.add_row(
            "Delta Range",
            f"{settings.strategy.min_delta:.2f} - {settings.strategy.max_delta:.2f}"
        )

        console.print(strategy_table)

        # Rate limiting settings
        rate_table = Table(title="\nRate Limiting")
        rate_table.add_column("Setting", style="cyan")
        rate_table.add_column("Value", style="white")

        rate_table.add_row("Calls per Minute", str(settings.rate_limit.calls_per_minute))
        rate_table.add_row("Calls per Hour", str(settings.rate_limit.calls_per_hour))
        rate_table.add_row("Min Delay (seconds)", str(settings.rate_limit.min_delay_seconds))
        rate_table.add_row("Backoff Factor", str(settings.rate_limit.backoff_factor))
        rate_table.add_row("Max Retries", str(settings.rate_limit.max_retries))

        console.print(rate_table)

        console.print(f"\n[dim]Configuration file: config/settings.py[/dim]")
        console.print(f"[dim]Edit .env file or config/settings.py to change values[/dim]\n")

    except Exception as e:
        logger.error(f"Config command failed: {e}")
        console.print(f"[bold red]✗ Failed to load config: {str(e)}[/bold red]\n")
        sys.exit(1)
