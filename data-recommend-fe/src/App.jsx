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
import 'font-awesome/css/font-awesome.css';

import Sidebar from './components/Sidebar';
import useWorkflowPersistence from './hooks/useWorkflowPersistence';
import ExecutionPanel from './components/ExecutionPanel';

import BaseNode from './components/nodes/BaseNode.jsx';
import { COMPATIBLE_CONNECTIONS } from './utils/nodeConfigs';
import { executeWorkflow, stopWorkflow, connectToExecution } from './services/workflowApi';
import { convertToBackendFormat } from './utils/workflowConverter';

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

const getNodeDefinitionByType = (nodeDefinitions, type) => {
  if (!nodeDefinitions || !Array.isArray(nodeDefinitions) || !type) {
    console.warn(`Invalid node definitions or type:`, nodeDefinitions, type);
    return null;
  }

  const nodeDefinition = nodeDefinitions.find(def => {
    const [key] = Object.keys(def);
    return key === type;
  });

  if (!nodeDefinition) {
    console.warn(`Node definition not found for type: ${type}`);
    return null;
  }

  // Return both the type and its configuration
  const [nodeType, nodeConfig] = Object.entries(nodeDefinition)[0];
  return {
    type: nodeType,
    config: nodeConfig,
    definition: nodeDefinition // Original definition object
  };
};

function Flow() {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [nodeDefinitions, setNodeDefinitions] = useState([]);
  const [nodeTypes, setNodeTypes] = useState({});

  const [executionState, setExecutionState] = useState({
    isOpen: false,
    executionId: null,
    status: 'idle',
    logs: [],
    nodeStatuses: {},
    nodeResults: {},
  });

  const { saveWorkflow, loadWorkflow } = useWorkflowPersistence();
  const wsRef = useRef(null);

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
              <BaseNode {...props} type={key} executionState={executionState} />
            );
          });
        }
        setNodeTypes(_nodeTypes);
      } catch (error) {
        console.error('Error fetching node definitions:', error);
      }
    };
    fetchNodeDefinitions();
  }, []);

  const addLog = useCallback((message, type = 'info') => {
    setExecutionState(prev => ({
      ...prev,
      logs: [...prev.logs, { message, type, timestamp: new Date().toLocaleTimeString() }]
    }));
  }, []);

  const handleWebSocketMessage = useCallback((message) => {
    const msgType = message.type || message.message_type;
    
    switch (msgType) {
      case 'initial_status':
        setExecutionState(prev => ({
          ...prev,
          status: message.status || 'running',
        }));
        addLog(`Initial status: ${message.status}`, 'info');
        break;
        
      case 'node_started':
        setExecutionState(prev => ({
          ...prev,
          nodeStatuses: {
            ...prev.nodeStatuses,
            [message.node_id]: { status: 'running', output: message.output },
          },
        }));
        addLog(`Node started: ${message.node_id}`, 'info');
        break;
        
      case 'node_completed':
        setExecutionState(prev => ({
          ...prev,
          nodeStatuses: {
            ...prev.nodeStatuses,
            [message.node_id]: { status: 'completed', output: message.output },
          },
          nodeResults: {
            ...prev.nodeResults,
            [message.node_id]: message.output || {},
          },
        }));
        addLog(`Node completed: ${message.node_id}`, 'success');
        break;
        
      case 'node_failed':
        setExecutionState(prev => ({
          ...prev,
          nodeStatuses: {
            ...prev.nodeStatuses,
            [message.node_id]: { status: 'failed', error: message.error },
          },
        }));
        addLog(`Node failed: ${message.node_id} - ${message.error}`, 'error');
        break;
        
      case 'execution_completed':
        setExecutionState(prev => ({
          ...prev,
          status: 'completed',
          nodeResults: message.results || prev.nodeResults,
        }));
        addLog('Execution completed', 'success');
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        break;
        
      case 'execution_failed':
        setExecutionState(prev => ({
          ...prev,
          status: 'failed',
        }));
        addLog(`Execution failed: ${message.error}`, 'error');
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        break;
        
      default:
        addLog(`Unknown message: ${JSON.stringify(message)}`, 'info');
    }
  }, [addLog]);

  const handleRunWorkflow = useCallback(async () => {
    try {
      const workflowData = convertToBackendFormat(nodes, edges, 'workflow', 'Executed from UI');
      
      const result = await executeWorkflow(workflowData);
      
      setExecutionState(prev => ({
        ...prev,
        isOpen: true,
        executionId: result.execution_id,
        status: result.status || 'running',
        logs: [{ message: `Execution started: ${result.execution_id}`, type: 'info' }],
        nodeStatuses: {},
        nodeResults: {},
      }));

      addLog(`Execution started: ${result.execution_id}`, 'info');

      if (wsRef.current) {
        wsRef.current.close();
      }

      wsRef.current = connectToExecution(
        result.execution_id,
        (message) => {
          handleWebSocketMessage(message);
        },
        (error) => {
          addLog(`WebSocket error: ${error}`, 'error');
        },
        () => {
          addLog('WebSocket connection closed', 'info');
        }
      );
    } catch (error) {
      addLog(`Failed to start execution: ${error.message}`, 'error');
      setExecutionState(prev => ({
        ...prev,
        status: 'failed',
      }));
    }
  }, [nodes, edges, addLog, handleWebSocketMessage]);

  const handleStopWorkflow = useCallback(async () => {
    if (!executionState.executionId) return;
    
    try {
      await stopWorkflow(executionState.executionId);
      addLog('Stopping execution...', 'info');
      setExecutionState(prev => ({
        ...prev,
        status: 'stopping',
      }));
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    } catch (error) {
      addLog(`Failed to stop execution: ${error.message}`, 'error');
    }
  }, [executionState.executionId, addLog]);

  const toggleExecutionPanel = useCallback(() => {
    setExecutionState(prev => ({
      ...prev,
      isOpen: !prev.isOpen,
    }));
  }, []);

  const onNodesChange = useCallback(
    (changes) => setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    [],
  );
  const onEdgesDelete = useCallback(
    (edgeIds) => {
      // Iterate over each edgeId data on edgeIds
      edgeIds.forEach((edge) => {
        const targetNode = nodes.find(n => n.id === edge.source);
        const targetHandleName = edge.targetHandle;
        // If there is a field with the same name as the the target handle, enable it again
        if (targetNode && targetNode.data.nodeDefinition) {
          const targetField = targetNode.data.nodeDefinition.fields.find(f => f.name === targetHandleName);
          if (targetField) {
            targetField.disabled = false;
          }
        }
      });
      setEdges((edgesSnapshot) => edgesSnapshot.filter((edge) => !edgeIds.includes(edge.id)))
    },
    [nodes],
  );
  const onConnect = useCallback(
    (params) => {
      const sourceNode = nodes.find(n => n.id === params.target);
      const targetNode = nodes.find(n => n.id === params.source);
      
      if (!sourceNode || !targetNode) {
        setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot));
        return;
      }

      const sourceDefinition = getNodeDefinitionByType(nodeDefinitions, sourceNode.type);
      const targetDefinition = getNodeDefinitionByType(nodeDefinitions, targetNode.type);

      const sourceHandle = sourceDefinition?.config?.outputs?.find(o => o.id === params.targetHandle);
      const targetHandle = targetDefinition?.config?.inputs?.find(i => i.id === params.sourceHandle);

      // if there is a field with the same name as the target handle, disable it, so the value of the field can not be changed until the connection is deleted
      if (targetHandle) {
        const targetField = targetNode.data.nodeDefinition.fields.find(f => f.name === targetHandle.id);
        if (targetField) {
          targetField.disabled = true;
        }
      }

      const edgeColor = sourceHandle?.color || targetHandle?.color || '#999';

      const edgeWithColor = {
        ...params,
        data: { color: edgeColor },
      };

      setEdges((edgesSnapshot) => addEdge(edgeWithColor, edgesSnapshot));
    },
    [nodes, nodeDefinitions]
  );

  const isValidConnection = useCallback(
    (connection) => {
      // the source and target on the connection are reversed
      if (connection.source === connection.target) {
        return false;
      }

      const sourceNode = nodes.find(n => n.id === connection.target);
      const targetNode = nodes.find(n => n.id === connection.source);

      if (!sourceNode || !targetNode) {
        return false;
      }

      const sourceDefinition = getNodeDefinitionByType(nodeDefinitions, sourceNode.type);
      const targetDefinition = getNodeDefinitionByType(nodeDefinitions, targetNode.type);

      if (!sourceDefinition || !targetDefinition) {
        return false;
      }
      const sourceHandle = sourceDefinition?.config?.outputs?.find(o => o.id === connection.targetHandle);
      const targetHandle = targetDefinition?.config?.inputs?.find(i => i.id === connection.sourceHandle);

      if (!sourceHandle || !targetHandle) {
        return false;
      }

      // Check if target handle connection count is already at max, remember that source and target are reversed in the connection object
      const targetConnections = edges.filter(e => e.source === connection.source && e.sourceHandle === connection.sourceHandle);
      if (targetConnections.length >= (targetHandle.connection_count || 1)) {
        return false;
      }

      const sourceTypes = Array.isArray(sourceHandle.type) ? sourceHandle.type : [sourceHandle.type];
      const targetTypes = Array.isArray(targetHandle.type) ? targetHandle.type : [targetHandle.type];

      const isCompatible = sourceTypes.some(sourceType => {
        const compatibleTypes = COMPATIBLE_CONNECTIONS[sourceType] || [];
        // Check direct match or compatible types
        return targetTypes.some(targetType => 
          sourceType === targetType || compatibleTypes.includes(targetType)
        );
      });

      return isCompatible;
    }, 
    [nodes, nodeDefinitions, edges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowWrapper.current) return;

      const nodeDefinitionData = getNodeDefinitionByType(nodeDefinitions, type);

      if (!nodeDefinitionData) {
        console.error(`Node definition not found for type: ${type}`);
        return;
      }

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left - 280,
        y: event.clientY - bounds.top,
      };

      const newNode = {
        id: `${nodeDefinitionData.type}-${Date.now()}`,
        type: nodeDefinitionData.type,
        position,
        data: {
          label: nodeDefinitionData.config.name || nodeDefinitionData.type.charAt(0).toUpperCase() + nodeDefinitionData.type.slice(1).replace(/([A-Z])/g, ' $1').trim(),
          config: nodeDefinitionData.config || {},
          isValid: false,
          nodeDefinition: nodeDefinitionData.config,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes, nodeDefinitions]
  );

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      {/* TODO: pass the data from the backend API for creating the node types palette */}
      <Sidebar 
        onSave={saveWorkflow} 
        onLoad={() => loadWorkflow(setNodes, setEdges)} 
        nodeDefinitions={nodeDefinitions}
        onRun={handleRunWorkflow}
        onStop={handleStopWorkflow}
        isRunning={executionState.status === 'running'}
        onTogglePanel={toggleExecutionPanel}
      />
      <div ref={reactFlowWrapper} style={{ flex: 1, height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          onEdgesDelete={onEdgesDelete}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onDragOver={onDragOver}
          onDrop={onDrop}
        >
          <Background variant="dots" gap={20} size={1} />
          <Controls />
          <MiniMap nodeColor="#fff" pannable zoomable />
        </ReactFlow>
      </div>

      <ExecutionPanel
        isOpen={executionState.isOpen}
        onClose={toggleExecutionPanel}
        executionId={executionState.executionId}
        status={executionState.status}
        logs={executionState.logs}
        onRun={handleRunWorkflow}
        onStop={handleStopWorkflow}
      />
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