import { useCallback } from 'react';
import { NODE_TYPES, NODE_CONFIG } from '../utils/nodeConfigs';

export default function Sidebar({ onSave, onLoad, nodeDefinitions }) {
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
          {Object.keys(nodeDefinitions).length > 0 ? (
            Object.values(nodeDefinitions).map((definition) => {
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
          ) : (
            Object.values(NODE_TYPES).map((type) => {
              const config = NODE_CONFIG[type];
              return (
                <div
                  key={type}
                  className="draggable-node"
                  onDragStart={(event) => onDragStart(event, type)}
                  draggable
                  style={{ borderColor: config.color }}
                >
                  <span className="node-icon"><i className={config.icon}></i></span>
                  <span className="node-label">{config.label}</span>
                </div>
              );
            })
          )}
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