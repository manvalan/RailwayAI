/**
 * Railway Network Topology Visualization v2
 * Handles interactive drawing, zoom, and pan for network graph.
 */

class TopologyVisualizer {
    constructor(canvasId, containerId) {
        this.canvas = document.getElementById(canvasId);
        this.container = document.getElementById(containerId);
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
        this.degrees = {};

        this.scale = 0.9; // Base scale
        this.offsetX = 0;
        this.offsetY = 0;

        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;

        this.bounds = { minLat: 0, maxLat: 1, minLon: 0, maxLon: 1 };

        this.initEvents();
    }

    initEvents() {
        window.addEventListener('resize', () => this.resize());

        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
        });

        window.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                const dx = e.clientX - this.lastMouseX;
                const dy = e.clientY - this.lastMouseY;
                this.offsetX += dx;
                this.offsetY += dy;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.draw();
            }
            this.handleHover(e);
        });

        window.addEventListener('mouseup', () => {
            this.isDragging = false;
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomSpeed = 0.001;
            const factor = 1 - e.deltaY * zoomSpeed;
            this.zoomAt(e.offsetX, e.offsetY, factor);
        }, { passive: false });

        this.canvas.addEventListener('dblclick', () => {
            this.resetView();
        });
    }

    zoomAt(x, y, factor) {
        // Limit zoom
        const newScale = this.scale * factor;
        if (newScale < 0.1 || newScale > 20) return;

        // Zoom relative to mouse position
        this.offsetX = x - (x - this.offsetX) * factor;
        this.offsetY = y - (y - this.offsetY) * factor;
        this.scale = newScale;
        this.draw();
    }

    resetView() {
        if (!this.data) return;
        this.scale = 0.8;
        this.offsetX = this.canvas.width / 2;
        this.offsetY = this.canvas.height / 2;
        this.draw();
    }

    resize() {
        if (!this.container) return;
        this.canvas.width = this.container.clientWidth;
        this.canvas.height = this.container.clientHeight;
        this.draw();
    }

    setData(data) {
        this.data = data;
        if (!data.nodes || data.nodes.length === 0) return;

        // Pre-calculate degrees
        this.degrees = {};
        data.edges.forEach(e => {
            this.degrees[e.source] = (this.degrees[e.source] || 0) + 1;
            this.degrees[e.target] = (this.degrees[e.target] || 0) + 1;
        });

        // Calculate geographical bounds
        const lats = data.nodes.map(n => n.pos[0]);
        const lons = data.nodes.map(n => n.pos[1]);
        this.bounds = {
            minLat: Math.min(...lats),
            maxLat: Math.max(...lats),
            minLon: Math.min(...lons),
            maxLon: Math.max(...lons)
        };

        this.resize();
        this.resetView();
    }

    // Convert Geo to Local Map coordinates (keeping aspect ratio)
    geoToLocal(lat, lon) {
        const { minLat, maxLat, minLon, maxLon } = this.bounds;

        // Use a fixed reference scale to keep aspect ratio
        // 1 degree lat is approx 111km, 1 degree lon is approx 111km * cos(lat)
        // For simplicity we use 1:1 if lat range is small
        const rangeLat = maxLat - minLat || 0.0001;
        const rangeLon = maxLon - minLon || 0.0001;

        // Normalized coordinates (-1 to 1 range relative to center)
        const nx = ((lon - minLon) / rangeLon - 0.5) * 2;
        const ny = ((lat - minLat) / rangeLat - 0.5) * 2;

        // Apply scale based on viewport
        const viewSize = Math.min(this.canvas.width, this.canvas.height) * 0.45;

        // Preserving aspect ratio:
        // We want to map the larger dimension to the viewSize
        const aspect = rangeLon / rangeLat;
        let x, y;
        if (aspect > 1) {
            x = nx * viewSize;
            y = -ny * (viewSize / aspect); // Inverted Y for canvas
        } else {
            x = nx * (viewSize * aspect);
            y = -ny * viewSize;
        }

        return {
            x: x * this.scale + this.offsetX,
            y: y * this.scale + this.offsetY
        };
    }

    draw() {
        if (!this.data) return;
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid or background
        this.drawBackground();

        // Draw Edges
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(79, 70, 229, 0.4)';
        ctx.lineWidth = Math.max(0.5, 1.5 * this.scale);

        this.data.edges.forEach(edge => {
            const s = this.data.nodes.find(n => n.id === edge.source);
            const t = this.data.nodes.find(n => n.id === edge.target);
            if (s && t) {
                const p1 = this.geoToLocal(s.pos[0], s.pos[1]);
                const p2 = this.geoToLocal(t.pos[0], t.pos[1]);
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
            }
        });
        ctx.stroke();

        // Draw Nodes
        this.data.nodes.forEach(node => {
            const pos = this.geoToLocal(node.pos[0], node.pos[1]);
            const degree = this.degrees[node.id] || 0;
            const radius = (3 + Math.min(degree, 8)) * Math.sqrt(this.scale);

            let color = '#fff';
            if (degree > 4) color = '#f43f5e'; // Hub
            else if (degree > 2) color = '#4f46e5'; // Junction

            ctx.fillStyle = color;
            ctx.shadowBlur = degree > 4 ? 10 * this.scale : 0;
            ctx.shadowColor = color;

            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            ctx.fill();

            // Label for hubs or if zoomed in enough
            if (degree > 3 || this.scale > 3) {
                ctx.shadowBlur = 0;
                ctx.fillStyle = 'rgba(255,255,255,0.8)';
                ctx.font = `${Math.max(8, 11 * Math.sqrt(this.scale))}px Inter`;
                ctx.fillText(node.name, pos.x + radius + 4, pos.y + 3);
            }
        });
    }

    drawBackground() {
        const ctx = this.ctx;
        ctx.save();
        ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        ctx.lineWidth = 1;
        const spacing = 50 * this.scale;
        if (spacing > 10) {
            for (let x = this.offsetX % spacing; x < this.canvas.width; x += spacing) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.canvas.height); ctx.stroke();
            }
            for (let y = this.offsetY % spacing; y < this.canvas.height; y += spacing) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.canvas.width, y); ctx.stroke();
            }
        }
        ctx.restore();
    }

    handleHover(e) {
        if (!this.data || this.isDragging) return;
        const rect = this.canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        let hovered = null;
        for (const node of this.data.nodes) {
            const pos = this.geoToLocal(node.pos[0], node.pos[1]);
            const dist = Math.sqrt((pos.x - mx) ** 2 + (pos.y - my) ** 2);
            if (dist < 15) {
                hovered = node;
                break;
            }
        }

        const overlay = document.getElementById('topo-overlay');
        if (hovered) {
            overlay.style.display = 'block';
            document.getElementById('topo-node-name').textContent = hovered.name;
            document.getElementById('topo-node-details').innerHTML = `
                ID: ${hovered.id}<br>
                Type: ${hovered.type}<br>
                Connessioni: ${this.degrees[hovered.id] || 0}
            `;
            this.canvas.style.cursor = 'pointer';
        } else {
            overlay.style.display = 'none';
            this.canvas.style.cursor = 'crosshair';
        }
    }
}

// Singleton instance
let visualizer = null;

window.loadTopology = async function () {
    if (!visualizer) {
        visualizer = new TopologyVisualizer('topo-canvas', 'topo-container');
    }

    try {
        const response = await fetch('/api/v1/network/topology', {
            headers: { 'X-API-Key': localStorage.getItem('access_token') }
        });

        if (response.ok) {
            const data = await response.json();
            visualizer.setData(data);
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
    const degrees = {};
    data.edges.forEach(e => {
        degrees[e.source] = (degrees[e.source] || 0) + 1;
        degrees[e.target] = (degrees[e.target] || 0) + 1;
    });
    const hubs = Object.values(degrees).filter(d => d > 3).length;
    document.getElementById('topo-stat-hubs').textContent = hubs;
    document.getElementById('topo-title').textContent = `🗺️ Topologia: ${data.scenario || 'Network'}`;
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('topo-refresh-btn')?.addEventListener('click', window.loadTopology);
});
