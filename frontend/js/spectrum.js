const SpectrumChart = {
    drawRaman(container, data) {
        const containerEl = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        if (!containerEl || !data || !data.spectrum_data) return;

        containerEl.innerHTML = '';

        const width = containerEl.clientWidth || 600;
        const height = containerEl.clientHeight || 300;
        const margin = { top: 20, right: 30, bottom: 40, left: 50 };

        const svg = d3.select(containerEl)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const w = width - margin.left - margin.right;
        const h = height - margin.top - margin.bottom;

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const wavelengths = data.wavelengths || data.spectrum_data.map((_, i) => i);
        const intensities = data.spectrum_data;

        const xScale = d3.scaleLinear()
            .domain(d3.extent(wavelengths))
            .range([0, w]);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(intensities) * 1.1])
            .range([h, 0]);

        const xAxis = d3.axisBottom(xScale)
            .ticks(8)
            .tickFormat(d => d + ' cm⁻¹');

        const yAxis = d3.axisLeft(yScale)
            .ticks(5);

        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${h})`)
            .call(xAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '10px');

        g.append('g')
            .attr('class', 'axis')
            .call(yAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '10px');

        g.selectAll('.axis path, .axis line')
            .style('stroke', 'rgba(255,255,255,0.2)');

        const line = d3.line()
            .x((d, i) => xScale(wavelengths[i]))
            .y(d => yScale(d))
            .curve(d3.curveBasis);

        const gradient = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'spectrumGradient')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '0%')
            .attr('y2', '100%');

        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#f5d742')
            .attr('stop-opacity', 0.8);

        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#f5d742')
            .attr('stop-opacity', 0.1);

        const area = d3.area()
            .x((d, i) => xScale(wavelengths[i]))
            .y0(h)
            .y1(d => yScale(d))
            .curve(d3.curveBasis);

        g.append('path')
            .datum(intensities)
            .attr('fill', 'url(#spectrumGradient)')
            .attr('d', area);

        g.append('path')
            .datum(intensities)
            .attr('fill', 'none')
            .attr('stroke', '#f5d742')
            .attr('stroke-width', 1.5)
            .attr('d', line);

        const peaks = this.findPeaks(intensities);
        if (peaks.length > 0) {
            const topPeaks = peaks.sort((a, b) => b.height - a.height).slice(0, 5);
            
            g.selectAll('.peak-label')
                .data(topPeaks)
                .enter()
                .append('text')
                .attr('class', 'peak-label')
                .attr('x', d => xScale(wavelengths[d.index]))
                .attr('y', d => yScale(d.height) - 5)
                .attr('text-anchor', 'middle')
                .style('fill', '#fff')
                .style('font-size', '9px')
                .text(d => wavelengths[d.index].toFixed(0));
        }

        g.append('text')
            .attr('x', w / 2)
            .attr('y', -5)
            .attr('text-anchor', 'middle')
            .style('fill', '#aaa')
            .style('font-size', '11px')
            .text('拉曼光谱 (Raman Spectrum)');

        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('padding', '8px 12px')
            .style('background', 'rgba(0,0,0,0.9)')
            .style('color', '#fff')
            .style('border-radius', '6px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('opacity', 0)
            .style('z-index', 100);

        const bisect = d3.bisector(d => d).left;

        svg.on('mousemove', function(event) {
            const [mx, my] = d3.pointer(event);
            const x0 = xScale.invert(mx - margin.left);
            
            let i = bisect(wavelengths, x0);
            i = Math.max(1, Math.min(i, wavelengths.length - 1));
            
            const d0 = wavelengths[i - 1];
            const d1 = wavelengths[i];
            const idx = x0 - d0 > d1 - x0 ? i : i - 1;
            
            if (idx >= 0 && idx < wavelengths.length) {
                tooltip
                    .style('opacity', 1)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px')
                    .html(`
                        <div>波数: ${wavelengths[idx].toFixed(1)} cm⁻¹</div>
                        <div>强度: ${intensities[idx].toFixed(4)}</div>
                    `);
            }
        })
        .on('mouseout', function() {
            tooltip.style('opacity', 0);
        });
    },

    drawXRF(container, data) {
        const containerEl = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        if (!containerEl || !data || !data.spectrum_data) return;

        containerEl.innerHTML = '';

        const width = containerEl.clientWidth || 600;
        const height = containerEl.clientHeight || 300;
        const margin = { top: 20, right: 30, bottom: 40, left: 50 };

        const svg = d3.select(containerEl)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const w = width - margin.left - margin.right;
        const h = height - margin.top - margin.bottom;

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const energies = data.energies || data.spectrum_data.map((_, i) => i);
        const intensities = data.spectrum_data;

        const xScale = d3.scaleLinear()
            .domain(d3.extent(energies))
            .range([0, w]);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(intensities) * 1.1])
            .range([h, 0]);

        const xAxis = d3.axisBottom(xScale)
            .ticks(8)
            .tickFormat(d => d + ' keV');

        const yAxis = d3.axisLeft(yScale)
            .ticks(5);

        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${h})`)
            .call(xAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '10px');

        g.append('g')
            .attr('class', 'axis')
            .call(yAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '10px');

        g.selectAll('.axis path, .axis line')
            .style('stroke', 'rgba(255,255,255,0.2)');

        const gradient = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'xrfGradient')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '0%')
            .attr('y2', '100%');

        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#4fc3f7')
            .attr('stop-opacity', 0.8);

        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#4fc3f7')
            .attr('stop-opacity', 0.05);

        const barWidth = w / energies.length;

        g.selectAll('.bar')
            .data(intensities)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', (d, i) => xScale(energies[i]) - barWidth/2)
            .attr('y', d => yScale(d))
            .attr('width', Math.max(1, barWidth - 0.5))
            .attr('height', d => h - yScale(d))
            .attr('fill', 'url(#xrfGradient)');

        const elementLabels = [
            { energy: 0.525, name: 'O', color: '#ff6b6b' },
            { energy: 1.49, name: 'Al', color: '#feca57' },
            { energy: 1.74, name: 'Si', color: '#48dbfb' },
            { energy: 3.69, name: 'Ca', color: '#ff9ff3' },
            { energy: 5.90, name: 'Mn', color: '#54a0ff' },
            { energy: 6.40, name: 'Fe', color: '#5f27cd' },
            { energy: 8.04, name: 'Cu', color: '#00d2d3' }
        ];

        elementLabels.forEach(el => {
            if (el.energy >= energies[0] && el.energy <= energies[energies.length - 1]) {
                const x = xScale(el.energy);
                
                g.append('line')
                    .attr('x1', x)
                    .attr('y1', 0)
                    .attr('x2', x)
                    .attr('y2', h)
                    .style('stroke', el.color)
                    .style('stroke-dasharray', '3,3')
                    .style('opacity', 0.5);

                g.append('text')
                    .attr('x', x)
                    .attr('y', 15)
                    .attr('text-anchor', 'middle')
                    .style('fill', el.color)
                    .style('font-size', '9px')
                    .style('font-weight', 'bold')
                    .text(el.name);
            }
        });

        g.append('text')
            .attr('x', w / 2)
            .attr('y', -5)
            .attr('text-anchor', 'middle')
            .style('fill', '#aaa')
            .style('font-size', '11px')
            .text('X射线荧光光谱 (XRF Spectrum)');
    },

    drawDiffusion(container, feData, mnData) {
        const containerEl = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        if (!containerEl) return;

        containerEl.innerHTML = '';

        const width = containerEl.clientWidth || 400;
        const height = containerEl.clientHeight || 200;
        const margin = { top: 20, right: 20, bottom: 35, left: 40 };

        const svg = d3.select(containerEl)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const w = width - margin.left - margin.right;
        const h = height - margin.top - margin.bottom;

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const feProfile = feData.concentration_profile || [];
        const mnProfile = mnData.concentration_profile || [];
        const depths = feData.depth_profile_mm || feProfile.map((_, i) => i * 0.1);

        const xScale = d3.scaleLinear()
            .domain([0, d3.max(depths) || 5])
            .range([0, w]);

        const allConcentrations = [...feProfile, ...mnProfile];
        const yScale = d3.scaleLinear()
            .domain([0, d3.max(allConcentrations) * 1.1 || 0.1])
            .range([h, 0]);

        const xAxis = d3.axisBottom(xScale)
            .ticks(5)
            .tickFormat(d => d.toFixed(1) + 'mm');

        const yAxis = d3.axisLeft(yScale)
            .ticks(4)
            .tickFormat(d => d.toFixed(3));

        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${h})`)
            .call(xAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '9px');

        g.append('g')
            .attr('class', 'axis')
            .call(yAxis)
            .selectAll('text')
            .style('fill', '#888')
            .style('font-size', '9px');

        g.selectAll('.axis path, .axis line')
            .style('stroke', 'rgba(255,255,255,0.15)');

        const feLine = d3.line()
            .x((d, i) => xScale(depths[i]))
            .y(d => yScale(d))
            .curve(d3.curveMonotoneX);

        const mnLine = d3.line()
            .x((d, i) => xScale(depths[i]))
            .y(d => yScale(d))
            .curve(d3.curveMonotoneX);

        g.append('path')
            .datum(feProfile)
            .attr('fill', 'none')
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 2)
            .attr('d', feLine);

        g.append('path')
            .datum(mnProfile)
            .attr('fill', 'none')
            .attr('stroke', '#4fc3f7')
            .attr('stroke-width', 2)
            .attr('d', mnLine);

        const legend = g.append('g')
            .attr('transform', `translate(${w - 100}, 10)`);

        legend.append('line')
            .attr('x1', 0).attr('y1', 0)
            .attr('x2', 20).attr('y2', 0)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 2);

        legend.append('text')
            .attr('x', 25)
            .attr('y', 4)
            .style('fill', '#aaa')
            .style('font-size', '10px')
            .text('Fe³+');

        legend.append('line')
            .attr('x1', 0).attr('y1', 18)
            .attr('x2', 20).attr('y2', 18)
            .attr('stroke', '#4fc3f7')
            .attr('stroke-width', 2);

        legend.append('text')
            .attr('x', 25)
            .attr('y', 22)
            .style('fill', '#aaa')
            .style('font-size', '10px')
            .text('Mn²+');
    },

    drawAnomalyChart(container, anomalyScore, forgeryProb) {
        const containerEl = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        if (!containerEl) return;

        containerEl.innerHTML = '';

        const width = containerEl.clientWidth || 400;
        const height = containerEl.clientHeight || 150;

        const svg = d3.select(containerEl)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const barHeight = 30;
        const barWidth = width - 80;
        const barX = 60;
        const barY = 30;

        const gradient = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'anomalyGradient')
            .attr('x1', '0%')
            .attr('x2', '100%');

        gradient.append('stop').attr('offset', '0%').attr('stop-color', '#2ed573');
        gradient.append('stop').attr('offset', '50%').attr('stop-color', '#feca57');
        gradient.append('stop').attr('offset', '100%').attr('stop-color', '#ff6b6b');

        svg.append('rect')
            .attr('x', barX)
            .attr('y', barY)
            .attr('width', barWidth)
            .attr('height', barHeight)
            .attr('fill', 'rgba(255,255,255,0.1)')
            .attr('rx', 5);

        const fillWidth = barWidth * Math.min(1, forgeryProb);
        svg.append('rect')
            .attr('x', barX)
            .attr('y', barY)
            .attr('width', fillWidth)
            .attr('height', barHeight)
            .attr('fill', 'url(#anomalyGradient)')
            .attr('rx', 5);

        const indicatorX = barX + barWidth * Math.min(1, forgeryProb);
        svg.append('circle')
            .attr('cx', indicatorX)
            .attr('cy', barY + barHeight / 2)
            .attr('r', 8)
            .attr('fill', '#fff')
            .attr('stroke', '#333')
            .attr('stroke-width', 2);

        svg.append('text')
            .attr('x', barX)
            .attr('y', barY - 8)
            .style('fill', '#aaa')
            .style('font-size', '11px')
            .text('作伪概率');

        svg.append('text')
            .attr('x', barX + barWidth)
            .attr('y', barY - 8)
            .attr('text-anchor', 'end')
            .style('fill', '#fff')
            .style('font-size', '14px')
            .style('font-weight', 'bold')
            .text((forgeryProb * 100).toFixed(1) + '%');

        svg.append('text')
            .attr('x', barX)
            .attr('y', barY + barHeight + 20)
            .style('fill', '#2ed573')
            .style('font-size', '10px')
            .text('真品');

        svg.append('text')
            .attr('x', barX + barWidth / 2)
            .attr('y', barY + barHeight + 20)
            .attr('text-anchor', 'middle')
            .style('fill', '#feca57')
            .style('font-size', '10px')
            .text('可疑');

        svg.append('text')
            .attr('x', barX + barWidth)
            .attr('y', barY + barHeight + 20)
            .attr('text-anchor', 'end')
            .style('fill', '#ff6b6b')
            .style('font-size', '10px')
            .text('疑似伪品');
    },

    findPeaks(spectrum) {
        const peaks = [];
        const threshold = d3.mean(spectrum) + d3.deviation(spectrum) * 0.5;

        for (let i = 2; i < spectrum.length - 2; i++) {
            if (spectrum[i] > spectrum[i-1] && 
                spectrum[i] > spectrum[i+1] && 
                spectrum[i] > threshold) {
                peaks.push({
                    index: i,
                    height: spectrum[i]
                });
            }
        }

        return peaks;
    }
};
