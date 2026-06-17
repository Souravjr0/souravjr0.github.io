import os

with open('pumpfun_sniper.py', 'r', encoding='latin1') as f:
    content = f.read()

# Let's find the start of the corrupt block
target_start = '                    # Check current price via bonding curve'
start_idx = content.find(target_start)

# Let's find the end of the corrupt block (the start of tiered TP)
target_end_marker = '# \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80 Tiered Take-Profit'
end_idx = content.find(target_end_marker)

if start_idx != -1 and end_idx != -1:
    print(f"Found start at {start_idx} and end at {end_idx}")
    
    clean_block = """                    # Check current price via bonding curve
                    if pos.bonding_curve:
                        bc_state = await self._get_bonding_curve_state(pos.bonding_curve)
                        if bc_state:
                            current_price = bc_state["price_sol"]

                            # --- Sell Pressure Detection -----------
                            # If bonding curve SOL reserves dropped >25% from entry,
                            # it means massive net selling -> emergency exit
                            if pos.entry_virtual_sol > 0:
                                current_vsol = bc_state.get("virtual_sol_reserves", 0)
                                vsol_change_pct = ((current_vsol - pos.entry_virtual_sol) / pos.entry_virtual_sol) * 100
                                if vsol_change_pct < -25.0:
                                    logger.info(
                                        f"{Fore.RED}[SELL PRESSURE]{Style.RESET_ALL} "
                                        f"{pos.token_symbol} - SOL reserves dropped {vsol_change_pct:.1f}% -> emergency exit"
                                    )
                                    await self._close_position(mint, "sell_pressure", current_price)
                                    continue

                            # Update peak
                            if current_price > pos.peak_price:
                                pos.peak_price = current_price

                            # Calculate P&L
                            if pos.entry_price > 0:
                                pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100

                                # Dynamic Break-Even & Profit Lock Stops (Institutional Safeguards)
                                if pnl_pct >= 30.0 and not pos.profit_lock_30:
                                    pos.profit_lock_30 = True
                                    logger.info(f"{Fore.LIGHTGREEN_EX}[PROFIT LOCK]{Style.RESET_ALL} {pos.token_symbol} reached +30.0%! Lock trailing stop-loss at +15.0% profit.")
                                elif pnl_pct >= 15.0 and not pos.break_even_locked:
                                    pos.break_even_locked = True
                                    logger.info(f"{Fore.LIGHTGREEN_EX}[BREAK-EVEN]{Style.RESET_ALL} {pos.token_symbol} reached +15.0%! Lock stop-loss at +5.0% break-even.")

                                # Exit triggers based on dynamic locks
                                if pos.profit_lock_30 and pnl_pct <= 15.0:
                                    logger.info(f"{Fore.YELLOW}[DYNAMIC SL]{Style.RESET_ALL} {pos.token_symbol} hit locked +15.0% profit stop (P&L: {pnl_pct:.1f}%)")
                                    await self._close_position(mint, "profit_lock_30", current_price)
                                    continue
                                elif pos.break_even_locked and not pos.profit_lock_30 and pnl_pct <= 5.0:
                                    logger.info(f"{Fore.YELLOW}[BREAK-EVEN SL]{Style.RESET_ALL} {pos.token_symbol} hit locked +5.0% break-even stop (P&L: {pnl_pct:.1f}%)")
                                    await self._close_position(mint, "break_even", current_price)
                                    continue
                                
                                """
    
    # Do the slice replacement
    new_content = content[:start_idx] + clean_block + content[end_idx:]
    
    with open('pumpfun_sniper.py', 'w', encoding='latin1') as f:
        f.write(new_content)
    print("Replacement completed successfully!")
else:
    print(f"Error finding markers! Start: {start_idx}, End: {end_idx}")
