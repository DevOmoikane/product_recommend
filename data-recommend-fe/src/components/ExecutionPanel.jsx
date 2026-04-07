import { useState, useEffect, useRef } from 'react';

export default function ExecutionPanel({
  isOpen,
  onClose,
  executionId,
  status,
  logs,
  onRun,
  onStop,
}) {
  const logContainerRef = useRef(null);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  if (!isOpen) return null;

  const getStatusColor = () => {
    switch (status) {
      case 'running': return '#f59e0b';
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'running': return 'Running...';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      case 'pending': return 'Pending';
      default: return 'Idle';
    }
  };

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <h3>Workflow Execution</h3>
        <button className="panel-close-btn" onClick={onClose}>
          <i className="fa fa-times"></i>
        </button>
      </div>

      <div className="execution-panel-content">
        <div className="execution-status">
          <span className="status-label">Status:</span>
          <span 
            className="status-badge" 
            style={{ backgroundColor: getStatusColor() }}
          >
            {getStatusText()}
          </span>
          {executionId && (
            <span className="execution-id" title={executionId}>
              ID: {executionId.slice(0, 8)}...
            </span>
          )}
        </div>

        <div className="execution-logs" ref={logContainerRef}>
          {logs.length === 0 ? (
            <div className="log-empty">No execution logs yet</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`log-entry ${log.type || 'info'}`}>
                {log.message}
              </div>
            ))
          )}
        </div>

        <div className="execution-actions">
          <button 
            className="action-btn run-btn" 
            onClick={onRun}
            disabled={status === 'running'}
          >
            <i className="fa fa-play"></i> Run
          </button>
          <button 
            className="action-btn stop-btn" 
            onClick={onStop}
            disabled={status !== 'running'}
          >
            <i className="fa fa-stop"></i> Stop
          </button>
        </div>
      </div>
    </div>
  );
}