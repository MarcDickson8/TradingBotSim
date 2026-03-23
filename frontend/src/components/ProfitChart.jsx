import React, { useEffect, useRef } from 'react';
import { createChart, LineSeries, ColorType } from 'lightweight-charts';

const ProfitChart = ({ data = [] }) => {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!chartContainerRef.current || data.length === 0) return;

        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#131722' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: '#2b2b43' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 250,
            timeScale: { rightOffset: 0, fixLeftEdge: true, fixRightEdge: true, minBarSpacing: 0.001 },
            handleScroll: false,
            handleScale: false,
        });

        const profitSeries = chart.addSeries(LineSeries, {
            color: '#26a69a',
            lineWidth: 2,
            priceLineVisible: false,
        });

        const seriesData = data.map(d => ({
            time: d.time,
            value: d.total_profit,
        }));

        profitSeries.setData(seriesData);
        requestAnimationFrame(() => chart.timeScale().fitContent());

        chartRef.current = chart;

        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            requestAnimationFrame(() => chart.timeScale().fitContent());
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
            chartRef.current = null;
        };
    }, [data]);

    return (
        <div>
            <div style={{ padding: '10px 12px', fontSize: '13px', color: '#aaa', borderBottom: '1px solid #2b2b43' }}>
                Total Profit Over Time
            </div>
            <div ref={chartContainerRef} style={{ width: '100%', height: '250px', backgroundColor: '#131722' }} />
        </div>
    );
};

export default ProfitChart;
