#!/usr/bin/env python3
"""
Streamlit UI for Crypto Assistant
Displays saved positions and allows running the complete workflow
"""

import streamlit as st
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import time
import threading
from queue import Queue
import sys
from io import StringIO
import io
from contextlib import redirect_stdout, redirect_stderr

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(__file__))

# Import our workflow
from run_complete_workflow import CompleteCryptoWorkflow

# Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    st.error("Supabase client not found. Please install it with: pip install supabase")
    st.stop()

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase credentials. Please check your .env file.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_stored_positions() -> List[Dict[str, Any]]:
    """Fetch all stored positions from Supabase"""
    try:
        response = supabase.table('new_positions').select('*').order('created_at', desc=True).execute()
        
        if response.data:
            return response.data
        else:
            return []
            
    except Exception as e:
        st.error(f"Error fetching positions: {e}")
        return []

def format_position_data(positions: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format positions data for display"""
    if not positions:
        return pd.DataFrame()
    
    formatted_data = []
    for pos in positions:
        formatted_data.append({
            'ID': pos.get('id'),
            'Symbol': pos.get('symbol'),
            'Entry Price': f"${pos.get('entry_price', 0):.8f}",
            'Size (USD)': f"${pos.get('size_usd', 0):.2f}",
            'Stop Loss': f"${pos.get('stop_loss', 0):.8f}",
            'Target 1': f"${pos.get('target_1', 0):.8f}",
            'Target 2': f"${pos.get('target_2', 0):.8f}",
            'Status': pos.get('status', 'active'),
            'Created': pos.get('created_at', ''),
            'Rationale': pos.get('rationale', '')[:100] + '...' if len(pos.get('rationale', '')) > 100 else pos.get('rationale', '')
        })
    
    return pd.DataFrame(formatted_data)

def update_position_status(position_id: int, new_status: str) -> bool:
    """Update position status in Supabase"""
    try:
        response = supabase.table('new_positions').update({
            'status': new_status
        }).eq('id', position_id).execute()
        
        return bool(response.data)
        
    except Exception as e:
        st.error(f"Error updating position status: {e}")
        return False

def run_workflow_sync() -> tuple[bool, str]:
    """Run the complete workflow synchronously"""
    try:
        # Create string buffer to capture output
        output_buffer = io.StringIO()
        
        # Redirect stdout and stderr to capture logs
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            # Run the async workflow in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                workflow = CompleteCryptoWorkflow()
                success = loop.run_until_complete(workflow.run_complete_workflow())
            except Exception as e:
                print(f"Workflow execution error: {e}")
                import traceback
                traceback.print_exc()
                success = False
            finally:
                loop.close()
        
        # Get captured output
        logs = output_buffer.getvalue()
        output_buffer.close()
        
        return success, logs
        
    except Exception as e:
        error_msg = f"Error running workflow: {e}"
        import traceback
        error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
        return False, error_msg

def update_workflow_logs():
    """Update workflow logs from the queue"""
    if 'workflow_logs' not in st.session_state:
        st.session_state.workflow_logs = []
    
    # Get new logs from the queue (this would need to be implemented with proper inter-process communication)
    # For now, we'll use a simpler approach with session state updates
    
    # Auto-refresh every 2 seconds when workflow is running
    if st.session_state.get('workflow_running', False):
        time.sleep(2)
        st.rerun()

def main():
    st.set_page_config(
        page_title="Crypto Assistant - Trading Positions",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title(" Crypto Assistant - Trading Positions")
    st.markdown("---")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("🛠️ Controls")
        
        # Run workflow button
        if st.button("🔄 Run Complete Workflow", type="primary", use_container_width=True):
            st.session_state.run_workflow = True
        
        st.markdown("---")
        
        # Refresh positions button
        if st.button("🔄 Refresh Positions", type="primary", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        
        # Status filter
        st.subheader("📊 Filter Positions")
        status_filter = st.selectbox(
            "Status",
            ["All", "active", "closed", "cancelled"],
            index=0
        )
        
        # Date range filter
        st.subheader("📅 Date Range")
        use_date_filter = st.checkbox("Filter by date range")
        
        if use_date_filter:
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
        else:
            start_date = None
            end_date = None
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Saved Trading Positions")
        
        # Fetch positions
        positions = get_stored_positions()
        
        if not positions:
            st.info("No positions found. Run the workflow to generate new positions!")
        else:
            # Apply filters
            filtered_positions = positions
            
            if status_filter != "All":
                filtered_positions = [p for p in filtered_positions if p.get('status') == status_filter]
            
            if use_date_filter and start_date and end_date:
                filtered_positions = [
                    p for p in filtered_positions 
                    if start_date <= datetime.fromisoformat(p.get('created_at', '').replace('Z', '+00:00')).date() <= end_date
                ]
            
            if filtered_positions:
                # Display positions in a table
                df = format_position_data(filtered_positions)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Summary statistics
                st.subheader(" Summary Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Positions", len(filtered_positions))
                
                with col2:
                    active_count = len([p for p in filtered_positions if p.get('status') == 'active'])
                    st.metric("Active Positions", active_count)
                
                with col3:
                    total_value = sum(p.get('size_usd', 0) for p in filtered_positions if p.get('status') == 'active')
                    st.metric("Total Value (USD)", f"${total_value:.2f}")
                
                with col4:
                    avg_entry = sum(p.get('entry_price', 0) for p in filtered_positions if p.get('status') == 'active') / max(active_count, 1)
                    st.metric("Avg Entry Price", f"${avg_entry:.8f}")
                
            else:
                st.info("No positions match the selected filters.")
    
    with col2:
        st.header("⚙️ Position Actions")
        
        if positions:
            # Position selection for actions
            position_options = {f"{p['symbol']} - {p['created_at'][:10]}": p['id'] for p in positions if p.get('status') == 'active'}
            
            if position_options:
                selected_position = st.selectbox("Select Position", list(position_options.keys()))
                position_id = position_options[selected_position]
                
                # Status update
                new_status = st.selectbox("New Status", ["active", "closed", "cancelled"])
                
                if st.button("Update Status", use_container_width=True):
                    if update_position_status(position_id, new_status):
                        st.success(f"Position status updated to {new_status}")
                        st.rerun()
                    else:
                        st.error("Failed to update position status")
                
                st.markdown("---")
                
                # Position details
                selected_pos = next(p for p in positions if p['id'] == position_id)
                st.subheader("📋 Position Details")
                st.write(f"**Symbol:** {selected_pos['symbol']}")
                st.write(f"**Entry Price:** ${selected_pos['entry_price']:.8f}")
                st.write(f"**Size:** ${selected_pos['size_usd']:.2f}")
                st.write(f"**Stop Loss:** ${selected_pos['stop_loss']:.8f}")
                st.write(f"**Target 1:** ${selected_pos['target_1']:.8f}")
                st.write(f"**Target 2:** ${selected_pos['target_2']:.8f}")
                st.write(f"**Status:** {selected_pos['status']}")
                st.write(f"**Created:** {selected_pos['created_at']}")
                
                # Full rationale
                with st.expander(" Full Rationale"):
                    st.write(selected_pos['rationale'])
            else:
                st.info("No active positions to manage.")
    
    with col2:
        st.header("⚙️ Workflow Status")
        
        # Show workflow status
        if st.session_state.get('workflow_running', False):
            st.info("🔄 Workflow is currently running...")
        
        elif st.session_state.get('workflow_success') is not None:
            if st.session_state.workflow_success:
                st.success("✅ Workflow completed successfully!")
            else:
                st.error("❌ Workflow failed!")
    
    # Workflow execution section
    if st.session_state.get('run_workflow', False):
        st.markdown("---")
        st.header("🔄 Running Complete Workflow")
        
        # Simple loading spinner
        with st.spinner("Running workflow... This may take several minutes."):
            # Run the workflow synchronously
            success, logs = run_workflow_sync()
        
        # Display results
        if success:
            st.success("✅ Workflow completed successfully!")
        else:
            st.error("❌ Workflow failed!")
        
        # Display logs in expandable section
        with st.expander("📋 Workflow Logs", expanded=True):
            st.code(logs, language="text")
        
        # Show new positions if any were generated
        if success:
            st.subheader("🆕 New Positions Generated")
            new_positions = get_stored_positions()
            
            if new_positions:
                # Get positions created in the last hour (likely from this workflow run)
                from datetime import datetime, timezone
                current_time = datetime.now(timezone.utc)
                
                recent_positions = [
                    p for p in new_positions 
                    if (current_time - datetime.fromisoformat(p['created_at'].replace('Z', '+00:00'))).total_seconds() < 3600
                ]
                
                if recent_positions:
                    st.success(f"Generated {len(recent_positions)} new positions!")
                    
                    for pos in recent_positions:
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{pos['symbol']}** - Entry: ${pos['entry_price']:.8f}")
                                st.write(f"Size: ${pos['size_usd']:.2f} | Stop Loss: ${pos['stop_loss']:.8f}")
                                st.write(f"Targets: ${pos['target_1']:.8f} → ${pos['target_2']:.8f}")
                            with col2:
                                st.write(f"**Status:** {pos['status']}")
                                st.write(f"**Created:** {pos['created_at'][:19]}")
                            
                            with st.expander("Rationale"):
                                st.write(pos['rationale'])
                            st.markdown("---")
                else:
                    st.info("No new positions were generated in this workflow run.")
        
        # Reset the workflow flag
        st.session_state.run_workflow = False
        
        # Auto-refresh to show new data
        st.rerun()

if __name__ == "__main__":
    # Initialize session state
    if 'run_workflow' not in st.session_state:
        st.session_state.run_workflow = False
    
    # Initialize workflow status and logs
    if 'workflow_logs' not in st.session_state:
        st.session_state.workflow_logs = []
    if 'workflow_running' not in st.session_state:
        st.session_state.workflow_running = False
    if 'workflow_success' not in st.session_state:
        st.session_state.workflow_success = None
    
    # Run the main function
    main()
