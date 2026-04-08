import { useCallback, useState, useMemo } from 'react';
import { NODE_TYPES, NODE_CONFIG } from '../utils/nodeConfigs';

const DEFAULT_CATEGORY = 'Default';

function groupNodesByCategory(nodeDefinitions) {
  const categoryMap = new Map();

  nodeDefinitions?.forEach((definition) => {
    const [key, value] = Object.entries(definition)[0];
    const category = value.category || DEFAULT_CATEGORY;

    if (!categoryMap.has(category)) {
      categoryMap.set(category, []);
    }

    categoryMap.get(category).push({ key, value });
  });

  const sortedCategories = Array.from(categoryMap.keys()).sort((a, b) => {
    if (a === DEFAULT_CATEGORY) return -1;
    if (b === DEFAULT_CATEGORY) return 1;
    return a.localeCompare(b);
  });

  return sortedCategories.map((category) => {
    const nodes = categoryMap.get(category).sort((a, b) =>
      a.value.label.localeCompare(b.value.label)
    );
    return [category, nodes];
  });
}

export default function Sidebar({ onSave, onLoad, nodeDefinitions, onRun, onStop, isRunning, onTogglePanel }) {
  const [expandedCategories, setExpandedCategories] = useState({});

  const onDragStart = useCallback((event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  const groupedNodes = useMemo(() => groupNodesByCategory(nodeDefinitions), [nodeDefinitions]);

  const handleToggleCategory = useCallback((category) => {
    setExpandedCategories(prev => {
      const current = prev[category];
      return {
        ...prev,
        [category]: current === undefined ? false : !current
      };
    });
  }, []);

  const isExpanded = (category) => {
    const val = expandedCategories[category];
    return val === undefined ? true : val;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Node Palette</h2>
      </div>
      
      <div className="sidebar-content">
        <h3>Drag nodes to canvas</h3>
        <div className="node-list">
          {groupedNodes.map(([category, nodes]) => (
            <div key={category} className="node-category">
              <div 
                className="category-header" 
                onClick={() => handleToggleCategory(category)}
              >
                <span className={`category-chevron ${isExpanded(category) ? 'expanded' : ''}`}>
                  <i className="fa fa-chevron-right"></i>
                </span>
                <span className="category-title">{category}</span>
              </div>
              <div className={`category-content ${isExpanded(category) ? 'expanded' : ''}`}>
                {nodes.map(({ key, value }) => (
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
                ))}
              </div>
            </div>
          ))}
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