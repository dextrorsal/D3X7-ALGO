import sys
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional, Dict, List
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QBrush
from src.utils.wallet.wallet_manager import WalletManager
from src.trading.drift.drift_adapter import DriftAdapter
import threading


class DriftGUI(QMainWindow):
    def __init__(self):
        print("Initializing DriftGUI...")
        super().__init__()

        # Load environment variables from .env file
        print("Loading environment variables...")
        load_dotenv()

        # Check for required environment variables
        if not os.getenv("WALLET_PASSWORD"):
            print("Error: WALLET_PASSWORD environment variable is not set")
            sys.exit(1)
        print("Environment variables loaded successfully")

        self.setWindowTitle("D3X7 Drift Account Manager")
        self.setMinimumSize(1200, 800)

        # Initialize managers
        print("Initializing wallet managers...")
        self.wallet_manager = WalletManager()  # For listing wallets
        self.drift_manager = WalletManager()  # For Drift-specific operations
        self.account_manager = None  # Will be set when wallet is selected
        print("Wallet managers initialized")

        # Initialize market info - IMPORTANT for devnet
        self.spot_markets = {0: "SOL", 1: "BTC", 2: "ETH"}

        self.perp_markets = {0: "SOL-PERP", 1: "BTC-PERP", 2: "ETH-PERP"}

        # Reverse mapping for market names to indices
        self.spot_market_indices = {v: k for k, v in self.spot_markets.items()}
        self.perp_market_indices = {v: k for k, v in self.perp_markets.items()}

        # Set dark theme
        print("Applying dark theme...")
        self.setup_dark_theme()

        # Setup main window layout
        print("Setting up main window layout...")
        self.setup_layout()

        # Setup UI components
        print("Setting up UI components...")
        self.setup_ui()

        # Setup refresh timer
        print("Setting up refresh timer...")
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_data)
        self.refresh_timer.start(5000)  # Update every 5 seconds

        # Load initial wallet data
        print("Loading initial wallet data...")
        self.load_wallets()

        # Show the window immediately
        self.show()
        print("Window shown")

        print("Initialization complete")

    def setup_dark_theme(self):
        """Set up dark theme for the application"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)

    def load_wallets(self):
        """Load available wallets into combo box"""
        try:
            print("Getting list of wallet names...")
            wallets = self.wallet_manager.list_wallets()
            print(f"Found wallets: {wallets}")

            if not wallets:
                print("No wallets found")
                return

            print("Updating wallet combo box...")
            self.wallet_combo.clear()
            self.wallet_combo.addItems(wallets)
            print("Wallet combo box updated")

            # Select first wallet
            if self.wallet_combo.count() > 0:
                print(f"Selecting first wallet: {wallets[0]}")
                self.wallet_combo.setCurrentIndex(0)
                self.on_wallet_changed(0)  # Pass index 0 instead of wallet name

        except Exception as e:
            print(f"Error loading wallets: {e}")
            import traceback

            traceback.print_exc()

    def run_async(self, coro):
        """Run a coroutine in the event loop"""
        try:
            # Get the current event loop or create a new one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Create a future that can be watched by Qt
            from PyQt6.QtCore import QEventLoop
            from PyQt6.QtWidgets import QApplication

            # Create a Qt event loop
            qloop = QEventLoop()

            # Create a callback that will quit the Qt event loop when the future is done
            future = asyncio.ensure_future(coro, loop=loop)

            def done_callback(fut):
                try:
                    # Get result to propagate any exceptions
                    fut.result()
                except Exception as e:
                    print(f"Error in async operation: {e}")
                    import traceback

                    traceback.print_exc()
                finally:
                    # Always quit the Qt event loop
                    if qloop.isRunning():
                        qloop.quit()

            future.add_done_callback(done_callback)

            # Process UI events while waiting for the future
            qloop.exec()

            # Return the result if the future is done
            if future.done():
                return future.result()
            return None
        except Exception as e:
            print(f"Error in run_async: {e}")
            import traceback

            traceback.print_exc()
            return None

    def setup_drift_client(self):
        """Synchronous wrapper to set up the Drift client."""
        print("Setting up Drift client synchronously...")

        async def setup_async():
            try:
                print("Starting async setup...")
                # Create the account manager if needed
                if not self.account_manager:
                    wallet_name = self.wallet_combo.currentText()
                    self.account_manager = DriftAdapter(wallet_name)

                # Perform the actual setup with detailed logging
                print("Calling account_manager.setup()...")
                await self.account_manager.setup(subaccount_id=0)  # Use main subaccount
                print("account_manager.setup() completed!")
                return True
            except Exception as e:
                print(f"Error in async setup: {e}")
                import traceback

                traceback.print_exc()
                return False

        print("Creating event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            print("Running setup task...")
            result = loop.run_until_complete(setup_async())
            print(f"Setup completed with result: {result}")
            return result
        except Exception as e:
            print(f"Error running setup: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            print("Closing event loop...")
            loop.close()

    def on_wallet_changed(self, index_or_name):
        """Handle wallet selection change"""
        try:
            # If we got a string (wallet name), find its index
            if isinstance(index_or_name, str):
                index = self.wallet_combo.findText(index_or_name)
                if index < 0:
                    print(f"Wallet {index_or_name} not found in combo box")
                    return
            else:
                index = index_or_name

            if index >= 0:
                # Get selected wallet name
                wallet_name = self.wallet_combo.itemText(index)
                print(f"\nSwitching to wallet: {wallet_name}")

                # Initialize account manager for the selected wallet
                print(f"Initializing DriftAdapter for {wallet_name}...")
                self.account_manager = DriftAdapter(wallet_name)

                # Setup Drift client - this is a blocking operation
                print(f"Setting up Drift client...")

                # Use our synchronous wrapper to set up the client
                if self.setup_drift_client():
                    print("Drift client setup successful!")
                    # Update UI with new data
                    self.update_data()
                else:
                    print("Drift client setup failed!")

        except Exception as e:
            print(f"Error switching wallet: {e}")
            import traceback

            traceback.print_exc()

    def setup_positions_tab(self):
        """Set up the positions tab"""
        positions_tab = QWidget()
        layout = QVBoxLayout()

        # Market selection and trading controls
        controls_layout = QHBoxLayout()

        # Market combo box
        market_label = QLabel("Market:")
        self.market_combo = QComboBox()
        self.market_combo.addItems(list(self.perp_markets.values()))
        controls_layout.addWidget(market_label)
        controls_layout.addWidget(self.market_combo)

        # Trading buttons
        self.long_button = QPushButton("Long")
        self.short_button = QPushButton("Short")
        self.close_button = QPushButton("Close Position")

        self.long_button.clicked.connect(self.on_long_clicked)
        self.short_button.clicked.connect(self.on_short_clicked)
        self.close_button.clicked.connect(self.on_close_clicked)

        controls_layout.addWidget(self.long_button)
        controls_layout.addWidget(self.short_button)
        controls_layout.addWidget(self.close_button)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Positions table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(6)
        self.positions_table.setHorizontalHeaderLabels(
            ["Market", "Size", "Entry Price", "Current Price", "PnL", "Leverage"]
        )

        # Set column widths
        self.positions_table.setColumnWidth(0, 100)  # Market
        self.positions_table.setColumnWidth(1, 100)  # Size
        self.positions_table.setColumnWidth(2, 100)  # Entry Price
        self.positions_table.setColumnWidth(3, 100)  # Current Price
        self.positions_table.setColumnWidth(4, 100)  # PnL
        self.positions_table.setColumnWidth(5, 100)  # Leverage

        layout.addWidget(self.positions_table)
        positions_tab.setLayout(layout)

        self.tab_widget.addTab(positions_tab, "Positions")

    def setup_balances_tab(self):
        """Set up the balances tab"""
        balances_tab = QWidget()
        layout = QVBoxLayout()

        # Balance table
        self.balance_table = QTableWidget()
        self.balance_table.setColumnCount(2)
        self.balance_table.setHorizontalHeaderLabels(["Token", "Balance"])

        # Set column widths
        self.balance_table.setColumnWidth(0, 100)  # Token
        self.balance_table.setColumnWidth(1, 150)  # Balance

        layout.addWidget(self.balance_table)
        balances_tab.setLayout(layout)

        self.tab_widget.addTab(balances_tab, "Balances")

    def setup_orders_tab(self):
        """Set up the orders tab"""
        orders_tab = QWidget()
        layout = QVBoxLayout()

        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(5)
        self.orders_table.setHorizontalHeaderLabels(
            ["Market", "Side", "Size", "Price", "Status"]
        )

        # Set column widths
        self.orders_table.setColumnWidth(0, 120)  # Market
        self.orders_table.setColumnWidth(1, 80)  # Side
        self.orders_table.setColumnWidth(2, 100)  # Size
        self.orders_table.setColumnWidth(3, 100)  # Price
        self.orders_table.setColumnWidth(4, 80)  # Status

        layout.addWidget(self.orders_table)
        orders_tab.setLayout(layout)

        self.tab_widget.addTab(orders_tab, "Orders")

    def update_data(self):
        """Update display with the latest data"""
        if not self.account_manager or not self.account_manager.drift_client:
            return

        try:
            print("Updating UI data...")
            # Get user data
            drift_user = self.account_manager.drift_client.get_user()
            print(f"User account ID: {drift_user.user_account.account_id}")

            # Get account balances
            try:
                spot_positions = drift_user.get_spot_positions()
                balances = {}

                print(f"Spot positions count: {len(spot_positions)}")

                # Process spot positions for balance info
                for spot in spot_positions:
                    market_index = spot.market_index
                    token_name = (
                        "USDC"
                        if market_index == 0
                        else self.spot_markets.get(
                            market_index, f"Unknown-{market_index}"
                        )
                    )

                    # Convert token amounts from lots to normal format
                    token_amount = spot.scaled_balance
                    print(
                        f"Spot position: {token_name}, market_index: {market_index}, balance: {token_amount}"
                    )

                    balances[token_name] = token_amount

                # Update balance table
                self.balance_table.setRowCount(len(balances))
                row = 0
                for token, balance in balances.items():
                    # Create or update token name item
                    token_item = QTableWidgetItem(token)
                    self.balance_table.setItem(row, 0, token_item)

                    # Create or update balance item
                    balance_item = QTableWidgetItem(f"{balance:.6f}")
                    self.balance_table.setItem(row, 1, balance_item)

                    row += 1

                print("Balance table updated")
            except Exception as e:
                print(f"Error updating balances: {e}")
                import traceback

                traceback.print_exc()

            # Get perpetual positions
            try:
                perp_positions = drift_user.get_perp_positions()

                # Calculate total PnL and leverage
                total_pnl = 0
                total_size = 0
                total_notional = 0

                positions_to_display = []

                print(f"Perp positions count: {len(perp_positions)}")

                # Process perp positions
                for pos in perp_positions:
                    if pos.base_asset_amount == 0:
                        continue

                    market_index = pos.market_index
                    market_name = self.perp_markets.get(
                        market_index, f"Unknown-{market_index}"
                    )

                    # Convert from base lots
                    size = pos.base_asset_amount / 1e9
                    entry_price = pos.entry_price / 1e6  # Convert from quote lots

                    # Get current market price
                    market_price = (
                        self.account_manager.drift_client.get_perp_market_price(
                            market_index
                        )
                        / 1e6
                    )

                    # Calculate PnL
                    direction = 1 if size > 0 else -1
                    pnl = direction * abs(size) * (market_price - entry_price)

                    # Calculate leverage
                    notional_value = abs(size) * market_price

                    # Add to totals
                    total_pnl += pnl
                    total_size += abs(size)
                    total_notional += notional_value

                    # Add to positions list for display
                    positions_to_display.append(
                        {
                            "market": market_name,
                            "size": size,
                            "entry_price": entry_price,
                            "current_price": market_price,
                            "pnl": pnl,
                            "leverage": pos.leverage / 100,  # Leverage is stored * 100
                        }
                    )

                    print(f"Perp position: {market_name}, size: {size}, pnl: {pnl}")

                # Also add spot positions (balances) with non-zero value
                for spot in spot_positions:
                    if (
                        spot.market_index == 0 or spot.scaled_balance == 0
                    ):  # Skip USDC or zero balances
                        continue

                    market_index = spot.market_index
                    market_name = self.spot_markets.get(
                        market_index, f"Unknown-{market_index}"
                    )

                    # Get token price relative to USDC
                    token_price = (
                        self.account_manager.drift_client.get_spot_market_price(
                            market_index
                        )
                        / 1e6
                    )

                    # Add to positions list
                    positions_to_display.append(
                        {
                            "market": market_name,
                            "size": spot.scaled_balance,
                            "entry_price": 0,  # Not applicable for spot
                            "current_price": token_price,
                            "pnl": 0,  # Not tracking spot PnL
                            "leverage": 1,  # Spot is 1x leverage
                        }
                    )

                    print(
                        f"Added spot position: {market_name}, size: {spot.scaled_balance}, price: {token_price}"
                    )

                # Calculate average leverage
                avg_leverage = total_notional / total_size if total_size > 0 else 0

                # Update positions table
                self.positions_table.setRowCount(len(positions_to_display))
                for i, pos in enumerate(positions_to_display):
                    # Market
                    self.positions_table.setItem(i, 0, QTableWidgetItem(pos["market"]))

                    # Size
                    self.positions_table.setItem(
                        i, 1, QTableWidgetItem(f"{pos['size']:.4f}")
                    )

                    # Entry Price
                    entry_price_str = (
                        f"${pos['entry_price']:.2f}"
                        if pos["entry_price"] > 0
                        else "N/A"
                    )
                    self.positions_table.setItem(
                        i, 2, QTableWidgetItem(entry_price_str)
                    )

                    # Current Price
                    self.positions_table.setItem(
                        i, 3, QTableWidgetItem(f"${pos['current_price']:.2f}")
                    )

                    # PnL
                    pnl_item = QTableWidgetItem(f"${pos['pnl']:.2f}")
                    if pos["pnl"] > 0:
                        pnl_item.setForeground(QBrush(QColor("green")))
                    elif pos["pnl"] < 0:
                        pnl_item.setForeground(QBrush(QColor("red")))
                    self.positions_table.setItem(i, 4, pnl_item)

                    # Leverage
                    self.positions_table.setItem(
                        i, 5, QTableWidgetItem(f"{pos['leverage']:.2f}x")
                    )

                # Update the balance label with total PnL and leverage
                total_balance = balances.get("USDC", 0)
                self.balance_label.setText(
                    f"Balance: ${total_balance:.2f} USDC | PnL: ${total_pnl:.2f} | Avg Leverage: {avg_leverage:.2f}x"
                )

                print("Positions table updated")
            except Exception as e:
                print(f"Error updating positions: {e}")
                import traceback

                traceback.print_exc()

            # Get open orders
            try:
                orders = drift_user.get_orders()

                # Filter for active orders
                active_orders = [
                    order for order in orders if order.status <= 1
                ]  # 0=open, 1=filled

                self.orders_table.setRowCount(len(active_orders))
                for i, order in enumerate(active_orders):
                    # Market - need to determine if it's a spot or perp order
                    market_type = "PERP" if order.market_type == 1 else "SPOT"
                    if market_type == "PERP":
                        market_name = self.perp_markets.get(
                            order.market_index, f"Unknown-{order.market_index}"
                        )
                    else:
                        market_name = self.spot_markets.get(
                            order.market_index, f"Unknown-{order.market_index}"
                        )

                    self.orders_table.setItem(
                        i, 0, QTableWidgetItem(f"{market_name} ({market_type})")
                    )

                    # Direction
                    direction = "LONG" if order.direction == 0 else "SHORT"
                    self.orders_table.setItem(i, 1, QTableWidgetItem(direction))

                    # Size
                    size = order.base_asset_amount / 1e9  # Convert from base lots
                    self.orders_table.setItem(i, 2, QTableWidgetItem(f"{size:.4f}"))

                    # Price
                    price = order.price / 1e6  # Convert from quote lots
                    self.orders_table.setItem(i, 3, QTableWidgetItem(f"${price:.2f}"))

                    # Status
                    status = "OPEN" if order.status == 0 else "FILLED"
                    self.orders_table.setItem(i, 4, QTableWidgetItem(status))

                print("Orders table updated")
            except Exception as e:
                print(f"Error updating orders: {e}")
                import traceback

                traceback.print_exc()

        except Exception as e:
            print(f"Error updating data: {e}")
            import traceback

            traceback.print_exc()

    def on_deposit_clicked(self):
        """Handle deposit button click"""
        if self.account_manager:
            try:
                # TODO: Add deposit amount dialog
                amount = 1.0  # For testing
                self.run_async(self.account_manager.deposit_sol(amount))
                self.update_data()
            except Exception as e:
                print(f"Error depositing: {e}")
                import traceback

                traceback.print_exc()

    def on_withdraw_clicked(self):
        """Handle withdraw button click"""
        if self.account_manager:
            try:
                # TODO: Add withdraw amount dialog
                amount = 1.0  # For testing
                self.run_async(self.account_manager.withdraw_sol(amount))
                self.update_data()
            except Exception as e:
                print(f"Error withdrawing: {e}")
                import traceback

                traceback.print_exc()

    def on_long_clicked(self):
        """Handle long position button click"""
        if self.account_manager:
            try:
                market = self.market_combo.currentText()
                # Use our market index mapping
                market_index = self.perp_market_indices.get(
                    market, 0
                )  # Default to SOL-PERP (0) if not found
                print(f"Opening LONG position on {market} (index: {market_index})")

                # TODO: Add position size dialog
                size = 1.0  # For testing
                self.run_async(
                    self.account_manager.place_perp_order(
                        market_index=market_index,
                        base_asset_amount=int(size * 1e9),  # Convert to base lots
                        direction=0,  # Long
                        order_type=0,  # Market
                        reduce_only=False,
                    )
                )
                self.update_data()
            except Exception as e:
                print(f"Error opening long position: {e}")
                import traceback

                traceback.print_exc()

    def on_short_clicked(self):
        """Handle short position button click"""
        if self.account_manager:
            try:
                market = self.market_combo.currentText()
                # Use our market index mapping
                market_index = self.perp_market_indices.get(
                    market, 0
                )  # Default to SOL-PERP (0) if not found
                print(f"Opening SHORT position on {market} (index: {market_index})")

                # TODO: Add position size dialog
                size = 1.0  # For testing
                self.run_async(
                    self.account_manager.place_perp_order(
                        market_index=market_index,
                        base_asset_amount=int(size * 1e9),  # Convert to base lots
                        direction=1,  # Short
                        order_type=0,  # Market
                        reduce_only=False,
                    )
                )
                self.update_data()
            except Exception as e:
                print(f"Error opening short position: {e}")
                import traceback

                traceback.print_exc()

    def on_close_clicked(self):
        """Handle close position button click"""
        if self.account_manager:
            try:
                market = self.market_combo.currentText()
                # Use our market index mapping
                market_index = self.perp_market_indices.get(
                    market, 0
                )  # Default to SOL-PERP (0) if not found
                print(f"Closing position on {market} (index: {market_index})")

                # Get current position to determine close direction
                drift_user = self.account_manager.drift_client.get_user()
                positions = drift_user.get_perp_positions()

                for pos in positions:
                    if pos.market_index == market_index:
                        # Close in opposite direction
                        direction = 1 if pos.base_asset_amount > 0 else 0
                        size = abs(pos.base_asset_amount)

                        print(
                            f"Closing position: {size} in direction {direction} (1=short, 0=long)"
                        )
                        self.run_async(
                            self.account_manager.place_perp_order(
                                market_index=market_index,
                                base_asset_amount=size,
                                direction=direction,
                                order_type=0,  # Market
                                reduce_only=True,
                            )
                        )
                        break
                else:
                    print(f"No open position found for {market}")

                self.update_data()
            except Exception as e:
                print(f"Error closing position: {e}")
                import traceback

                traceback.print_exc()

    def on_cancel_all_clicked(self):
        """Handle cancel all orders button click"""
        if self.account_manager:
            try:
                self.run_async(self.account_manager.cancel_all_orders())
                self.update_data()
            except Exception as e:
                print(f"Error canceling orders: {e}")
                import traceback

                traceback.print_exc()

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            print("Shutting down...")
            # Stop the refresh timer first
            self.refresh_timer.stop()

            # Unsubscribe from Drift client
            if self.account_manager and hasattr(self.account_manager, "drift_client"):
                try:
                    # Create a temporary event loop for cleanup if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Properly unsubscribe and clean up
                    if hasattr(self.account_manager.drift_client, "unsubscribe"):
                        loop.run_until_complete(
                            self.account_manager.drift_client.unsubscribe()
                        )

                    # Close all pending connections
                    pending = asyncio.all_tasks(loop=loop)
                    if pending:
                        print(f"Cancelling {len(pending)} pending tasks...")
                        for task in pending:
                            task.cancel()
                        # Give tasks a chance to cancel properly
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )

                    # Close the loop
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
                except Exception as e:
                    print(f"Error during drift client cleanup: {e}")
                    import traceback

                    traceback.print_exc()

            print("Shutdown complete")
            event.accept()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            event.accept()

    def setup_layout(self):
        """Set up the main window layout"""
        print("Setting up main window layout...")

        # Create central widget and main layout
        print("Creating central widget...")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        print("Creating main layout...")
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create wallet selection combo box
        wallet_layout = QHBoxLayout()
        wallet_label = QLabel("Wallet:")
        self.wallet_combo = QComboBox()
        self.wallet_combo.currentIndexChanged.connect(
            self.on_wallet_changed
        )  # Connect to index changed signal
        wallet_layout.addWidget(wallet_label)
        wallet_layout.addWidget(self.wallet_combo)
        wallet_layout.addStretch()
        main_layout.addLayout(wallet_layout)

        # Create balance display
        balance_layout = QHBoxLayout()
        self.balance_label = QLabel("Balance: $0.00 USDC")
        balance_layout.addWidget(self.balance_label)
        balance_layout.addStretch()
        main_layout.addLayout(balance_layout)

        # Create tab widget
        print("Creating tab widget...")
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Set up tabs
        print("Setting up tabs...")
        self.setup_positions_tab()
        self.setup_balances_tab()
        self.setup_orders_tab()
        print("Tabs setup complete")

        # Set window properties
        self.setWindowTitle("Drift Trading GUI")
        self.resize(800, 600)  # Set a reasonable default size

    def setup_ui(self):
        """Set up UI components"""
        print(
            "Setting up UI components - no additional setup needed as it's handled in tabs"
        )
        pass


def main():
    print("Program starting...")
    try:
        app = QApplication(sys.argv)

        # Create and show the GUI
        gui = DriftGUI()

        # Start the event loop
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error in main: {str(e)}")
        if QApplication.instance():
            QApplication.instance().quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
