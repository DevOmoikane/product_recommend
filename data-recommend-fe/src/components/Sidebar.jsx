import { useCallback } from 'react';
import { NODE_TYPES, NODE_CONFIG } from '../utils/nodeConfigs';

export default function Sidebar({ onSave, onLoad }) {
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
          {Object.values(NODE_TYPES).map((type) => {
            const config = NODE_CONFIG[type];
            return (
              <div
                key={type}
                className="draggable-node"
                onDragStart={(event) => onDragStart(event, type)}
                draggable
                style={{ borderColor: config.color }}
              >
                <span className="node-icon">{config.icon}</span>
                <span className="node-label">{config.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="sidebar-actions">
        <button onClick={onSave} className="action-btn save-btn">
          Save Workflow
        </button>
        <button onClick={onLoad} className="action-btn load-btn">
          Load Workflow
        </button>
      </div>
    </aside>
  );
}