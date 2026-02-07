import React, { useEffect, useRef } from 'react';
import { createChart, LineSeries, ColorType } from 'lightweight-charts';

const WINDOW_SIZE = 300;
const FRAME_DELAY_MS = 40; // speed control

const TradingChart = ({ data = [], activeTradeSpeed, generalSpeed, onUpdateSummary }) => {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const seriesRef = useRef(null);
    const timeoutRef = useRef(null);
    const stopLineRef = useRef(null);
    const entryLineRef = useRef(null);
    const upperSeriesRef = useRef(null);
    const lowerSeriesRef = useRef(null);
    

    activeTradeSpeed =  FRAME_DELAY_MS / activeTradeSpeed
    generalSpeed = FRAME_DELAY_MS / generalSpeed 


    // 1️⃣ Create chart ONCE
    useEffect(() => {
        if (!chartContainerRef.current || chartRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#131722' },
                textColor: '#d1d4dc',
            },

            grid: {
                vertLines: {
                visible: false,
                },
                horzLines: {
                visible: false,
                },
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
        const bbupperSeries = chart.addSeries(LineSeries, {
            color: '#264fa6ff',
            lineWidth: 2,
        });
        const bblowerSeries = chart.addSeries(LineSeries, {
            color: '#264fa6ff',
            lineWidth: 2,
        });

        chartRef.current = chart;
        seriesRef.current = lineSeries;
        upperSeriesRef.current = bbupperSeries;
        lowerSeriesRef.current = bblowerSeries;

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
            upperSeriesRef.current = null;
            lowerSeriesRef.current = null;
        };
    }, []);

    // 2️⃣ Animate sliding window
    useEffect(() => {
        if (!seriesRef.current || data.length < WINDOW_SIZE) return;

        let index = WINDOW_SIZE;


        const tick = () => {
            if (index >= data.length) {return;}

            const windowData = data
            .slice(index - WINDOW_SIZE, index)
            .map(d => ({
                time: d.time,
                value: d.close,
            }));

            const upperSeriesData = data
            .slice(index - WINDOW_SIZE, index)
            .map(d => ({
                time: d.time,
                value: d.bb_upper,
            }));

            const lowerSeriesData = data
            .slice(index - WINDOW_SIZE, index)
            .map(d => ({
                time: d.time,
                value: d.bb_lower,
            }));
            
            seriesRef.current.setData(windowData);
            upperSeriesRef.current.setData(upperSeriesData);
            lowerSeriesRef.current.setData(lowerSeriesData);
            chartRef.current.timeScale().scrollToRealTime();

            const currentBar = data[index - 1];
            const tradeActive = currentBar.entry_price > 0;

            // ---- Price lines ----
            if (stopLineRef.current) {
                seriesRef.current.removePriceLine(stopLineRef.current);
                stopLineRef.current = null;
                onUpdateSummary({
                    total_profit: data[index].total_profit,
                    trade_count: data[index].trade_count,
                });
            }
            if (entryLineRef.current) {
                seriesRef.current.removePriceLine(entryLineRef.current);
                entryLineRef.current = null;
            }

            if (tradeActive) {
                stopLineRef.current = seriesRef.current.createPriceLine({
                    price: currentBar.trailing_sl,
                    color: 'red',
                    lineWidth: 2,
                    title: 'Stop Loss',
                });

                entryLineRef.current = seriesRef.current.createPriceLine({
                    price: currentBar.entry_price,
                    color: 'yellow',
                    lineWidth: 2,
                    title: 'Entry Price',
                });
            }

            index++;

            // ---- Speed decision (neat + obvious) ----
            const delay = tradeActive
            ? activeTradeSpeed
            : generalSpeed;

            timeoutRef.current = setTimeout(tick, delay);
        };

        tick(); // kick off animation

        return () => {
            clearInterval(timeoutRef.current);
            if (stopLineRef.current) {
                seriesRef.current.removePriceLine(stopLineRef.current);
            }
            if (entryLineRef.current) {
                seriesRef.current.removePriceLine(entryLineRef.current);
            }
        };
    }, [data, activeTradeSpeed, generalSpeed, onUpdateSummary]);

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

// class RectanglePrimitive {
//   constructor(p1, p2, options) {
//     this.p1 = p1; // { time, price }
//     this.p2 = p2;
//     this.options = options;
//   }

//   draw(ctx, renderer) {
//     const x1 = renderer.timeToCoordinate(this.p1.time);
//     const y1 = renderer.priceToCoordinate(this.p1.price);
//     const x2 = renderer.timeToCoordinate(this.p2.time);
//     const y2 = renderer.priceToCoordinate(this.p2.price);

//     if (x1 === null || x2 === null || y1 === null || y2 === null) return;

//     ctx.fillStyle = this.options.fillColor;
//     ctx.strokeStyle = this.options.borderColor;
//     ctx.lineWidth = this.options.lineWidth;

//     const x = Math.min(x1, x2);
//     const y = Math.min(y1, y2);
//     const w = Math.abs(x2 - x1);
//     const h = Math.abs(y2 - y1);

//     ctx.fillRect(x, y, w, h);
//     ctx.strokeRect(x, y, w, h);
//   }
// }


export default TradingChart;
