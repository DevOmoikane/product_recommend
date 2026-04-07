import { useCallback } from 'react';
import { NODE_TYPES, NODE_CONFIG } from '../utils/nodeConfigs';

export default function Sidebar({ onSave, onLoad, nodeDefinitions, onRun, onStop, isRunning, onTogglePanel }) {
  const onDragStart = useCallback((event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Node Palette</h2>
      </div>
      
      <div className="sidebar-content">
        <h3>Drag nodes to canvas</h3>
        <div className="node-list">
          {Object.values(nodeDefinitions)?.map((definition) => {
              const [key, value] = Object.entries(definition)[0];
              return (
                <div
                  key={key}
                  className="draggable-node"
                  onDragStart={(event) => onDragStart(event, key)}
                  draggable
                  style={{ borderColor: value.color }}
                >
                  <span className="node-icon"><i className={value.icon}></i></span>
                  <span className="node-label">{value.label}</span>
                </div>
              );
            })
          }
        </div>
      </div>

      <div className="sidebar-actions">
        <button onClick={onRun} className="action-btn run-btn" disabled={isRunning}>
          <i className="fa fa-play"></i> Run
        </button>
        <button onClick={onStop} className="action-btn stop-btn" disabled={!isRunning}>
          <i className="fa fa-stop"></i> Stop
        </button>
        <button onClick={onTogglePanel} className="action-btn panel-btn">
          <i className="fa fa-terminal"></i> Logs
        </button>
        <button onClick={onSave} className="action-btn save-btn">
          Save
        </button>
        <button onClick={onLoad} className="action-btn load-btn">
          Load
        </button>
      </div>
    </aside>
  );
}