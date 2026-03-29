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
        # Get sample variant IDs with full population data
        # Query multiple variants to find ones with good frequency data
        search_request = {
            'table': 'eva_variants',
            'limit': 1000,
            '_source': ['variant_id', 'afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
        }
        response = search_api.search(search_request)
        hits = response.hits.hits if response.hits else []

        if not hits:
            return []

        # Score variants by total population frequency data (count of non-zero frequencies)
        variant_scores = []
        for hit in hits:
            if not hit.source:
                continue
            data = hit.source
            # Count non-zero frequencies
            non_zero_count = sum(1 for key in ['afr_freq', 'amr_freq', 'eas_freq', 'eur_freq', 'sas_freq', 'aj_freq', 'fipa_freq', 'cau_freq', 'oth_freq', 'apl_freq', 'asn_freq', 'amr_cau_freq']
                               if data.get(key, 0) and data.get(key, 0) > 0)
            variant_scores.append({
                'variant_id': data.get('variant_id', ''),
                'score': non_zero_count,
                'data': data
            })

        # Sort by score (descending) and take top 10
        variant_scores.sort(key=lambda x: x['score'], reverse=True)
        top_variants = [v['variant_id'] for v in variant_scores[:10]]

        return top_variants
    except Exception as e:
        print(f"Error getting sample variants: {e}")
        return []

def show_examples():
    try:
        sample_variants = get_sample_variants()
        return gr.Dropdown(
            label="Select Sample Variant",
            choices=sample_variants,
            value=sample_variants[0] if sample_variants else None,
            allow_custom_value=True,
            interactive=True
        )
    except Exception as e:
        return gr.Dropdown(
            label="Select Sample Variant",
            choices=[],
            value=None,
            allow_custom_value=True,
            interactive=True
        )

def format_variant_info(variant_info):
    if not variant_info:
        return {
            'variant_id': '-',
            'chrom': '-',
            'pos': '-',
            'ref': '-',
            'alt': '-',
            'afr_freq': '-',
            'amr_freq': '-',
            'eas_freq': '-',
            'eur_freq': '-',
            'sas_freq': '-',
            'aj_freq': '-',
            'fipa_freq': '-',
            'cau_freq': '-',
            'oth_freq': '-',
            'apl_freq': '-',
            'asn_freq': '-',
            'amr_cau_freq': '-'
        }

    return {
        'variant_id': variant_info.get('variant_id', '-'),
        'chrom': variant_info.get('chrom', '-'),
        'pos': str(variant_info.get('pos', '-')),
        'ref': variant_info.get('ref', '-'),
        'alt': variant_info.get('alt', '-'),
        'afr_freq': f"{variant_info.get('afr_freq', 0):.6f}",
        'amr_freq': f"{variant_info.get('amr_freq', 0):.6f}",
        'eas_freq': f"{variant_info.get('eas_freq', 0):.6f}",
        'eur_freq': f"{variant_info.get('eur_freq', 0):.6f}",
        'sas_freq': f"{variant_info.get('sas_freq', 0):.6f}",
        'aj_freq': f"{variant_info.get('aj_freq', 0):.6f}",
        'fipa_freq': f"{variant_info.get('fipa_freq', 0):.6f}",
        'cau_freq': f"{variant_info.get('cau_freq', 0):.6f}",
        'oth_freq': f"{variant_info.get('oth_freq', 0):.6f}",
        'apl_freq': f"{variant_info.get('apl_freq', 0):.6f}",
        'asn_freq': f"{variant_info.get('asn_freq', 0):.6f}",
        'amr_cau_freq': f"{variant_info.get('amr_cau_freq', 0):.6f}"
    }

# Gradio Interface
with gr.Blocks(title="EVA Population Frequencies") as app:
    gr.Markdown("# Genomic Population Frequency Insights")
    gr.Markdown("Search for an NCBI variant ID to see its population distributions, and view regional density across the loaded ALFA project chromosome.")

    # Hide dropdown initially
    var_dropdown = gr.Dropdown(
        label="Select Sample Variant",
        choices=[],
        value=None,
        allow_custom_value=True,
        interactive=True,
        visible=False
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Search")
            var_id_input = gr.Textbox(label="Variant ID", placeholder="rs...")
            search_btn = gr.Button("Search", variant="primary")
            examples_btn = gr.Button("Examples", variant="secondary")

        with gr.Column(scale=1):
            gr.Markdown("### Variant Information")
            variant_info = gr.Dataframe(
                label="Variant Details",
                headers=["Field", "Value"],
                value=[],
                interactive=False,
                wrap=True
            )

    with gr.Row():
        with gr.Column(scale=1):
            bar_chart = gr.Plot(label="Categorical Frequencies")
        with gr.Column(scale=1):
            density_plot = gr.Plot(label="Chromosome Distribution")

    with gr.Row():
        refresh_btn = gr.Button("Refresh Density Plot")

    # Connect events
    search_btn.click(
        fn=lambda vid: (var_dropdown.update(value=vid, visible=True), None, None),
        inputs=var_id_input,
        outputs=[var_dropdown, bar_chart, variant_info]
    ).then(
        fn=search_variant,
        inputs=var_dropdown,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    ).then(
        fn=format_variant_info,
        inputs=variant_info,
        outputs=variant_info
    )

    var_dropdown.change(
        fn=search_variant,
        inputs=var_dropdown,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    ).then(
        fn=format_variant_info,
        inputs=variant_info,
        outputs=variant_info
    )

    examples_btn.click(
        fn=show_examples,
        inputs=[],
        outputs=var_dropdown
    ).then(
        fn=search_variant,
        inputs=var_dropdown,
        outputs=[bar_chart, variant_info, gr.Textbox(visible=False)]
    ).then(
        fn=format_variant_info,
        inputs=variant_info,
        outputs=variant_info
    )

    refresh_btn.click(fn=get_chromosome_distribution, inputs=[], outputs=density_plot)

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
