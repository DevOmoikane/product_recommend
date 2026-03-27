import { useState, useCallback, useRef, memo, useEffect } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Background,
  Controls,
  MiniMap,
  BaseEdge,
  getBezierPath,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import Sidebar from './components/Sidebar';
import useWorkflowPersistence from './hooks/useWorkflowPersistence';

import BaseNode from './components/nodes/BaseNode.jsx';
import { NODE_CONFIG, COMPATIBLE_CONNECTIONS } from './utils/nodeConfigs';

// const nodeTypes = {
//   dataSource: (props) => {
//     return <BaseNode {...props} type="dataSource" />
//   },
//   sqlQuery: (props) => {
//     return <BaseNode {...props} type="sqlQuery" />
//   },
//   mlModel: (props) => {
//     return <BaseNode {...props} type="mlModel" />
//   },
//   processor: (props) => {
//     return <BaseNode {...props} type="processor" />
//   },
//   output: (props) => {
//     return <BaseNode {...props} type="output" />
//   },
// };

const CustomEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}) => {
  const edgeColor = data?.color || '#999';
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        stroke: edgeColor,
        strokeWidth: 3,
      }}
    />
  );
});

const edgeTypes = {
  default: CustomEdge,
};

const initialNodes = [];
const initialEdges = [];

function Flow() {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [nodeDefinitions, setNodeDefinitions] = useState([]);
  const [nodeTypes, setNodeTypes] = useState({});

  const { saveWorkflow, loadWorkflow } = useWorkflowPersistence();

  useEffect(() => {
    const fetchNodeDefinitions = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/node-definitions');
        const data = await response.json();
        console.log('Fetched node definitions:', data);
        setNodeDefinitions(data);
        let _nodeTypes = {};
        if (data.length > 0) {
          data.forEach((nodeDefinition) => {
            const [key, _] = Object.entries(nodeDefinition)[0];
            _nodeTypes[key] = (props) => (
              <BaseNode {...props} type={key} />
            );
          });
        }
        console.log('NodeTypes = ', _nodeTypes);
        setNodeTypes(_nodeTypes);
      } catch (error) {
        console.error('Error fetching node definitions:', error);
      }
    };
    fetchNodeDefinitions();
  }, []);

  const onNodesChange = useCallback(
    (changes) => setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    [],
  );
  const onConnect = useCallback(
    (params) => {
      const sourceNode = nodes.find(n => n.id === params.source);
      const targetNode = nodes.find(n => n.id === params.target);
      
      if (!sourceNode || !targetNode) {
        setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot));
        return;
      }

      const sourceConfig = NODE_CONFIG[sourceNode.type];
      const targetConfig = NODE_CONFIG[targetNode.type];

      const sourceHandle = sourceConfig?.outputs?.find(o => o.id === params.sourceHandle);
      const targetHandle = targetConfig?.inputs?.find(i => i.id === params.targetHandle);

      const edgeColor = sourceHandle?.color || targetHandle?.color || '#999';

      const edgeWithColor = {
        ...params,
        data: { color: edgeColor },
      };

      setEdges((edgesSnapshot) => addEdge(edgeWithColor, edgesSnapshot));
    },
    [nodes],
  );

  const isValidConnection = useCallback((connection) => {
    if (connection.source === connection.target) return false;

    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);

    if (!sourceNode || !targetNode) return false;

    const sourceConfig = NODE_CONFIG[sourceNode.type];
    const targetConfig = NODE_CONFIG[targetNode.type];

    if (!sourceConfig || !targetConfig) return false;

    const sourceHandle = sourceConfig.outputs?.find(o => o.id === connection.sourceHandle);
    const targetHandle = targetConfig.inputs?.find(i => i.id === connection.targetHandle);

    if (!sourceHandle || !targetHandle) return false;

    const compatibleTypes = COMPATIBLE_CONNECTIONS[sourceHandle.type] || [];
    if (!compatibleTypes.includes(targetHandle.type)) return false;

    return true;
  }, [nodes]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left - 280,
        y: event.clientY - bounds.top,
      };

      const newNode = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: {
          label: type.charAt(0).toUpperCase() + type.slice(1).replace(/([A-Z])/g, ' $1').trim(),
          config: {},
          isValid: false,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes]
  );

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      {/* TODO: pass the data from the backend API for creating the node types palette */}
      <Sidebar 
        onSave={saveWorkflow} 
        onLoad={() => loadWorkflow(setNodes, setEdges)} 
        nodeDefinitions={nodeDefinitions} 
      />
      <div ref={reactFlowWrapper} style={{ flex: 1, height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onDragOver={onDragOver}
          onDrop={onDrop}
          fitView
        >
          <Background variant="dots" gap={20} size={1} />
          <Controls />
          <MiniMap nodeColor="#fff" pannable zoomable />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}