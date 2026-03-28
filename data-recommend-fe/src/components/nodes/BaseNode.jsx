import { memo, useCallback } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import CustomHandle from '../CustomHandle';

const validateNode = (node, nodeDefinition) => {
  if (!nodeDefinition) return { isValid: false, errors: ['Unknown node type'] };

  const errors = [];
  nodeDefinition.fields.forEach(field => {
    const value = node.data.config[field.name];
    if (!value || (typeof value === 'string' && value.trim() === '')) {
      errors.push(`${field.label} is required`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
  };
};

function BaseNode({ id, type, data, selected }) {
  const { setNodes } = useReactFlow();
  const nodeDefinition = data.nodeDefinition;

  const handleConfigChange = useCallback((fieldName, value) => {
    setNodes((nodes) =>
      nodes.map((node) => {
        if (node.id === id) {
          const newConfig = { ...node.data.config, [fieldName]: value };
          const updatedNode = {
            ...node,
            data: { ...node.data, config: newConfig },
          };
          const validation = validateNode(updatedNode, nodeDefinition);
          return {
            ...updatedNode,
            data: { ...updatedNode.data, isValid: validation.isValid, errors: validation.errors },
          };
        }
        return node;
      })
    );
  }, [id, setNodes, nodeDefinition]);

  const renderField = (field) => {
    const value = data.config[field.name] || '';
    
    if (field.type === 'select') {
      return (
        <select
          value={value}
          onChange={(e) => handleConfigChange(field.name, e.target.value)}
          className="node-select"
        >
          {field.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    }
    
    if (field.type === 'textarea') {
      return (
        <textarea
          value={value}
          onChange={(e) => handleConfigChange(field.name, e.target.value)}
          className="node-textarea"
          placeholder={field.label}
        />
      );
    }
    
    return (
      <input
        type="text"
        value={value}
        onChange={(e) => handleConfigChange(field.name, e.target.value)}
        className="node-input"
        placeholder={field.label}
      />
    );
  };

  const renderHandles = (handles, position) => {
    if (!handles || handles.length === 0) return null;
    
    const isInput = position === Position.Left;
    const spacing = 50;
    const startY = -(handles.length - 1) * spacing / 2;

    return handles.map((handle, index) => (
      <div 
        key={handle.id} 
        className={`handle-wrapper ${isInput ? 'handle-input' : 'handle-output'}`}
        style={{ top: `calc(50% + ${startY + index * spacing}px)` }}
      >
        {isInput ? (
          <>
            <CustomHandle
              type="target"
              position={Position.Left}
              id={handle.id}
              className="handle"
              connectionCount={handle.connectionCount ?? 1}
              style={{ background: handle.color, borderColor: handle.color }}
            />
            <label className="handle-label" style={{ color: handle.color }}>{handle.label}</label>
          </>
        ) : (
          <>
            <label className="handle-label" style={{ color: handle.color }}>{handle.label}</label>
            <CustomHandle
              type="source"
              position={Position.Right}
              id={handle.id}
              className="handle"
              style={{ background: handle.color, borderColor: handle.color }}
            />
          </>
        )}
      </div>
    ));
  };

  return (
    <div
      className={`base-node ${selected ? 'selected' : ''} ${data.isValid ? 'valid' : 'invalid'}`}
      style={{ borderColor: nodeDefinition.color }}
    >
      {renderHandles(nodeDefinition.inputs, Position.Left)}

      <div className="node-header" style={{ backgroundColor: nodeDefinition.color }}>
        <span className="node-icon"><i className={nodeDefinition.icon}></i></span>
        <span className="node-label">{data.label}</span>
      </div>
      
      <div className="node-content" style={{paddingLeft: '5em', paddingRight: '5em'}}>
        <div className="node-form">
          {nodeDefinition.fields.map((field) => (
            <div key={field.name} className="field-group">
              <label className="field-label">{field.label}</label>
              {renderField(field)}
            </div>
          ))}
        </div>
        {data.errors && data.errors.length > 0 && (
          <div className="node-errors">
            {data.errors.map((err, i) => (
              <span key={i} className="error-tag">{err}</span>
            ))}
          </div>
        )}
      </div>
      
      {renderHandles(nodeDefinition.outputs, Position.Right)}
    </div>
  );
}

export default memo(BaseNode);
