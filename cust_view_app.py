import gradio as gr
import requests
import pandas as pd
from supabase import create_client, Client

# --- 1. ASSETS & CREDENTIALS ---
URL = "https://tvvtmjaiyhueijqwcudw.supabase.co"
KEY = "sb_publishable_brtHx0OfjTIt36mtsH5cjA_V8yaELpn"
IMAGE_URL = "https://raw.githubusercontent.com/Teddddyyyy/mishtee-magic/refs/heads/main/unnamed.jpg"
STYLE_URL = "https://raw.githubusercontent.com/Teddddyyyy/mishtee-magic/refs/heads/main/style.py"

# Initialize Supabase Client
supabase: Client = create_client(URL, KEY)

# Fetch Custom CSS from style.py
try:
    response = requests.get(STYLE_URL)
    response.raise_for_status()
    local_vars = {}
    exec(response.text, {}, local_vars)
    mishtee_css = local_vars.get("css", "")
except Exception as e:
    print(f"Error loading CSS: {e}")
    mishtee_css = ""

# --- 2. DATA FUNCTIONS ---

def get_customer_portal_data(phone_number):
    """Retrieves greeting and personal order history."""
    if not phone_number or len(phone_number) < 10:
        return "Please enter a valid 10-digit phone number.", pd.DataFrame()

    # Fetch Customer Name
    cust_resp = supabase.table("customers").select("full_name").eq("phone", phone_number).maybe_single().execute()
    
    if not cust_resp.data:
        return "Welcome! Phone number not recognized. Please contact support.", pd.DataFrame()

    customer_name = cust_resp.data['full_name']
    greeting = f"## Namaste, {customer_name} ji! \nGreat to see you again."

    # Fetch Order History with Join
    order_resp = supabase.table("orders").select(
        "order_id, qty_kg, status, order_date, products(sweet_name)"
    ).eq("cust_phone", phone_number).execute()

    if order_resp.data:
        df = pd.DataFrame(order_resp.data)
        # Flatten join data
        df['Product'] = df['products'].apply(lambda x: x['sweet_name'] if x else "Unknown")
        df = df[['order_id', 'Product', 'qty_kg', 'status', 'order_date']]
        df.columns = ["Order ID", "Sweet Name", "Qty (kg)", "Status", "Date"]
        return greeting, df
    
    return greeting, pd.DataFrame(columns=["Order ID", "Sweet Name", "Qty (kg)", "Status", "Date"])

def get_trending_data():
    """Retrieves top 4 products for the trending tab."""
    resp = supabase.table("orders").select("qty_kg, products(sweet_name)").execute()
    
    if not resp.data:
        return pd.DataFrame(columns=["Sweet Name", "Total Sold (kg)"])

    raw_df = pd.DataFrame(resp.data)
    raw_df['Sweet Name'] = raw_df['products'].apply(lambda x: x['sweet_name'] if x else "Unknown")
    
    trending_df = raw_df.groupby('Sweet Name')['qty_kg'].sum().reset_index()
    trending_df = trending_df.sort_values(by='qty_kg', ascending=False).head(4)
    trending_df.columns = ["Sweet Name", "Total Sold (kg)"]
    return trending_df

# --- 3. GRADIO UI ASSEMBLY ---

with gr.Blocks(css=mishtee_css, title="MishTee-Magic Customer Portal") as demo:
    
    # Header Section
    with gr.Column(elem_id="header_container"):
        gr.Image(IMAGE_URL, show_label=False, container=False, width=250, elem_id="logo")
        gr.Markdown("<h3 style='text-align: center; color: #4a4a4a;'>[Purity and Health]</h3>")

    # Welcome & Login Logic
    with gr.Row(variant="compact"):
        with gr.Column(scale=2):
            phone_input = gr.Textbox(
                label="Registered Mobile Number", 
                placeholder="e.g. 98250XXXXX",
                max_lines=1
            )
            login_btn = gr.Button("Access My Portal", variant="primary")
        
        with gr.Column(scale=3):
            # This area updates upon login
            welcome_msg = gr.Markdown("### Welcome to MishTee-Magic \nEnter your number to view your exclusive health-first sweet history.")

    gr.HTML("<br>")

    # Tabbed Data Tables (Sober Minimalist Look)
    with gr.Tabs():
        with gr.TabItem("🕒 My Order History"):
            history_table = gr.Dataframe(
                headers=["Order ID", "Sweet Name", "Qty (kg)", "Status", "Date"],
                interactive=False,
                wrap=True
            )
            
        with gr.TabItem("🔥 Trending Today"):
            trending_table = gr.Dataframe(
                headers=["Sweet Name", "Total Sold (kg)"],
                interactive=False
            )

    # Event Mapping
    def handle_login(phone):
        greeting, history_df = get_customer_portal_data(phone)
        trending_df = get_trending_data()
        return greeting, history_df, trending_df

    login_btn.click(
        fn=handle_login,
        inputs=[phone_input],
        outputs=[welcome_msg, history_table, trending_table]
    )

    # Footer
    gr.Markdown(
        "<p style='text-align: center; font-size: 0.8em; margin-top: 50px;'>"
        "MishTee-Magic Ahmedabad • Organic • Low-Gluten • Low-Sugar</p>"
    )

# --- 4. LAUNCH ---
if __name__ == "__main__":
    demo.launch()
