/**
 * Railway Network Topology Visualization v4 (Premium)
 * Advanced interactive graph renderer with neon aesthetics and real-time animations.
 */

class TopologyVisualizer {
    constructor(canvasId, containerId) {
        this.canvas = document.getElementById(canvasId);
        this.container = document.getElementById(containerId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.data = null;
        this.degrees = {};
        this.hoveredNode = null;
        this.selectedNode = null;

        this.scale = 1.0;
        this.offsetX = 0;
        this.offsetY = 0;

        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;

        this.animationFrame = null;
        this.dashOffset = 0;

        this.bounds = { minLat: 0, maxLat: 1, minLon: 0, maxLon: 1 };
        this.initEvents();
        this.startAnimation();
    }

    initEvents() {
        window.addEventListener('resize', () => this.resize());

        this.canvas.addEventListener('mousedown', (e) => {
            if (e.button === 0) { // Left click
                this.isDragging = true;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;

                // Selection logic
                const rect = this.canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left;
                const my = e.clientY - rect.top;
                this.selectedNode = this.findNodeAt(mx, my);
                this.draw();
            }
        });

        window.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            if (this.isDragging) {
                const dx = e.clientX - this.lastMouseX;
                const dy = e.clientY - this.lastMouseY;
                this.offsetX += dx;
                this.offsetY += dy;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.draw();
            } else {
                const prevHover = this.hoveredNode;
                this.hoveredNode = this.findNodeAt(mx, my);
                if (prevHover !== this.hoveredNode) {
                    this.handleHover();
                    this.draw();
                }
            }
        });

        window.addEventListener('mouseup', () => {
            this.isDragging = false;
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomAt(e.offsetX, e.offsetY, factor);
        }, { passive: false });

        this.canvas.addEventListener('dblclick', () => this.resetView());
    }

    findNodeAt(mx, my) {
        if (!this.data) return null;
        for (const node of this.data.nodes) {
            const pos = this.geoToLocal(node.pos[0], node.pos[1]);
            const dist = Math.sqrt((pos.x - mx) ** 2 + (pos.y - my) ** 2);
            if (dist < 15) return node;
        }
        return null;
    }

    zoomAt(x, y, factor) {
        const newScale = this.scale * factor;
        if (newScale < 0.05 || newScale > 50) return;

        this.offsetX = x - (x - this.offsetX) * factor;
        this.offsetY = y - (y - this.offsetY) * factor;
        this.scale = newScale;
        this.draw();
    }

    resetView() {
        if (!this.data || this.data.nodes.length === 0) return;

        this.resize();

        const padding = 50;
        const viewWidth = this.canvas.width - padding * 2;
        const viewHeight = this.canvas.height - padding * 2;

        // Calculate the bounding box in "unscaled local coordinates" (offset=0, scale=1)
        // But geoToLocal depends on scale, so let's simplify.
        // We'll just center and pick a reasonable scale.
        this.scale = Math.min(this.canvas.width, this.canvas.height) / 1200;
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
            const sId = String(e.source);
            const tId = String(e.target);
            this.degrees[sId] = (this.degrees[sId] || 0) + 1;
            this.degrees[tId] = (this.degrees[tId] || 0) + 1;
        });

        const lats = data.nodes.map(n => n.pos[0]).filter(v => v != null && !isNaN(v));
        const lons = data.nodes.map(n => n.pos[1]).filter(v => v != null && !isNaN(v));
        this.bounds = {
            minLat: Math.min(...lats),
            maxLat: Math.max(...lats),
            minLon: Math.min(...lons),
            maxLon: Math.max(...lons)
        };

        this.resetView();
    }

    geoToLocal(lat, lon) {
        const { minLat, maxLat, minLon, maxLon } = this.bounds;
        const rangeLat = maxLat - minLat || 0.0001;
        const rangeLon = maxLon - minLon || 0.0001;

        // Mercator projection approximation for small scales
        const nx = ((lon - minLon) / rangeLon - 0.5) * 2;
        const ny = ((lat - minLat) / rangeLat - 0.5) * 2;

        const baseSize = 800; // Reference size
        const aspect = rangeLon / (rangeLat * Math.cos(lat * Math.PI / 180));

        let x, y;
        if (aspect > 1) {
            x = nx * baseSize;
            y = -ny * (baseSize / aspect);
        } else {
            x = nx * (baseSize * aspect);
            y = -ny * baseSize;
        }

        return {
            x: x * this.scale + this.offsetX,
            y: y * this.scale + this.offsetY
        };
    }

    startAnimation() {
        const animate = () => {
            this.dashOffset -= 0.5;
            this.draw();
            this.animationFrame = requestAnimationFrame(animate);
        };
        // Avoid starting multiple loops
        if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
        this.animationFrame = requestAnimationFrame(animate);
    }

    draw() {
        if (!this.data || !this.ctx) return;
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Drawing Grid (Deep Space Atmosphere)
        this.drawGrid(ctx, w, h);

        // Draw Links (Edges)
        this.drawEdges(ctx);

        // Draw Nodes (Stations)
        this.drawNodes(ctx);
    }

    drawGrid(ctx, w, h) {
        ctx.save();
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.05)';
        ctx.lineWidth = 1;
        const spacing = 50 * this.scale;
        if (spacing > 10) {
            ctx.beginPath();
            for (let x = this.offsetX % spacing; x < w; x += spacing) {
                ctx.moveTo(x, 0); ctx.lineTo(x, h);
            }
            for (let y = this.offsetY % spacing; y < h; y += spacing) {
                ctx.moveTo(0, y); ctx.lineTo(w, y);
            }
            ctx.stroke();
        }
        ctx.restore();
    }

    drawEdges(ctx) {
        ctx.save();
        // Background track (dim)
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(71, 85, 105, 0.2)';
        ctx.lineWidth = Math.max(0.5, 1.5 * this.scale);

        const edgePaths = [];
        this.data.edges.forEach(edge => {
            const sVal = String(edge.source);
            const tVal = String(edge.target);
            const s = this.data.nodes.find(n => String(n.id) === sVal);
            const t = this.data.nodes.find(n => String(n.id) === tVal);
            if (s && t) {
                const p1 = this.geoToLocal(s.pos[0], s.pos[1]);
                const p2 = this.geoToLocal(t.pos[0], t.pos[1]);
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                edgePaths.push({ p1, p2, edge });
            }
        });
        ctx.stroke();

        // Highlighted Edges (Connected to Selected Node)
        if (this.selectedNode) {
            ctx.beginPath();
            ctx.strokeStyle = '#f43f5e';
            ctx.lineWidth = Math.max(2, 4 * this.scale);
            ctx.shadowBlur = 10 * this.scale;
            ctx.shadowColor = 'rgba(244, 63, 94, 0.6)';
            edgePaths.forEach(({ p1, p2, edge }) => {
                if (String(edge.source) === String(this.selectedNode.id) || String(edge.target) === String(this.selectedNode.id)) {
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                }
            });
            ctx.stroke();
            ctx.shadowBlur = 0;
        }

        // Active "Pulse" Overlay (Neon Flow)
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)';
        ctx.setLineDash([10 * this.scale, 20 * this.scale]);
        ctx.lineDashOffset = this.dashOffset;
        ctx.lineWidth = Math.max(1, 2 * this.scale);
        edgePaths.forEach(({ p1, p2 }) => {
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
        });
        ctx.stroke();
        ctx.restore();
    }


    drawNodes(ctx) {
        this.data.nodes.forEach(node => {
            const pos = this.geoToLocal(node.pos[0], node.pos[1]);
            const degree = this.degrees[String(node.id)] || 0;
            const isHovered = this.hoveredNode && this.hoveredNode.id === node.id;
            const isSelected = this.selectedNode && this.selectedNode.id === node.id;

            const baseRadius = 3 + Math.min(degree, 8);
            const radius = (isHovered ? baseRadius * 1.5 : baseRadius) * Math.sqrt(this.scale);

            let color = '#94a3b8';
            let glow = 'rgba(148, 163, 184, 0.3)';

            if (degree >= 5) { // Hub
                color = '#6366f1';
                glow = 'rgba(99, 102, 241, 0.6)';
            } else if (degree >= 3) { // Junction
                color = '#818cf8';
                glow = 'rgba(129, 140, 248, 0.4)';
            }

            if (isSelected) {
                color = '#f43f5e';
                glow = 'rgba(244, 63, 94, 0.8)';
            } else if (isHovered) {
                color = '#fff';
                glow = 'rgba(255, 255, 255, 0.8)';
            }

            // Glow effect
            ctx.save();
            ctx.shadowBlur = (isHovered || isSelected || degree >= 5) ? 15 * this.scale : 0;
            ctx.shadowColor = glow;

            ctx.fillStyle = color;
            ctx.beginPath();
            if (degree >= 5) {
                // Star shape for hubs
                this.drawStar(ctx, pos.x, pos.y, 5, radius * 1.5, radius * 0.7);
            } else {
                ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            }
            ctx.fill();

            // Core
            if (degree >= 5 || isHovered) {
                ctx.fillStyle = '#fff';
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, radius * 0.4, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.restore();

            // Label text
            if (isHovered || isSelected || (degree >= 5 && this.scale > 0.5) || this.scale > 3) {
                ctx.fillStyle = isSelected ? '#f43f5e' : (isHovered ? '#fff' : '#94a3b8');
                ctx.font = `${isSelected ? 'bold' : ''} ${Math.max(10, 12 * Math.sqrt(this.scale))}px Outfit`;
                ctx.textAlign = 'center';
                ctx.fillText(node.name, pos.x, pos.y - radius - 10);
            }
        });
    }

    drawStar(ctx, cx, cy, spikes, outerRadius, innerRadius) {
        let rot = Math.PI / 2 * 3;
        let x = cx;
        let y = cy;
        let step = Math.PI / spikes;

        ctx.beginPath();
        ctx.moveTo(cx, cy - outerRadius);
        for (let i = 0; i < spikes; i++) {
            x = cx + Math.cos(rot) * outerRadius;
            y = cy + Math.sin(rot) * outerRadius;
            ctx.lineTo(x, y);
            rot += step;

            x = cx + Math.cos(rot) * innerRadius;
            y = cy + Math.sin(rot) * innerRadius;
            ctx.lineTo(x, y);
            rot += step;
        }
        ctx.lineTo(cx, cy - outerRadius);
        ctx.closePath();
    }

    handleHover() {
        const overlay = document.getElementById('topo-overlay');
        if (this.hoveredNode) {
            overlay.style.display = 'block';
            document.getElementById('topo-node-name').textContent = this.hoveredNode.name.toUpperCase();
            document.getElementById('topo-node-name').style.color = (this.degrees[this.hoveredNode.id] >= 5) ? 'var(--primary)' : 'var(--text-primary)';

            document.getElementById('topo-node-details').innerHTML = `
                <div style="display:grid; grid-template-columns: 1fr; gap:0.4rem; margin-top:0.8rem;">
                    <span style="font-size:0.7rem; color:var(--text-secondary);">TIPO: <strong>${this.hoveredNode.type || 'STAZIONE'}</strong></span>
                    <span style="font-size:0.7rem; color:var(--text-secondary);">GRADO: <strong>${this.degrees[this.hoveredNode.id] || 0} linee</strong></span>
                    <span style="font-size:0.6rem; color:var(--primary); opacity:0.8;">COORD: ${this.hoveredNode.pos[0].toFixed(4)}, ${this.hoveredNode.pos[1].toFixed(4)}</span>
                </div>
            `;
            this.canvas.style.cursor = 'pointer';
        } else if (!this.selectedNode) {
            overlay.style.display = 'none';
            this.canvas.style.cursor = 'crosshair';
        }
    }
}

let visualizer = null;

window.loadTopology = async function () {
    const topoContainer = document.getElementById('topo-container');
    if (!topoContainer) return;

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
    const nodesEl = document.getElementById('topo-stat-nodes');
    const edgesEl = document.getElementById('topo-stat-edges');
    const densityEl = document.getElementById('topo-stat-density');
    const hubsEl = document.getElementById('topo-stat-hubs');

    if (nodesEl) nodesEl.textContent = data.nodes.length;
    if (edgesEl) edgesEl.textContent = data.edges.length;

    const density = data.nodes.length > 0 ? (data.edges.length / data.nodes.length).toFixed(2) : '0';
    if (densityEl) densityEl.textContent = density;

    let hubCount = 0;
    Object.values(visualizer.degrees).forEach(d => { if (d >= 5) hubCount++; });
    if (hubsEl) hubsEl.textContent = hubCount;

    const title = document.getElementById('topo-title');
    if (title) title.textContent = `🗺️ Topologia di Rete: ${data.scenario || 'Settore Core'}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('topo-refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', window.loadTopology);
});

