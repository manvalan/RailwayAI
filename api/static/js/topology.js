/**
 * Railway Network Topology Visualization v3 (English)
 * Advanced interactive graph renderer for infrastructure monitoring.
 */

class TopologyVisualizer {
    constructor(canvasId, containerId) {
        this.canvas = document.getElementById(canvasId);
        this.container = document.getElementById(containerId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
        this.degrees = {};

        this.scale = 0.9;
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
            const factor = 1 - e.deltaY * 0.001;
            this.zoomAt(e.offsetX, e.offsetY, factor);
        }, { passive: false });

        this.canvas.addEventListener('dblclick', () => this.resetView());
    }

    zoomAt(x, y, factor) {
        const newScale = this.scale * factor;
        if (newScale < 0.1 || newScale > 30) return;

        this.offsetX = x - (x - this.offsetX) * factor;
        this.offsetY = y - (y - this.offsetY) * factor;
        this.scale = newScale;
        this.draw();
    }

    resetView() {
        if (!this.data) return;
        this.scale = Math.min(this.canvas.width, this.canvas.height) / 1000;
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

        this.degrees = {};
        data.edges.forEach(e => {
            this.degrees[e.source] = (this.degrees[e.source] || 0) + 1;
            this.degrees[e.target] = (this.degrees[e.target] || 0) + 1;
        });

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

    geoToLocal(lat, lon) {
        const { minLat, maxLat, minLon, maxLon } = this.bounds;
        const rangeLat = maxLat - minLat || 0.0001;
        const rangeLon = maxLon - minLon || 0.0001;

        const nx = ((lon - minLon) / rangeLon - 0.5) * 2;
        const ny = ((lat - minLat) / rangeLat - 0.5) * 2;

        const viewSize = Math.min(this.canvas.width, this.canvas.height) * 0.4;
        const aspect = rangeLon / rangeLat;

        let x, y;
        if (aspect > 1) {
            x = nx * viewSize;
            y = -ny * (viewSize / aspect);
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

        // Grid
        ctx.save();
        ctx.strokeStyle = 'rgba(255,255,255,0.02)';
        const spacing = 40 * this.scale;
        if (spacing > 5) {
            for (let x = this.offsetX % spacing; x < this.canvas.width; x += spacing) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.canvas.height); ctx.stroke();
            }
            for (let y = this.offsetY % spacing; y < this.canvas.height; y += spacing) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.canvas.width, y); ctx.stroke();
            }
        }
        ctx.restore();

        // Links
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(79, 70, 229, 0.3)';
        ctx.lineWidth = Math.max(0.5, 1 * this.scale);
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

        // Nodes
        this.data.nodes.forEach(node => {
            const pos = this.geoToLocal(node.pos[0], node.pos[1]);
            const degree = this.degrees[node.id] || 0;
            const radius = (2 + Math.min(degree, 6)) * Math.sqrt(this.scale);

            let color = '#94a3b8';
            if (degree > 4) color = '#f43f5e';
            else if (degree > 2) color = '#4f46e5';

            ctx.fillStyle = color;
            if (degree > 4) {
                ctx.shadowBlur = 15 * this.scale;
                ctx.shadowColor = color;
            } else {
                ctx.shadowBlur = 0;
            }

            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            ctx.fill();

            if (degree > 4 || this.scale > 5) {
                ctx.shadowBlur = 0;
                ctx.fillStyle = '#f8fafc';
                ctx.font = `${Math.max(7, 10 * Math.sqrt(this.scale))}px Outfit`;
                ctx.fillText(node.name, pos.x + radius + 3, pos.y + 3);
            }
        });
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
            if (dist < 10) { hovered = node; break; }
        }

        const overlay = document.getElementById('topo-overlay');
        if (hovered) {
            overlay.style.display = 'block';
            document.getElementById('topo-node-name').textContent = hovered.name;
            document.getElementById('topo-node-details').innerHTML = `
                TIPO: ${hovered.type || 'STAZIONE'}<br>
                CONNESSIONI: ${this.degrees[hovered.id] || 0} linee<br>
                GPS: ${hovered.pos[0].toFixed(4)}, ${hovered.pos[1].toFixed(4)}
            `;
            this.canvas.style.cursor = 'pointer';
        } else {
            overlay.style.display = 'none';
            this.canvas.style.cursor = 'crosshair';
        }
    }
}

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
        console.error('Topology link failed:', error);
    }
};

function updateTopologyStats(data) {
    document.getElementById('topo-stat-nodes').textContent = data.nodes.length;
    document.getElementById('topo-stat-edges').textContent = data.edges.length;
    const density = data.nodes.length > 0 ? (data.edges.length / data.nodes.length).toFixed(2) : '0';
    document.getElementById('topo-stat-density').textContent = density;

    let hubCount = 0;
    Object.values(visualizer.degrees).forEach(d => { if (d > 3) hubCount++; });
    document.getElementById('topo-stat-hubs').textContent = hubCount;

    const title = document.getElementById('topo-title');
    if (title) title.textContent = `🗺️ Topologia di Rete: ${data.scenario || 'Settore Primario'}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('topo-refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', window.loadTopology);
});
