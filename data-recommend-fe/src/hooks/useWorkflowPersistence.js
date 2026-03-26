import { useCallback } from 'react';
import { useReactFlow } from '@xyflow/react';

const STORAGE_KEY = 'workflow-persistence';
const API_BASE_URL = '/api/workflows';

export default function useWorkflowPersistence() {
  const { getNodes, getEdges } = useReactFlow();

  const saveToLocalStorage = useCallback((nodes, edges) => {
    const workflowData = {
      nodes,
      edges,
      savedAt: new Date().toISOString(),
      version: '1.0',
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(workflowData));
    return { success: true, message: 'Saved to local storage' };
  }, []);

  const loadFromLocalStorage = useCallback(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const { nodes, edges } = JSON.parse(saved);
        return { success: true, data: { nodes, edges } };
      } catch {
        return { success: false, message: 'Failed to parse saved workflow' };
      }
    }
    return { success: false, message: 'No saved workflow found' };
  }, []);

  const saveToBackend = useCallback(async (nodes, edges) => {
    try {
      const workflowData = {
        nodes,
        edges,
        savedAt: new Date().toISOString(),
      };
      
      const response = await fetch(`${API_BASE_URL}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflowData),
      });
      
      if (!response.ok) throw new Error('Failed to save to backend');
      return { success: true, message: 'Saved to backend' };
    } catch (error) {
      console.error('Backend save failed:', error);
      return { success: false, message: 'Backend save failed, falling back to local', error };
    }
  }, []);

  const loadFromBackend = useCallback(async (workflowId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/load/${workflowId}`);
      if (!response.ok) throw new Error('Failed to load from backend');
      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error('Backend load failed:', error);
      return { success: false, message: 'Failed to load from backend', error };
    }
  }, []);

  const saveWorkflow = useCallback(async () => {
    const nodes = getNodes();
    const edges = getEdges();
    
    const result = saveToLocalStorage(nodes, edges);
    
    try {
      await saveToBackend(nodes, edges);
    } catch {
      console.log('Backend not available, using local storage only');
    }
    
    return result;
  }, [getNodes, getEdges, saveToLocalStorage, saveToBackend]);

  const loadWorkflow = useCallback((setNodes, setEdges) => {
    const result = loadFromLocalStorage();
    if (result.success && result.data) {
      setNodes(result.data.nodes);
      setEdges(result.data.edges);
    }
    return result;
  }, [loadFromLocalStorage]);

  return {
    saveWorkflow,
    loadWorkflow,
    saveToLocalStorage,
    loadFromLocalStorage,
    saveToBackend,
    loadFromBackend,
  };
}