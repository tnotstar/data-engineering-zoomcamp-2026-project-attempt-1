import gradio as gr
import manticoresearch
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
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
            return None, None, "Variant not found."

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
                     title=f"Population Frequencies for {variant_id}",
                     color='Population')

        # Create variant info for status grid
        variant_info = {
            'variant_id': data.get('variant_id', 'N/A'),
            'chrom': data.get('chrom', 'N/A'),
            'pos': data.get('pos', 'N/A'),
            'ref': data.get('ref', 'N/A'),
            'alt': data.get('alt', 'N/A'),
            'afr_freq': data.get('afr_freq', 0),
            'amr_freq': data.get('amr_freq', 0),
            'eas_freq': data.get('eas_freq', 0),
            'eur_freq': data.get('eur_freq', 0),
            'sas_freq': data.get('sas_freq', 0),
            'aj_freq': data.get('aj_freq', 0),
            'fipa_freq': data.get('fipa_freq', 0),
            'cau_freq': data.get('cau_freq', 0),
            'oth_freq': data.get('oth_freq', 0),
            'apl_freq': data.get('apl_freq', 0),
            'asn_freq': data.get('asn_freq', 0),
            'amr_cau_freq': data.get('amr_cau_freq', 0),
        }

        return fig, variant_info, "Variant found."
    except Exception as e:
        return None, None, f"Error: {str(e)}"

def get_chromosome_distribution():
    try:
        search_api = get_manticore_client()
        # Get up to 5000 records to show density
        search_request = {
            'table': 'eva_variants',
            'limit': 1000,
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
                           title="Distribution of Variants across Chromosome segment",
                           template="plotly_dark")
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except Exception as e:
        print(f"Error getting distribution: {e}")
        return None

def get_sample_variants():
    try:
        search_api = get_manticore_client()
        # Get sample variant IDs with full population data
        # Query multiple variants to find ones with good frequency data
        search_request = {
            'table': 'eva_variants',
            'limit': 100,
            '_source': ['variant_id', 'afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return []

        # Calculate total frequency across all 12 populations for sorting
        variant_scores = []
        freq_keys = ['afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
        
        for hit in hits:
            if not hit.source:
                continue
            data = hit.source
            # Sum of all non-null frequencies
            total_freq = sum(data.get(key, 0) or 0 for key in freq_keys)
            
            variant_scores.append({
                'variant_id': data.get('variant_id', ''),
                'score': total_freq
            })

        # Sort by total frequency (descending) and take top 10
        variant_scores.sort(key=lambda x: x['score'], reverse=True)
        top_variants = [v['variant_id'] for v in variant_scores[:10] if v['variant_id']]

        return top_variants
    except Exception as e:
        print(f"Error getting sample variants: {e}")
        return []

def show_examples():
    try:
        sample_variants = get_sample_variants()
        first_val = sample_variants[0] if sample_variants else None
        
        return (
            gr.update(
                choices=sample_variants,
                value=first_val,
                visible=True
            ),
            gr.update(value=first_val) # Update searchbox as well
        )
    except Exception as e:
        print(f"Error in show_examples: {e}")
        return gr.Dropdown(choices=[], value=None, visible=False), gr.update()

def format_variant_info_as_list(data):
    """Formats variant dictionary into a list of [Field, Value] for Gr.Dataframe"""
    if not data:
        return [["Field", "Value"]]

    # Round frequencies
    freq_keys = ['afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
    
    info_list = [
        ["Variant ID", data.get('variant_id', '-')],
        ["Chromosome", data.get('chrom', '-')],
        ["Position", str(data.get('pos', '-'))],
        ["Reference", data.get('ref', '-')],
        ["Alternate", data.get('alt', '-')],
    ]
    
    # Add population frequencies
    for key in freq_keys:
        label = key.replace('_freq', '').upper()
        val = data.get(key, 0)
        info_list.append([f"{label} Frequency", f"{val:.6f}" if val is not None else "0.000000"])
        
    return info_list

def search_and_format_variant(variant_id):
    """Atomic function to search and format variant info for UI to reduce latency"""
    if not variant_id:
        return None, [["Field", "Value"]], "No ID provided."
    
    try:
        search_api = get_manticore_client()
        search_request = {
            'table': 'eva_variants',
            'query': {
                'match': {'variant_id': f"*{variant_id}*"}
            }
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return None, [["Field", "Value"]], f"Variant {variant_id} not found."

        data = hits[0].source

        # 1. Bar Chart Data
        freq_keys = ['afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
        freq_data = {
            'Population': [k.replace('_freq', '').upper() for k in freq_keys],
            'Frequency': [data.get(k, 0) or 0 for k in freq_keys]
        }
        df = pd.DataFrame(freq_data)
        fig = px.bar(df, x='Population', y='Frequency',
                     title=f"Population Frequencies for {variant_id}",
                     color='Population',
                     template="plotly_dark")
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        # 2. Table Data (List of Lists)
        info_table = format_variant_info_as_list(data)

        return fig, info_table, f"Showing results for {variant_id}"
    except Exception as e:
        print(f"Error searching variant: {e}")
        return None, [["Field", "Value"]], f"Error: {str(e)}"

# Gradio Interface - Premium Redesign
with gr.Blocks(
    title="EVA Population Frequencies"
) as app:
    with gr.Column():
        gr.Markdown("# Genomic Population Frequency Insights")
        gr.Markdown("Search for an NCBI variant ID to see its population distributions, and view regional density across the loaded ALFA project chromosome.")

        # Row 1: Search Section
        with gr.Row(variant="panel"):
            with gr.Column(scale=8):
                gr.Markdown("### Search")
                var_id_input = gr.Textbox(
                    label="Variant ID", 
                    placeholder="rs...", 
                    show_label=True,
                    container=True
                )
                # Nest dropdown here so it appears in the right place
                var_dropdown = gr.Dropdown(
                    label="Select Sample Variant",
                    choices=[],
                    value=None,
                    allow_custom_value=True,
                    interactive=True,
                    visible=False
                )
            with gr.Column(scale=1, min_width=150):
                gr.Markdown("<br>", visible=True) # Spacer
                search_btn = gr.Button("Search", variant="primary")
                examples_btn = gr.Button("Examples", variant="secondary")

        # Row 2: Information & Categorical Chart
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Variant Information")
                gr.Markdown("Variant Details")
                variant_info = gr.Dataframe(
                    headers=["Field", "Value"],
                    value=[],
                    interactive=False,
                    wrap=True
                )
            with gr.Column(scale=1):
                gr.Markdown("### Categorical Frequencies")
                bar_chart = gr.Plot(show_label=False)

        # Row 3: Chromosome Distribution (Full Width)
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Chromosome Distribution")
                density_plot = gr.Plot(show_label=False)

        # Row 4: Action Button
        with gr.Row():
            refresh_btn = gr.Button("Refresh Density Plot", variant="secondary")

    # Connect events
    search_btn.click(
        fn=lambda vid: (gr.update(value=vid, visible=False), None, None),
        inputs=var_id_input,
        outputs=[var_dropdown, bar_chart, variant_info]
    ).then(
        fn=search_and_format_variant,
        inputs=var_id_input,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    )

    var_dropdown.change(
        fn=search_and_format_variant,
        inputs=var_dropdown,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    )

    examples_btn.click(
        fn=show_examples,
        inputs=[],
        outputs=[var_dropdown, var_id_input]
    ).then(
        fn=search_and_format_variant,
        inputs=var_dropdown,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    )

    refresh_btn.click(fn=get_chromosome_distribution, inputs=[], outputs=density_plot)

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=False,
        theme=gr.themes.Soft(primary_hue="orange", neutral_hue="slate")
    )
