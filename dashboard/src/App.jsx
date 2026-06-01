import React, { useState, useEffect, useRef } from 'react';
import { Play, Copy, Database, Sparkles, CheckCircle, AlertTriangle, BarChart3, HelpCircle, Activity, ChevronLeft, ChevronRight } from 'lucide-react';
import { Bar, Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
} from 'chart.js';

// Register ChartJS plugins
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const BACKEND_URL = "http://localhost:8000";

function App() {
  const [instruction, setInstruction] = useState('');
  const [loadingGen, setLoadingGen] = useState(false);
  const [loadingExec, setLoadingExec] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(null);
  
  const [generatedSql, setGeneratedSql] = useState('');
  const [executionResult, setExecutionResult] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [copied, setCopied] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 5;

  // Chart type auto-selection
  const [chartType, setChartType] = useState('bar'); // 'bar' | 'line' | 'doughnut'

  // Health check polling on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/health`);
        const data = await res.json();
        if (data.status === "ok") {
          setBackendHealthy(true);
        } else {
          setBackendHealthy(false);
        }
      } catch (err) {
        setBackendHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateSql = async (e) => {
    e.preventDefault();
    if (!instruction.trim()) return;

    setLoadingGen(true);
    setErrorDetail('');
    setExecutionResult(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction })
      });

      const data = await res.json();
      if (res.status === 200) {
        setGeneratedSql(data.sql);
      } else {
        setErrorDetail(data.detail || "Failed to generate SQL from model.");
      }
    } catch (err) {
      setErrorDetail("Backend is unreachable. Ensure the FastAPI app.py is running on port 8000.");
    } finally {
      setLoadingGen(false);
    }
  };

  const handleExecuteSql = async () => {
    if (!generatedSql.trim()) return;

    setLoadingExec(true);
    setErrorDetail('');
    setExecutionResult(null);
    setCurrentPage(1);

    try {
      const res = await fetch(`${BACKEND_URL}/api/execute-sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql: generatedSql })
      });

      const data = await res.json();
      if (res.status === 200) {
        setExecutionResult(data);
        // Automatically determine optimal chart type
        detectOptimalChart(data);
      } else {
        setErrorDetail(data.detail || "Failed to execute generated SQL in database.");
      }
    } catch (err) {
      setErrorDetail("Failed to connect to database execution API.");
    } finally {
      setLoadingExec(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const detectOptimalChart = (result) => {
    if (!result || !result.data || result.data.length === 0) return;
    
    // Check if we have standard category and numeric values
    const columns = result.columns;
    let hasString = false;
    let hasNumber = false;
    let hasDate = false;

    // Inspect columns
    columns.forEach(col => {
      const sampleVal = result.data[0][col];
      if (typeof sampleVal === 'number') {
        hasNumber = true;
      } else if (typeof sampleVal === 'string') {
        if (col.includes('date') || col.includes('time') || col.includes('timestamp')) {
          hasDate = true;
        } else {
          hasString = true;
        }
      }
    });

    // Smart charts selection
    if (hasDate && hasNumber) {
      setChartType('line');
    } else if (result.data.length <= 6) {
      setChartType('doughnut');
    } else {
      setChartType('bar');
    }
  };

  // Compile Chart.js datasets from data
  const getChartData = () => {
    if (!executionResult || !executionResult.data || executionResult.data.length === 0) return null;

    const data = executionResult.data;
    const columns = executionResult.columns;

    // Detect primary text/label column and first number/value column
    let labelColumn = null;
    let valueColumn = null;

    columns.forEach(col => {
      const sample = data[0][col];
      if (!labelColumn && (typeof sample === 'string' || typeof sample === 'object')) {
        labelColumn = col;
      }
      if (!valueColumn && typeof sample === 'number') {
        valueColumn = col;
      }
    });

    // Fallbacks if not auto-detected
    if (!labelColumn) labelColumn = columns[0];
    if (!valueColumn) {
      // Find any number or default to row indices
      columns.forEach(col => {
        if (typeof data[0][col] === 'number') valueColumn = col;
      });
    }

    if (!valueColumn) return null; // Can't render chart without numeric values

    const labels = data.map(row => String(row[labelColumn] || 'N/A'));
    const values = data.map(row => row[valueColumn] || 0);

    return {
      labels,
      datasets: [
        {
          label: valueColumn.replace(/_/g, ' ').toUpperCase(),
          data: values,
          backgroundColor: chartType === 'doughnut' ? [
            'rgba(142, 68, 173, 0.7)',
            'rgba(236, 64, 122, 0.7)',
            'rgba(52, 152, 219, 0.7)',
            'rgba(46, 204, 113, 0.7)',
            'rgba(241, 196, 15, 0.7)',
            'rgba(230, 126, 34, 0.7)',
          ] : 'rgba(142, 68, 173, 0.65)',
          borderColor: chartType === 'doughnut' ? [
            'rgb(142, 68, 173)',
            'rgb(236, 64, 122)',
            'rgb(52, 152, 219)',
            'rgb(46, 204, 113)',
            'rgb(241, 196, 15)',
            'rgb(230, 126, 34)',
          ] : 'rgb(142, 68, 173)',
          borderWidth: 1.5,
          tension: 0.35,
          fill: true
        }
      ]
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: chartType === 'doughnut',
        labels: { color: 'hsl(210, 40%, 98%)', font: { family: 'Outfit' } }
      },
      tooltip: {
        padding: 10,
        titleFont: { family: 'Outfit', size: 14 },
        bodyFont: { family: 'Outfit', size: 12 }
      }
    },
    scales: chartType !== 'doughnut' ? {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: 'hsl(215, 20%, 65%)', font: { family: 'Outfit' } }
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: 'hsl(215, 20%, 65%)', font: { family: 'Outfit' } }
      }
    } : {}
  };

  // Pagination logic
  const paginatedData = () => {
    if (!executionResult || !executionResult.data) return [];
    const startIndex = (currentPage - 1) * rowsPerPage;
    return executionResult.data.slice(startIndex, startIndex + rowsPerPage);
  };

  const totalPages = executionResult ? Math.ceil(executionResult.rows_count / rowsPerPage) : 0;

  return (
    <div className="app-container">
      {/* Top Navigation Panel */}
      <header className="dashboard-header">
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.02em', background: 'linear-gradient(135deg, #fff 30%, var(--accent-pink))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            SQL Llama BI Console
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            AI-Powered Indonesian Text-to-SQL Analytics
          </p>
        </div>
        
        {/* Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', borderRadius: '20px' }}>
            <Activity size={15} style={{ color: backendHealthy ? 'var(--accent-green)' : backendHealthy === false ? 'var(--accent-pink)' : 'var(--text-muted)' }} />
            <span>Backend API:</span>
            <span style={{ fontWeight: '600', color: backendHealthy ? 'var(--accent-green)' : backendHealthy === false ? 'var(--accent-pink)' : 'var(--text-muted)' }}>
              {backendHealthy === true ? 'CONNECTED' : backendHealthy === false ? 'OFFLINE' : 'CONNECTING...'}
            </span>
          </div>
        </div>
      </header>

      {/* Primary Dashboard Grid */}
      <div className="dashboard-grid">
        
        {/* Step 1: Input Instruction */}
        <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'hsla(263, 90%, 55%, 0.15)', display: 'flex', alignItems: 'center', justify: 'center', justifyContent: 'center' }}>
              <Sparkles size={18} style={{ color: 'var(--accent-purple)' }} />
            </div>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: '600' }}>Tanya Database Llama</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Ketik instruksi bahasa Indonesia untuk menerjemahkan ke SQL Olist.</p>
            </div>
          </div>

          <form onSubmit={handleGenerateSql} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <textarea
              className="neon-input"
              rows="3"
              placeholder="Contoh: Tampilkan 5 produk teratas dengan harga termahal atau Hitung jumlah pelanggan di kota 'sao paulo'..."
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              disabled={loadingGen}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn-primary" type="submit" disabled={loadingGen || !instruction.trim()}>
                {loadingGen ? 'Menganalisis...' : 'Terjemahkan SQL'}
                <Sparkles size={16} />
              </button>
            </div>
          </form>
        </section>

        {/* Step 2: SQL View Output panel */}
        {generatedSql && (
          <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'hsla(199, 90%, 50%, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Database size={18} style={{ color: 'var(--accent-blue)' }} />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Generated PostgreSQL Query</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>AI-generated read-only SQL query.</p>
                </div>
              </div>
              
              {/* Copy action */}
              <button className="btn-secondary" style={{ padding: '8px 16px', fontSize: '13px' }} onClick={copyToClipboard}>
                {copied ? 'Copied!' : 'Copy'}
                <Copy size={14} />
              </button>
            </div>

            {/* Code editor pane */}
            <div className="code-panel">
              {generatedSql}
            </div>

            {/* Execution action */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button className="btn-primary" style={{ background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))', boxShadow: '0 4px 15px rgba(52, 152, 219, 0.3)' }} onClick={handleExecuteSql} disabled={loadingExec}>
                {loadingExec ? 'Executing...' : 'Jalankan Query'}
                <Play size={15} />
              </button>
            </div>
          </section>
        )}

        {/* Error Alert Display */}
        {errorDetail && (
          <div className="glass-card" style={{ borderLeft: '4px solid var(--accent-pink)', display: 'flex', gap: '16px', padding: '16px 20px', background: 'rgba(231, 76, 60, 0.05)' }}>
            <AlertTriangle size={24} style={{ color: 'var(--accent-pink)', flexShrink: 0 }} />
            <div>
              <h4 style={{ fontWeight: '600', fontSize: '15px', color: 'var(--accent-pink)' }}>System Alert</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px', whiteSpace: 'pre-wrap' }}>{errorDetail}</p>
            </div>
          </div>
        )}

        {/* Query Results Visual & Tabular Panel */}
        {executionResult && (
          <div className="grid-cols-2">
            
            {/* Visual Chart Panel */}
            <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'hsla(142, 70%, 45%, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <BarChart3 size={18} style={{ color: 'var(--accent-green)' }} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: '600' }}>BI Data Visualization</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Interactive charts based on numerical metrics.</p>
                  </div>
                </div>
                
                {/* Visual selectors */}
                {getChartData() && (
                  <div style={{ display: 'flex', background: 'hsla(224, 25%, 4%, 0.6)', padding: '4px', borderRadius: '8px', gap: '4px' }}>
                    {['bar', 'line', 'doughnut'].map(t => (
                      <button
                        key={t}
                        style={{ background: chartType === t ? 'hsla(224, 25%, 20%, 0.8)' : 'transparent', border: 'none', color: 'var(--text-main)', fontSize: '11px', textTransform: 'capitalize', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}
                        onClick={() => setChartType(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Chart canvas viewport */}
              <div style={{ minHeight: '260px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                {getChartData() ? (
                  <div style={{ position: 'absolute', width: '100%', height: '100%' }}>
                    {chartType === 'bar' && <Bar data={getChartData()} options={chartOptions} />}
                    {chartType === 'line' && <Line data={getChartData()} options={chartOptions} />}
                    {chartType === 'doughnut' && <Doughnut data={getChartData()} options={chartOptions} />}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
                    <HelpCircle size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                    <p>No numeric values returned to render charts.</p>
                  </div>
                )}
              </div>
            </section>

            {/* Tabular Data Grid Panel */}
            <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Query Data Grid</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Returned records count: {executionResult.rows_count} rows</p>
                </div>
              </div>

              {executionResult.rows_count > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', justifyContent: 'space-between' }}>
                  <div className="table-container">
                    <table className="premium-table">
                      <thead>
                        <tr>
                          {executionResult.columns.map(col => (
                            <th key={col}>{col.replace(/_/g, ' ')}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedData().map((row, idx) => (
                          <tr key={idx}>
                            {executionResult.columns.map(col => (
                              <td key={col}>
                                {row[col] === null ? <span style={{ fontStyle: 'italic', opacity: 0.5 }}>null</span> : String(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination control */}
                  {totalPages > 1 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px', borderTop: '1px solid hsla(224, 20%, 20%, 0.3)', paddingTop: '14px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        Page <strong style={{ color: 'var(--text-main)' }}>{currentPage}</strong> of <strong style={{ color: 'var(--text-main)' }}>{totalPages}</strong>
                      </span>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                          <ChevronLeft size={16} />
                        </button>
                        <button className="btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '14px', minHeight: '260px' }}>
                  <CheckCircle size={32} style={{ color: 'var(--accent-green)', margin: '0 auto 12px', display: 'block', opacity: 0.5 }} />
                  <p>Query executed successfully but returned 0 rows.</p>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
