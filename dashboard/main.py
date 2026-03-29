import gradio as gr
import manticoresearch
import pandas as pd
import plotly.express as px
import os
import time

MANTICORE_PORT = "9308"
MANTICORE_URL = os.getenv("MANTICORE_URL", f"http://127.0.0.1:{MANTICORE_PORT}")

def get_manticore_client():
    configuration = manticoresearch.Configuration(host=MANTICORE_URL)
    client = manticoresearch.ApiClient(configuration)
    return manticoresearch.SearchApi(client)

def search_variant(variant_id):
    try:
        search_api = get_manticore_client()
        search_request = {
            'table': 'eva_variants',
            'query': {
                'match': {'variant_id': variant_id}
            }
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return None, f"Variant '{variant_id}' not found."

        data = hits[0].source

        # Prepare data for Bar Chart
        freq_data = {
            'Population': ['AFR', 'AMR', 'EAS', 'EUR', 'SAS', 'AJ', 'FIPA', 'CAU', 'OTH', 'APL', 'ASN', 'AMR_CAU'],
            'Frequency': [
                data.get('afr_freq', 0) or 0,
                data.get('amr_freq', 0) or 0,
                data.get('eas_freq', 0) or 0,
                data.get('eur_freq', 0) or 0,
                data.get('sas_freq', 0) or 0,
                data.get('aj_freq', 0) or 0,
                data.get('fipa_freq', 0) or 0,
                data.get('cau_freq', 0) or 0,
                data.get('oth_freq', 0) or 0,
                data.get('apl_freq', 0) or 0,
                data.get('asn_freq', 0) or 0,
                data.get('amr_cau_freq', 0) or 0
            ]
        }
        df = pd.DataFrame(freq_data)

        fig = px.bar(df, x='Population', y='Frequency',
                     title=f"Population Frequencies for {variant_id} (Pos: {data.get('pos')})",
                     color='Population')

        return fig, f"Found variant at position {data.get('pos')} (Ref: {data.get('ref')}, Alt: {data.get('alt')})"
    except Exception as e:
        return None, f"Error: {str(e)}"

def get_chromosome_distribution():
    try:
        search_api = get_manticore_client()
        # Get up to 5000 records to show density
        search_request = {
            'table': 'eva_variants',
            'limit': 5000,
            '_source': ['pos']
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return None

        positions = [hit.source.get('pos') for hit in hits if hit.source and 'pos' in hit.source]

        if not positions:
            return None

        df = pd.DataFrame({'Position': positions})
        fig = px.histogram(df, x='Position', nbins=50,
                           title="Distribution of Variants across Chromosome segment")
        return fig
    except Exception as e:
        print(f"Error getting distribution: {e}")
        return None

def get_sample_variants():
    try:
        search_api = get_manticore_client()
        # Get sample variant IDs for dropdown
        search_request = {
            'table': 'eva_variants',
            'limit': 20,
            '_source': ['variant_id']
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return []

        return [hit.source.get('variant_id', '') for hit in hits if hit.source and 'variant_id' in hit.source]
    except Exception as e:
        print(f"Error getting sample variants: {e}")
        return []

# Gradio Interface
with gr.Blocks(title="EVA Population Frequencies") as app:
    gr.Markdown("# Genomic Population Frequency Insights")
    gr.Markdown("Search for an NCBI variant ID to see its population distributions, and view the regional density across the loaded ALFA project chromosome.")

    # Load sample variants on startup
    sample_variants = get_sample_variants()

    with gr.Row():
        with gr.Column(scale=1):
            var_dropdown = gr.Dropdown(
                label="Select Sample Variant",
                choices=sample_variants,
                value=sample_variants[0] if sample_variants else None,
                allow_custom_value=True,
                interactive=True
            )
            search_btn = gr.Button("Search", variant="primary")
            status_text = gr.Textbox(label="Status", interactive=False)

        with gr.Column(scale=2):
            bar_chart = gr.Plot(label="Categorical Frequencies")

    with gr.Row():
        with gr.Column(scale=1):
            refresh_btn = gr.Button("Refresh Density Plot")
            refresh_samples_btn = gr.Button("Refresh Sample List")
            density_plot = gr.Plot(label="Chromosome Distribution")

    # Connect events
    search_btn.click(fn=search_variant, inputs=var_dropdown, outputs=[bar_chart, status_text])
    var_dropdown.change(fn=search_variant, inputs=var_dropdown, outputs=[bar_chart, status_text])
    refresh_btn.click(fn=get_chromosome_distribution, inputs=[], outputs=density_plot)
    refresh_samples_btn.click(fn=get_sample_variants, inputs=[], outputs=var_dropdown)
    
    # Run once on load for the distribution plot
    app.load(fn=get_chromosome_distribution, inputs=[], outputs=density_plot)

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
