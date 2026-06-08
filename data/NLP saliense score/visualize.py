"""Interactive Plotly HTML report generation for entity salience analysis."""

import json
import logging
import os
from collections import defaultdict
from urllib.parse import urlparse

import networkx as nx
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from db import (
    get_db,
    get_top_entities,
    get_entities_for_domain,
    get_clusters,
    get_cluster_pages,
    get_pages,
)
from compare import get_entity_type_distribution
from utils import clean_domain

log = logging.getLogger("salience.visualize")

# ---------------------------------------------------------------------------
# Chart 1: Entity Salience Heatmap
# ---------------------------------------------------------------------------

def plot_salience_heatmap(domain, config, db_path=None):
    """Heatmap of top entities × pages, color = salience score."""
    domain = clean_domain(domain)
    top_n = config.get("visualization", {}).get("top_entities_heatmap", 50)

    with get_db(db_path) as conn:
        top_ents = get_top_entities(conn, domain, top_n=top_n)
        entity_names = [e["entity_name"] for e in top_ents]

        pages = get_pages(conn, domain, status="analyzed")
        page_urls = [p["url"] for p in pages]

        # Shorten URLs for display
        page_labels = [urlparse(u).path or "/" for u in page_urls]

        # Build matrix
        matrix = np.zeros((len(page_urls), len(entity_names)))
        all_entities = get_entities_for_domain(conn, domain)
        url_idx = {u: i for i, u in enumerate(page_urls)}
        ent_idx = {n: i for i, n in enumerate(entity_names)}

        for e in all_entities:
            if e["url"] in url_idx and e["entity_name"] in ent_idx:
                matrix[url_idx[e["url"]], ent_idx[e["entity_name"]]] = e["salience"]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=entity_names,
        y=page_labels,
        colorscale="YlOrRd",
        colorbar=dict(title="Salience"),
        hovertemplate="Entity: %{x}<br>Page: %{y}<br>Salience: %{z:.4f}<extra></extra>",
    ))

    fig.update_layout(
        title=f"Entity Salience Heatmap — {domain}",
        xaxis_title="Entities",
        yaxis_title="Pages",
        height=max(400, len(page_urls) * 20),
        width=max(800, len(entity_names) * 25),
        xaxis=dict(tickangle=45),
        margin=dict(b=150),
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 2: Entity Network Graph
# ---------------------------------------------------------------------------

def plot_entity_network(domain, config, db_path=None):
    """Network graph: nodes = entities, edges = co-occurrence, size = salience."""
    domain = clean_domain(domain)
    top_n = config.get("visualization", {}).get("top_entities_network", 75)
    min_edge = config.get("visualization", {}).get("min_edge_weight", 2)

    with get_db(db_path) as conn:
        top_ents = get_top_entities(conn, domain, top_n=top_n)
        entity_set = {e["entity_name"] for e in top_ents}
        entity_salience = {e["entity_name"]: e["avg_salience"] for e in top_ents}
        entity_type = {}
        for e in top_ents:
            entity_type[e["entity_name"]] = e.get("entity_type", "OTHER")

        pages = get_pages(conn, domain, status="analyzed")

        # Build co-occurrence counts
        cooccurrence = defaultdict(int)
        for p in pages:
            page_ents = conn.execute(
                "SELECT entity_name FROM entities WHERE url=? AND entity_name IN ({})".format(
                    ",".join("?" * len(entity_set))
                ),
                [p["url"]] + list(entity_set),
            ).fetchall()
            names = [r["entity_name"] for r in page_ents]
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    pair = tuple(sorted([names[i], names[j]]))
                    cooccurrence[pair] += 1

    # Build networkx graph
    G = nx.Graph()
    for name in entity_set:
        G.add_node(name, salience=entity_salience.get(name, 0), type=entity_type.get(name, "OTHER"))

    for (a, b), weight in cooccurrence.items():
        if weight >= min_edge:
            G.add_edge(a, b, weight=weight)

    # Remove isolated nodes
    isolated = list(nx.isolates(G))
    G.remove_nodes_from(isolated)

    if len(G.nodes) == 0:
        return _empty_figure("Entity Network", "No co-occurring entities found")

    # Layout
    pos = nx.spring_layout(G, k=2 / np.sqrt(len(G.nodes)), seed=42)

    # Type → color mapping
    type_colors = {
        "PERSON": "#FF6B6B", "ORGANIZATION": "#4ECDC4", "LOCATION": "#45B7D1",
        "EVENT": "#96CEB4", "WORK_OF_ART": "#FFEAA7", "CONSUMER_GOOD": "#DDA0DD",
        "NUMBER": "#98D8C8", "OTHER": "#C0C0C0", "UNKNOWN": "#C0C0C0",
        "PHONE_NUMBER": "#98D8C8", "ADDRESS": "#45B7D1", "DATE": "#96CEB4",
        "PRICE": "#FFD93D",
    }

    # Edge traces
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
    )

    # Node traces
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_text = list(G.nodes())
    node_size = [max(10, G.nodes[n]["salience"] * 80) for n in G.nodes()]
    node_color = [type_colors.get(G.nodes[n].get("type", "OTHER"), "#C0C0C0") for n in G.nodes()]

    hover_text = [
        f"{n}<br>Type: {G.nodes[n].get('type', 'OTHER')}<br>"
        f"Salience: {G.nodes[n]['salience']:.4f}<br>"
        f"Connections: {G.degree(n)}"
        for n in G.nodes()
    ]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_text, textposition="top center", textfont=dict(size=8),
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="white")),
        hovertext=hover_text, hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Entity Network — {domain}",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=700, width=1000,
        plot_bgcolor="white",
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 3: Competitor Comparison Bars
# ---------------------------------------------------------------------------

def plot_competitor_bars(comparison, config):
    """Side-by-side bar chart of top entity salience per domain."""
    primary = comparison["primary"]
    all_domains = [primary] + comparison["competitors"]

    # Get top 25 entities by primary salience
    overlap = comparison["overlap"][:25]
    entity_names = [e["entity_name"] for e in overlap]

    fig = go.Figure()
    colors = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"]

    for i, d in enumerate(all_domains):
        saliences = []
        for e in overlap:
            if d == primary:
                saliences.append(e["primary_salience"])
            else:
                saliences.append(e.get(f"{d}_salience", 0))

        fig.add_trace(go.Bar(
            name=d,
            x=entity_names,
            y=saliences,
            marker_color=colors[i % len(colors)],
        ))

    fig.update_layout(
        title="Competitor Entity Salience Comparison (Top 25 Shared Entities)",
        barmode="group",
        xaxis_title="Entity",
        yaxis_title="Average Salience",
        xaxis=dict(tickangle=45),
        height=500, width=1000,
        margin=dict(b=150),
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 4: Topic Coverage Radar
# ---------------------------------------------------------------------------

def plot_type_radar(primary_domain, competitor_domains, config, db_path=None):
    """Radar chart of entity type distribution per domain."""
    all_domains = [clean_domain(primary_domain)] + [clean_domain(d) for d in competitor_domains]
    colors = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"]

    # Get type distributions
    all_types = set()
    distributions = {}
    for d in all_domains:
        dist = get_entity_type_distribution(d, config, db_path)
        distributions[d] = {r["entity_type"]: r["count"] for r in dist}
        all_types.update(distributions[d].keys())

    categories = sorted(all_types)

    fig = go.Figure()
    for i, d in enumerate(all_domains):
        values = [distributions[d].get(t, 0) for t in categories]
        # Normalize to percentages
        total = sum(values) or 1
        values_pct = [v / total * 100 for v in values]
        values_pct.append(values_pct[0])  # Close the radar

        fig.add_trace(go.Scatterpolar(
            r=values_pct,
            theta=categories + [categories[0]],
            name=d,
            line_color=colors[i % len(colors)],
            fill="toself",
            opacity=0.3,
        ))

    fig.update_layout(
        title="Entity Type Coverage (% Distribution)",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=600, width=700,
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 5: Gap Analysis Table
# ---------------------------------------------------------------------------

def plot_gap_table(comparison, config):
    """Interactive table of entity gaps."""
    gaps = comparison["gaps"][:50]  # Top 50 gaps

    if not gaps:
        return _empty_figure("Gap Analysis", "No entity gaps found")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Entity", "Type", "Competitor", "Salience", "Mentions", "Pages"],
            fill_color="#2196F3",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=[
                [g["entity_name"] for g in gaps],
                [g.get("entity_type", "") for g in gaps],
                [g["competitor"] for g in gaps],
                [f"{g['competitor_salience']:.4f}" for g in gaps],
                [g["competitor_mentions"] for g in gaps],
                [g["competitor_pages"] for g in gaps],
            ],
            fill_color=[["#f9f9f9", "white"] * (len(gaps) // 2 + 1)][:len(gaps)],
            align="left",
        ),
    )])

    fig.update_layout(
        title="Entity Gaps — What Competitors Cover That You Don't",
        height=max(400, len(gaps) * 30),
        width=900,
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 6: Cluster Treemap
# ---------------------------------------------------------------------------

def plot_cluster_treemap(domain, method, config, db_path=None):
    """Treemap visualization of page clusters."""
    domain = clean_domain(domain)

    with get_db(db_path) as conn:
        clusters = get_clusters(conn, domain, method)

    if not clusters:
        return _empty_figure(f"Clusters ({method})", "No clusters found")

    labels, parents, values, hover = [], [], [], []
    root = f"{domain} — {method}"
    labels.append(root)
    parents.append("")
    values.append(0)
    hover.append(f"Total pages across all clusters")

    for c in clusters:
        top_ents = json.loads(c["top_entities"]) if c["top_entities"] else []
        label = c["label"] or f"Cluster {c['cluster_id']}"
        # Truncate long labels
        if len(label) > 50:
            label = label[:47] + "..."

        labels.append(label)
        parents.append(root)
        values.append(c["page_count"])
        hover.append(
            f"Cluster {c['cluster_id']}<br>"
            f"Pages: {c['page_count']}<br>"
            f"Top entities: {', '.join(top_ents[:3])}"
        )

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        hovertext=hover,
        hoverinfo="text",
        textinfo="label+value",
        marker=dict(colorscale="Blues"),
    ))

    fig.update_layout(
        title=f"Page Clusters — {method.title()} Method ({domain})",
        height=500, width=900,
    )

    return fig


# ---------------------------------------------------------------------------
# Chart 7: Dendrogram
# ---------------------------------------------------------------------------

def plot_dendrogram(linkage_info, domain, config):
    """Dendrogram from hierarchical clustering."""
    if not linkage_info:
        return _empty_figure("Dendrogram", "No hierarchical clustering data")

    from scipy.cluster.hierarchy import dendrogram as sci_dendrogram
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    linkage_matrix = np.array(linkage_info["linkage_matrix"])
    page_urls = linkage_info["page_urls"]
    labels = [urlparse(u).path or "/" for u in page_urls]

    # Truncate labels for readability
    labels = [l[:40] if len(l) > 40 else l for l in labels]

    # Create dendrogram data using scipy
    dend = sci_dendrogram(linkage_matrix, labels=labels, no_plot=True)

    # Convert to Plotly
    fig = go.Figure()

    # Draw the dendrogram lines
    for xs, ys, color in zip(dend["icoord"], dend["dcoord"], dend["color_list"]):
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=color if color != "C0" else "#2196F3", width=1.5),
            hoverinfo="skip", showlegend=False,
        ))

    fig.update_layout(
        title=f"Hierarchical Clustering Dendrogram — {domain}",
        xaxis=dict(
            ticktext=dend["ivl"],
            tickvals=list(range(5, len(dend["ivl"]) * 10 + 5, 10)),
            tickangle=90,
            tickfont=dict(size=8),
        ),
        yaxis_title="Distance",
        height=600,
        width=max(800, len(labels) * 15),
        margin=dict(b=200),
        plot_bgcolor="white",
    )

    return fig


# ---------------------------------------------------------------------------
# Assemble full report
# ---------------------------------------------------------------------------

def build_report(domain, config, comparison=None, linkage_info=None,
                 db_path=None, output_dir=None):
    """Build a complete interactive HTML report with all charts."""
    domain = clean_domain(domain)
    out_dir = output_dir or config.get("export", {}).get("output_dir", "./output")
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(os.path.dirname(__file__), out_dir)
    os.makedirs(out_dir, exist_ok=True)

    report_title = config.get("visualization", {}).get("report_title", "Entity Salience Analysis")
    filepath = os.path.join(out_dir, f"{domain.replace('.', '-')}_report.html")

    log.info(f"Building report for {domain}")

    # Collect all figures
    figures = []

    # 1. Heatmap
    try:
        fig = plot_salience_heatmap(domain, config, db_path)
        figures.append(("Entity Salience Heatmap", fig))
    except Exception as e:
        log.warning(f"Failed to create heatmap: {e}")

    # 2. Network graph
    try:
        fig = plot_entity_network(domain, config, db_path)
        figures.append(("Entity Network Graph", fig))
    except Exception as e:
        log.warning(f"Failed to create network graph: {e}")

    # 3. Competitor comparison
    if comparison:
        try:
            fig = plot_competitor_bars(comparison, config)
            figures.append(("Competitor Entity Comparison", fig))
        except Exception as e:
            log.warning(f"Failed to create competitor bars: {e}")

    # 4. Radar chart
    if comparison:
        try:
            fig = plot_type_radar(
                domain, comparison["competitors"], config, db_path
            )
            figures.append(("Entity Type Coverage Radar", fig))
        except Exception as e:
            log.warning(f"Failed to create radar chart: {e}")

    # 5. Gap table
    if comparison:
        try:
            fig = plot_gap_table(comparison, config)
            figures.append(("Entity Gap Analysis", fig))
        except Exception as e:
            log.warning(f"Failed to create gap table: {e}")

    # 6. Cluster treemaps (one per method)
    for method in ["cooccurrence", "kmeans", "hierarchical"]:
        try:
            fig = plot_cluster_treemap(domain, method, config, db_path)
            figures.append((f"Clusters — {method.title()}", fig))
        except Exception as e:
            log.warning(f"Failed to create {method} treemap: {e}")

    # 7. Dendrogram
    if linkage_info:
        try:
            fig = plot_dendrogram(linkage_info, domain, config)
            figures.append(("Hierarchical Dendrogram", fig))
        except Exception as e:
            log.warning(f"Failed to create dendrogram: {e}")

    # Assemble HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        f"<title>{report_title} — {domain}</title>",
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; ",
        "       margin: 0; padding: 20px; background: #f5f5f5; }",
        "h1 { color: #333; border-bottom: 3px solid #2196F3; padding-bottom: 10px; }",
        "h2 { color: #555; margin-top: 40px; }",
        ".chart { background: white; border-radius: 8px; padding: 20px; ",
        "         margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
        ".stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }",
        ".stat-card { background: white; border-radius: 8px; padding: 20px; ",
        "             box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-width: 150px; }",
        ".stat-card .number { font-size: 2em; font-weight: bold; color: #2196F3; }",
        ".stat-card .label { color: #777; font-size: 0.9em; }",
        "nav { position: sticky; top: 0; background: white; padding: 10px 20px; ",
        "      box-shadow: 0 2px 4px rgba(0,0,0,0.1); z-index: 100; margin: -20px -20px 20px; }",
        "nav a { margin-right: 15px; text-decoration: none; color: #2196F3; font-size: 0.9em; }",
        "nav a:hover { text-decoration: underline; }",
        "</style>",
        "</head><body>",
        f"<h1>{report_title} — {domain}</h1>",
    ]

    # Stats cards
    with get_db(db_path) as conn:
        from db import page_count
        total_pages = page_count(conn, domain)
        analyzed = page_count(conn, domain, "analyzed")
        entities = conn.execute(
            "SELECT COUNT(DISTINCT entity_name) as c FROM entities WHERE domain=?", (domain,)
        ).fetchone()["c"]

    html_parts.append('<div class="stats">')
    for label, value in [
        ("Pages Analyzed", analyzed),
        ("Unique Entities", entities),
        ("Total Pages", total_pages),
    ]:
        html_parts.append(
            f'<div class="stat-card"><div class="number">{value}</div>'
            f'<div class="label">{label}</div></div>'
        )
    if comparison:
        html_parts.append(
            f'<div class="stat-card"><div class="number">{comparison["stats"]["gap_count"]}</div>'
            f'<div class="label">Entity Gaps</div></div>'
        )
        html_parts.append(
            f'<div class="stat-card"><div class="number">{comparison["stats"]["overlap_count"]}</div>'
            f'<div class="label">Shared Entities</div></div>'
        )
    html_parts.append("</div>")

    # Navigation
    html_parts.append("<nav>")
    for i, (title, _) in enumerate(figures):
        anchor = title.lower().replace(" ", "-").replace("—", "")
        html_parts.append(f'<a href="#{anchor}">{title}</a>')
    html_parts.append("</nav>")

    # Charts
    for i, (title, fig) in enumerate(figures):
        anchor = title.lower().replace(" ", "-").replace("—", "")
        html_parts.append(f'<div class="chart" id="{anchor}">')
        html_parts.append(f"<h2>{title}</h2>")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        html_parts.append("</div>")

    html_parts.append("</body></html>")

    with open(filepath, "w") as f:
        f.write("\n".join(html_parts))

    log.info(f"Report saved to {filepath}")
    return filepath


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_figure(title, message):
    """Create a placeholder figure with a message."""
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(size=16, color="#999"))
    fig.update_layout(title=title, height=200)
    return fig
