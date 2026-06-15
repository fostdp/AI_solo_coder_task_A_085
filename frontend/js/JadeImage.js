const JadeImage = {
    jadeTypes: {
        '玉璧': (ctx, w, h) => JadeImage.drawBi(ctx, w, h),
        '玉琮': (ctx, w, h) => JadeImage.drawCong(ctx, w, h),
        '玉钺': (ctx, w, h) => JadeImage.drawYue(ctx, w, h),
        '玉璜': (ctx, w, h) => JadeImage.drawHuang(ctx, w, h),
        '玉珠': (ctx, w, h) => JadeImage.drawZhu(ctx, w, h),
        '玉管': (ctx, w, h) => JadeImage.drawGuan(ctx, w, h),
        '玉兽': (ctx, w, h) => JadeImage.drawShou(ctx, w, h),
        '玉鸟': (ctx, w, h) => JadeImage.drawNiao(ctx, w, h)
    },

    drawJade(canvas, jadeType, options = {}) {
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        const bgGradient = ctx.createRadialGradient(w/2, h/2, 0, w/2, h/2, w/2);
        bgGradient.addColorStop(0, '#2a2a4a');
        bgGradient.addColorStop(1, '#1a1a2e');
        ctx.fillStyle = bgGradient;
        ctx.fillRect(0, 0, w, h);

        const drawFunc = this.jadeTypes[jadeType] || this.jadeTypes['玉璧'];
        drawFunc(ctx, w, h);
    },

    drawBi(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;
        const outerR = Math.min(w, h) * 0.38;
        const innerR = outerR * 0.35;

        const gradient = ctx.createRadialGradient(cx, cy, innerR, cx, cy, outerR);
        gradient.addColorStop(0, '#c8e6c9');
        gradient.addColorStop(0.3, '#a5d6a7');
        gradient.addColorStop(0.7, '#81c784');
        gradient.addColorStop(1, '#66bb6a');

        ctx.beginPath();
        ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
        ctx.arc(cx, cy, innerR, 0, Math.PI * 2, true);
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        for (let i = 0; i < 8; i++) {
            const angle = (i / 8) * Math.PI * 2;
            ctx.beginPath();
            ctx.moveTo(cx + Math.cos(angle) * innerR, cy + Math.sin(angle) * innerR);
            ctx.lineTo(cx + Math.cos(angle) * outerR, cy + Math.sin(angle) * outerR);
            ctx.stroke();
        }
    },

    drawCong(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;
        const size = Math.min(w, h) * 0.7;
        const half = size / 2;
        const innerSize = size * 0.35;

        ctx.beginPath();
        ctx.rect(cx - half, cy - half, size, size);
        const gradient = ctx.createLinearGradient(cx - half, cy - half, cx + half, cy + half);
        gradient.addColorStop(0, '#c8e6c9');
        gradient.addColorStop(0.5, '#a5d6a7');
        gradient.addColorStop(1, '#81c784');
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx, cy, innerSize, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 2;
        ctx.strokeRect(cx - half, cy - half, size, size);
        ctx.beginPath();
        ctx.arc(cx, cy, innerSize, 0, Math.PI * 2);
        ctx.stroke();

        const sections = 4;
        const sectionHeight = size / sections;
        for (let i = 1; i < sections; i++) {
            const y = cy - half + i * sectionHeight;
            ctx.beginPath();
            ctx.moveTo(cx - half, y);
            ctx.lineTo(cx + half, y);
            ctx.stroke();
        }
    },

    drawYue(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;
        const width = Math.min(w, h) * 0.6;
        const height = width * 0.8;

        ctx.beginPath();
        ctx.moveTo(cx - width/2, cy - height/2 + 20);
        ctx.lineTo(cx - width/3, cy - height/2);
        ctx.lineTo(cx + width/3, cy - height/2);
        ctx.lineTo(cx + width/2, cy - height/2 + 20);
        ctx.lineTo(cx + width/2, cy + height/2);
        ctx.quadraticCurveTo(cx, cy + height/2 + 10, cx - width/2, cy + height/2);
        ctx.closePath();

        const gradient = ctx.createLinearGradient(0, cy - height/2, 0, cy + height/2);
        gradient.addColorStop(0, '#b2dfdb');
        gradient.addColorStop(0.5, '#80cbc4');
        gradient.addColorStop(1, '#4db6ac');
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx, cy - height/4, width * 0.08, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();
    },

    drawHuang(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2 + 20;
        const r = Math.min(w, h) * 0.35;

        ctx.beginPath();
        ctx.arc(cx, cy, r, Math.PI, 0);
        ctx.lineTo(cx + r * 0.85, cy + r * 0.3);
        ctx.arc(cx, cy, r * 0.7, 0, Math.PI, true);
        ctx.closePath();

        const gradient = ctx.createLinearGradient(0, cy - r, 0, cy + r * 0.3);
        gradient.addColorStop(0, '#ffe0b2');
        gradient.addColorStop(0.5, '#ffcc80');
        gradient.addColorStop(1, '#ffb74d');
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx - r * 0.75, cy, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx + r * 0.75, cy, 6, 0, Math.PI * 2);
        ctx.fill();
    },

    drawZhu(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;
        const r = Math.min(w, h) * 0.3;

        const gradient = ctx.createRadialGradient(cx - r*0.3, cy - r*0.3, 0, cx, cy, r);
        gradient.addColorStop(0, '#f8bbd0');
        gradient.addColorStop(0.5, '#f48fb1');
        gradient.addColorStop(1, '#ec407a');

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx - r*0.3, cy - r*0.3, r * 0.2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.fill();
    },

    drawGuan(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;
        const width = Math.min(w, h) * 0.3;
        const height = Math.min(w, h) * 0.7;

        ctx.beginPath();
        ctx.ellipse(cx, cy - height/2, width/2, width*0.15, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#90caf9';
        ctx.fill();

        ctx.fillRect(cx - width/2, cy - height/2, width, height);

        ctx.beginPath();
        ctx.ellipse(cx, cy + height/2, width/2, width*0.15, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#42a5f5';
        ctx.fill();

        const gradient = ctx.createLinearGradient(cx - width/2, 0, cx + width/2, 0);
        gradient.addColorStop(0, '#64b5f6');
        gradient.addColorStop(0.5, '#90caf9');
        gradient.addColorStop(1, '#42a5f5');
        ctx.fillStyle = gradient;
        ctx.fillRect(cx - width/2, cy - height/2, width, height);
    },

    drawShou(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;

        ctx.beginPath();
        ctx.ellipse(cx, cy + 20, 60, 50, 0, 0, Math.PI * 2);
        const bodyGradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, 60);
        bodyGradient.addColorStop(0, '#c5cae9');
        bodyGradient.addColorStop(1, '#7986cb');
        ctx.fillStyle = bodyGradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx, cy - 35, 35, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(cx - 30, cy - 50);
        ctx.lineTo(cx - 40, cy - 75);
        ctx.lineTo(cx - 25, cy - 55);
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(cx + 30, cy - 50);
        ctx.lineTo(cx + 40, cy - 75);
        ctx.lineTo(cx + 25, cy - 55);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx - 12, cy - 35, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx + 12, cy - 35, 5, 0, Math.PI * 2);
        ctx.fill();
    },

    drawNiao(ctx, w, h) {
        const cx = w / 2;
        const cy = h / 2;

        ctx.beginPath();
        ctx.ellipse(cx, cy, 45, 35, -0.2, 0, Math.PI * 2);
        const bodyGradient = ctx.createLinearGradient(cx - 50, cy - 30, cx + 50, cy + 30);
        bodyGradient.addColorStop(0, '#b39ddb');
        bodyGradient.addColorStop(0.5, '#9575cd');
        bodyGradient.addColorStop(1, '#7e57c2');
        ctx.fillStyle = bodyGradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx + 35, cy - 15, 22, 0, Math.PI * 2);
        ctx.fillStyle = '#9575cd';
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(cx + 50, cy - 15);
        ctx.lineTo(cx + 65, cy - 12);
        ctx.lineTo(cx + 50, cy - 8);
        ctx.closePath();
        ctx.fillStyle = '#ffcc80';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx + 40, cy - 18, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        ctx.beginPath();
        ctx.ellipse(cx - 20, cy - 5, 30, 15, -0.5, 0, Math.PI * 2);
        ctx.fillStyle = '#b39ddb';
        ctx.fill();
    },

    drawOverlay(canvas, jadeType, densityMap, options = {}) {
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = w;
        tempCanvas.height = h;
        const tempCtx = tempCanvas.getContext('2d');

        PatinaDensity.draw(tempCanvas, densityMap, options);

        const maskCanvas = document.createElement('canvas');
        maskCanvas.width = w;
        maskCanvas.height = h;
        const maskCtx = maskCanvas.getContext('2d');

        const drawFunc = JadeImage.jadeTypes[jadeType] || JadeImage.jadeTypes['玉璧'];

        maskCtx.fillStyle = '#000';
        maskCtx.fillRect(0, 0, w, h);

        maskCtx.globalCompositeOperation = 'destination-out';
        drawFunc(maskCtx, w, h);

        const resultCtx = ctx;
        resultCtx.save();

        resultCtx.drawImage(tempCanvas, 0, 0);

        resultCtx.globalCompositeOperation = 'destination-in';
        resultCtx.drawImage(maskCanvas, 0, 0);

        resultCtx.restore();

        resultCtx.globalCompositeOperation = 'destination-over';

        JadeImage.drawJade(canvas, jadeType);

        resultCtx.globalCompositeOperation = 'source-over';
    },

    drawForgeryFrame(canvas, probability) {
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        const alpha = Math.min(1, probability * 2);

        ctx.strokeStyle = `rgba(255, 67, 54, ${alpha})`;
        ctx.lineWidth = 4;
        ctx.setLineDash([10, 5]);
        ctx.strokeRect(4, 4, w - 8, h - 8);
        ctx.setLineDash([]);

        ctx.shadowColor = 'rgba(255, 67, 54, 0.5)';
        ctx.shadowBlur = 10;
        ctx.strokeStyle = `rgba(255, 67, 54, ${alpha * 0.5})`;
        ctx.lineWidth = 2;
        ctx.strokeRect(6, 6, w - 12, h - 12);
        ctx.shadowBlur = 0;
    }
};
