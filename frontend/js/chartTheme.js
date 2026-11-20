// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

const COLORS = {
    text: "#52616d",
    grid: "#e2e8ed",
    axis: "#cbd4dc",
    navy: "#245b7a",
    amber: "#bd7026"
};

export const chartColors = COLORS;

export function createChartOptions({
    yTitle = "Value",
    xTitle = "Time",
    maintainAspectRatio = false
} = {}) {
    return {
        responsive: true,
        maintainAspectRatio,
        animation: false,
        interaction: { intersect: false, mode: "index" },
        elements: {
            line: { borderWidth: 2, tension: 0.2, fill: false, borderCapStyle: "round" },
            point: { radius: 0, hoverRadius: 3, hitRadius: 8 }
        },
        plugins: {
            legend: {
                display: true,
                position: "bottom",
                labels: {
                    color: COLORS.text,
                    usePointStyle: true,
                    pointStyle: "line",
                    boxWidth: 22,
                    boxHeight: 8,
                    padding: 16,
                    font: { family: "Verdana, Geneva, Tahoma, sans-serif", size: 12 }
                }
            },
            tooltip: {
                enabled: true,
                backgroundColor: "#173b56",
                titleColor: "#ffffff",
                bodyColor: "#f1f4f6",
                borderColor: "#526a7c",
                borderWidth: 1,
                padding: 10,
                displayColors: true,
                callbacks: {
                    label(context) {
                        const value = Number(context.parsed.y);
                        const formatted = Number.isFinite(value)
                            ? value.toLocaleString("en-CA", { maximumFractionDigits: 2 })
                            : "Unavailable";
                        return `${context.dataset.label}: ${formatted}`;
                    }
                }
            }
        },
        scales: {
            x: {
                title: {
                    display: Boolean(xTitle),
                    text: xTitle,
                    color: COLORS.text,
                    font: { weight: "600" }
                },
                grid: { color: COLORS.grid, drawTicks: false },
                border: { color: COLORS.axis },
                ticks: { color: COLORS.text, maxTicksLimit: 8, maxRotation: 0, padding: 8 }
            },
            y: {
                beginAtZero: true,
                title: {
                    display: Boolean(yTitle),
                    text: yTitle,
                    color: COLORS.text,
                    font: { weight: "600" }
                },
                grid: { color: COLORS.grid, drawTicks: false },
                border: { color: COLORS.axis },
                ticks: {
                    color: COLORS.text,
                    maxTicksLimit: 6,
                    padding: 8,
                    callback(value) {
                        return Number(value).toLocaleString("en-CA", { maximumFractionDigits: 1 });
                    }
                }
            }
        }
    };
}
