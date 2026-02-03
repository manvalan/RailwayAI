/**
 * Railway Network Topology Visualization
 * Handles drawing the network graph on canvas.
 */

window.loadTopology = async function () {
    try {
        const response = await fetch('/api/v1/network/topology', {
            headers: { 'X-API-Key': localStorage.getItem('access_token') }
        });

        if (response.ok) {
            const data = await response.json();
            renderTopology(data);
            updateTopologyStats(data);
        }
    } catch (error) {
        console.error('Failed to load topology:', error);
    }
};

function updateTopologyStats(data) {
    document.getElementById('topo-stat-nodes').textContent = data.nodes.length;
    document.getElementById('topo-stat-edges').textContent = data.edges.length;

    const density = data.nodes.length > 0 ? (data.edges.length / data.nodes.length).toFixed(2) : '0';
    document.getElementById('topo-stat-density').textContent = density;

    // Simple hub detection (nodes with degree > 3)
    const degrees = {};
    data.edges.forEach(e => {
        degrees[e.source] = (degrees[e.source] || 0) + 1;
        degrees[e.target] = (degrees[e.target] || 0) + 1;
    });
    const hubs = Object.values(degrees).filter(d => d > 3).length;
    document.getElementById('topo-stat-hubs').textContent = hubs;

    document.getElementById('topo-title').textContent = `🗺️ Topologia: ${data.scenario || 'Network'}`;
}

function renderTopology(data) {
    const canvas = document.getElementById('topo-canvas');
    const ctx = canvas.getContext('2d');
    const container = document.getElementById('topo-container');

    // Set canvas resolution
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    if (data.nodes.length === 0) return;

    // Normalization helper
    const lats = data.nodes.map(n => n.pos[0]);
    const lons = data.nodes.map(n => n.pos[1]);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    const padding = 50;
    const width = canvas.width - padding * 2;
    const height = canvas.height - padding * 2;

    function getX(lon) {
        if (maxLon === minLon) return canvas.width / 2;
        return padding + ((lon - minLon) / (maxLon - minLon)) * width;
    }

    function getY(lat) {
        if (maxLat === minLat) return canvas.height / 2;
        // Invert Y because canvas starts from top
        return canvas.height - (padding + ((lat - minLat) / (maxLat - minLat)) * height);
    }

    // Map degrees for visual weight
    const degrees = {};
    data.edges.forEach(e => {
        degrees[e.source] = (degrees[e.source] || 0) + 1;
        degrees[e.target] = (degrees[e.target] || 0) + 1;
    });

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Edges (Tracks)
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(79, 70, 229, 0.4)'; // var(--primary) with alpha

    data.edges.forEach(edge => {
        const sourceNode = data.nodes.find(n => n.id === edge.source);
        const targetNode = data.nodes.find(n => n.id === edge.target);

        if (sourceNode && targetNode) {
            ctx.beginPath();
            ctx.moveTo(getX(sourceNode.pos[1]), getY(sourceNode.pos[0]));
            ctx.lineTo(getX(targetNode.pos[1]), getY(targetNode.pos[0]));
            ctx.stroke();

            // Add subtle glow to high capacity tracks
            if (edge.capacity > 2) {
                ctx.save();
                ctx.lineWidth = 3;
                ctx.strokeStyle = 'rgba(79, 70, 229, 0.1)';
                ctx.stroke();
                ctx.restore();
            }
        }
    });

    // Draw Nodes (Stations)
    data.nodes.forEach(node => {
        const x = getX(node.pos[1]);
        const y = getY(node.pos[0]);
        const degree = degrees[node.id] || 0;
        const radius = 3 + Math.min(degree * 1.5, 10);

        // Station color
        let color = '#fff';
        if (degree > 4) color = '#f43f5e'; // Hub (accent)
        else if (degree > 2) color = '#4f46e5'; // Junction (primary)

        // Outer glow for hubs
        if (degree > 4) {
            ctx.shadowBlur = 10;
            ctx.shadowColor = color;
        } else {
            ctx.shadowBlur = 0;
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        // Label for major hubs
        if (degree > 3) {
            ctx.fillStyle = 'rgba(255,255,255,0.7)';
            ctx.font = '10px Inter';
            ctx.fillText(node.name, x + radius + 4, y + 3);
        }
    });

    // Interactivity (simple hover)
    canvas.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        let hoveredNode = null;
        for (const node of data.nodes) {
            const nx = getX(node.pos[1]);
            const ny = getY(node.pos[0]);
            const dist = Math.sqrt((mx - nx) ** 2 + (my - ny) ** 2);
            if (dist < 10) {
                hoveredNode = node;
                break;
            }
        }

        const overlay = document.getElementById('topo-overlay');
        if (hoveredNode) {
            overlay.style.display = 'block';
            document.getElementById('topo-node-name').textContent = hoveredNode.name;
            document.getElementById('topo-node-details').innerHTML = `
                ID: ${hoveredNode.id}<br>
                Type: ${hoveredNode.type}<br>
                Connessioni: ${degrees[hoveredNode.id] || 0}
            `;
        } else {
            overlay.style.display = 'none';
        }
    };
}

// Initial binding
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('topo-refresh-btn')?.addEventListener('click', window.loadTopology);
});
