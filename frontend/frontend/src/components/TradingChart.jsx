import React, { useEffect, useRef } from 'react';
import { createChart, LineSeries, ColorType } from 'lightweight-charts';

const WINDOW_SIZE = 300;
const FRAME_DELAY_MS = 40; // speed control

const TradingChart = ({ data = [] }) => {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const seriesRef = useRef(null);
    const animationRef = useRef(null);

    // 1️⃣ Create chart ONCE
    useEffect(() => {
        if (!chartContainerRef.current || chartRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#131722' },
                textColor: '#d1d4dc',
            },
            width: chartContainerRef.current.clientWidth,
            height: 500,
            timeScale: {
                rightOffset: 5,
                barSpacing: 6,
                fixLeftEdge: true,
            },
        });

        const lineSeries = chart.addSeries(LineSeries, {
            color: '#26a69a',
            lineWidth: 2,
        });

        chartRef.current = chart;
        seriesRef.current = lineSeries;

        const handleResize = () => {
            chart.applyOptions({
                width: chartContainerRef.current.clientWidth,
            });
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
            chartRef.current = null;
            seriesRef.current = null;
        };
    }, []);

    // 2️⃣ Animate sliding window
    useEffect(() => {
        if (!seriesRef.current || data.length < WINDOW_SIZE) return;

        let index = WINDOW_SIZE;

        animationRef.current = setInterval(() => {
            if (index >= data.length) {
                clearInterval(animationRef.current);
                return;
            }

            const windowData = data
                .slice(index - WINDOW_SIZE, index)
                .map(d => ({
                    time: d.time,
                    value: d.close,
                }));

            seriesRef.current.setData(windowData);
            chartRef.current.timeScale().scrollToRealTime();

            index++;
        }, FRAME_DELAY_MS);

        return () => clearInterval(animationRef.current);
    }, [data]);

    return (
        <div
            ref={chartContainerRef}
            style={{
                width: '100%',
                height: '500px',
                backgroundColor: '#131722',
            }}
        />
    );
};

export default TradingChart;
